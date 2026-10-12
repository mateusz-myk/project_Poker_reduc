"""CLI checks for human, AI, and observer play modes."""
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

from leduc.engine import GameEngine
from leduc.evaluate import evaluate, _run_config
from leduc.play import play
from leduc.render import compact_card


def _run_play(**kwargs):
    output = StringIO()
    def scripted_input(prompt=""):
        if prompt.startswith(" Akcja:"):
            return "c"
        if prompt.startswith("Kolejne rozdanie?"):
            return "n"
        return ""
    with patch("builtins.input", side_effect=scripted_input), patch("leduc.play._clear"), redirect_stdout(output):
        game = play(**kwargs)
    return game, output.getvalue()


def test_one_human_two_ai_hides_cards_and_logs_ai_moves():
    game, output = _run_play(players=3, seed=314, ai_seats=(1, 2), n_sims=12, agent_seed=40)
    assert game.is_terminal()
    assert "Gracz 1 (AI):" in output or "Gracz 2 (AI):" in output
    assert "Gracz 1 (AI):" in output.split("SHOWDOWN", 1)[0] or "Gracz 2 (AI):" in output.split("SHOWDOWN", 1)[0]
    pre_showdown = output.split("SHOWDOWN", 1)[0]
    for seat in (1, 2):
        assert compact_card(game.private_cards[seat]) not in pre_showdown
    assert "Teraz Gracz" not in output  # one human is never asked to pass the computer


def test_debug_shows_cards_and_ai_root_statistics():
    game, output = _run_play(players=3, seed=315, ai_seats=(1, 2), n_sims=12, debug=True)
    pre_showdown = output.split("SHOWDOWN", 1)[0]
    assert all(compact_card(card) in pre_showdown for card in game.private_cards)
    assert "Debug AI Gracz" in output
    assert "odwiedziny" in output and "srednia" in output and "czas" in output


def test_observer_has_no_action_prompt_and_is_deterministic():
    kwargs = dict(players=3, seed=900, ai_seats=(0, 1, 2), n_sims=12, no_pause=True)
    first, out1 = _run_play(**kwargs)
    second, out2 = _run_play(**kwargs)
    assert first.log["actions"] == second.log["actions"]
    assert " Akcja:" not in out1
    assert "Teraz Gracz" not in out1


def test_pass_screen_only_when_multiple_humans():
    _, one_human = _run_play(players=3, seed=122, ai_seats=(1, 2), n_sims=8)
    _, two_humans = _run_play(players=3, seed=122, ai_seats=(2,), n_sims=8)
    assert "Teraz Gracz" not in one_human
    assert "Teraz Gracz" in two_humans

def test_evaluator_selfplay_is_exact_zero_sum_and_mean_ci_covers_zero():
    match = _run_config(0, 76, 10, 1.4, 3, "ismcts", 10, 1.4)
    assert sum(match["payoffs"]) == 0
    result = evaluate(n_sims=10, c=1.4, hands=90, players=3, seed=740, workers=1,
                      opponents="ismcts", opp_n_sims=10, opp_c=1.4)
    mean = result["mean_payoff"]
    ci = result["ci95"]
    assert mean - ci <= 0 <= mean + ci
    assert set(result["mean_payoff_by_seat"]) == {"0", "1", "2"}
    assert result["mean_decision_seconds_a"] > 0
    assert result["mean_decision_seconds_b"] > 0


def test_ismcts_opponents_results_are_worker_invariant():
    serial = evaluate(n_sims=10, c=1.1, hands=12, players=3, seed=818, workers=1,
                      opponents="ismcts", opp_n_sims=8, opp_c=1.4)
    parallel = evaluate(n_sims=10, c=1.1, hands=12, players=3, seed=818, workers=3,
                        opponents="ismcts", opp_n_sims=8, opp_c=1.4)
    assert parallel["mean_payoff"] == serial["mean_payoff"]
    assert parallel["ci95"] == serial["ci95"]
    assert parallel["mean_payoff_by_seat"] == serial["mean_payoff_by_seat"]


def test_ai_seat_validation_allows_observer_and_rejects_invalid_seats():
    from leduc.play import _parse_ai_seats
    assert _parse_ai_seats("0,1,2", 3) == (0, 1, 2)
    for value in ("3", "-1", "1,1", "x"):
        try:
            _parse_ai_seats(value, 3)
        except ValueError:
            pass
        else:
            raise AssertionError(f"invalid AI seat specification accepted: {value}")
