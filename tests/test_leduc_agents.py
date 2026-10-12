"""IS-MCTS and determinization checks."""
from collections import Counter
import random
import time
from pathlib import Path

from leduc.engine import Card, GameEngine, Observation
from leduc.agents import ISMCTSAgent, RandomAgent
from leduc.agents.runner import play_hand


def _finish_randomly(game, seed):
    rng = random.Random(seed)
    while not game.is_terminal():
        player = game.current_player()
        game.step(rng.choice(game.legal_actions(player)))


def test_determinize_preserves_observation_privacy_and_card_uniqueness():
    for n_players in (2, 3, 4):
        for seed in range(20):
            game = GameEngine(seed, n_players)
            rng = random.Random(seed * 100 + n_players)
            while not game.is_terminal():
                player = game.current_player()
                obs = game.observe(player)
                before = game.to_json()
                sampled = GameEngine.determinize(obs, rng)
                assert sampled.observe(player) == obs
                cards = sampled.private_cards + [sampled._hidden_community]
                assert len(set(cards)) == n_players + 1
                assert game.to_json() == before
                game.step(random.Random(seed + player + len(game.history)).choice(game.legal_actions(player)))


def test_determinize_samples_unseen_cards_uniformly():
    obs = Observation(0, Card(0, 0), None, 3, (1, 1, 1), (False, False, False), 1, (), 0)
    counts = Counter()
    rng = random.Random(9173)
    draws = 6000
    for _ in range(draws):
        sample = GameEngine.determinize(obs, rng)
        counts[sample.private_cards[1]] += 1
    assert len(counts) == 8
    assert all(abs(n - draws / 8) < 100 for n in counts.values())


def test_ismcts_legal_deterministic_and_bounded():
    obs = GameEngine(21).observe(0)
    legal = GameEngine(21).legal_actions(0)
    a, b = ISMCTSAgent(40, seed=8), ISMCTSAgent(40, seed=8)
    assert a.act(obs, legal) == b.act(obs, legal)
    for agent in (a, b):
        stats = agent.last_stats
        assert stats["n_sims"] == 40
        assert stats["nodes"] <= 41
        assert stats["nodes"] <= 489
        assert stats["root_actions"]
        assert agent.act(obs, legal) in legal
    forced = ISMCTSAgent(20, seed=3)
    assert forced.act(obs, ("call",)) == "call"
    assert forced.last_stats["n_sims"] == 0


def test_search_stats_and_action_do_not_depend_on_hidden_cards():
    obs = GameEngine(22).observe(0)
    other = GameEngine(22).copy()
    other.private_cards[1], other.private_cards[2] = other.private_cards[2], other.private_cards[1]
    obs2 = other.observe(0)
    legal = ("call", "raise")
    a, b = ISMCTSAgent(100, seed=55), ISMCTSAgent(100, seed=55)
    assert a.act(obs, legal) == b.act(obs2, legal)
    assert {k:v for k,v in a.last_stats.items() if k != "elapsed_seconds"} == {k:v for k,v in b.last_stats.items() if k != "elapsed_seconds"}


def test_copy_and_determinize_thousand_calls_are_fast():
    game = GameEngine(2)
    obs = game.observe(0)
    start = time.perf_counter()
    for i in range(1000):
        GameEngine.determinize(obs, random.Random(i))
    determinize_time = time.perf_counter() - start
    start = time.perf_counter()
    for _ in range(1000):
        game.copy()
    copy_time = time.perf_counter() - start
    assert determinize_time < 3.0
    assert determinize_time < copy_time


def test_play_hand_returns_zero_sum_exact_payoffs():
    game = GameEngine(123)
    payoff = play_hand(game, [ISMCTSAgent(20, seed=1), RandomAgent(2), RandomAgent(3)])
    assert game.is_terminal()
    assert sum(payoff) == 0


def test_ismcts_has_positive_mean_against_random_baseline():
    values = []
    for seed in range(160):
        players = 3
        seat = seed % players
        game = GameEngine(seed, players)
        agents = [ISMCTSAgent(100, seed=seed + 8000) if p == seat else RandomAgent(seed * 7 + p) for p in range(players)]
        values.append(float(play_hand(game, agents)[seat]))
    mean = sum(values) / len(values)
    assert mean > 0, mean


def test_king_pair_is_never_folded_when_facing_a_bet():
    observations = []
    for seed in range(1000):
        game = GameEngine(seed)
        # Target player 0 holding a King and the hidden board King.
        if game.private_cards[0].rank != 2 or game._hidden_community.rank != 2:
            continue
        rng = random.Random(seed + 10000)
        while not game.is_terminal():
            p = game.current_player()
            legal = game.legal_actions(p)
            obs = game.observe(p)
            if p == 0 and obs.community_card is not None and obs.private_card.rank == 2 and "fold" in legal:
                observations.append((obs, legal))
                break
            game.step(rng.choice(legal))
        if observations:
            break
    assert observations, "could not find a reachable King-pair decision"
    obs, legal = observations[0]
    assert obs.private_card.rank == obs.community_card.rank == 2
    for seed in range(8):
        agent = ISMCTSAgent(300, seed=seed)
        assert agent.act(obs, legal) != "fold"


def test_public_tree_bounds_and_export_files(tmp_path):
    for players, bound in ((2, 36), (3, 489)):
        game = GameEngine(711, players)
        agent = ISMCTSAgent(1200, seed=18)
        agent.act(game.observe(0), game.legal_actions(0))
        assert agent.last_stats["nodes"] <= bound
        prefix = str(tmp_path / "tree")
        data = agent.export_tree(prefix=prefix)
        assert data["nodes"] and data["edges"]
        assert (tmp_path / "tree.json").is_file()
        assert (tmp_path / "tree.dot").is_file()
