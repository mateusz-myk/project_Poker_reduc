import random
from leduc.engine import GameEngine

def finish_to_showdown(g):
    while not g.is_terminal(): g.step("call")

def test_seed_and_replay():
    a,b=GameEngine(12),GameEngine(12)
    assert a.private_cards==b.private_cards
    finish_to_showdown(a)
    assert GameEngine.replay_json(a.to_json()).payoffs()==a.payoffs()

def test_legal_and_fold():
    g=GameEngine(2); assert "fold" not in g.legal_actions(0)
    g.step("raise"); assert "fold" in g.legal_actions(1)
    g.step("fold"); g.step("fold")
    assert g.is_terminal() and sum(g.payoffs())==0

def test_round_and_raise_limit():
    g=GameEngine(4)
    g.step("call"); g.step("call"); g.step("call")
    assert g.round_number==2 and g.community_card is not None
    g.step("raise"); g.step("raise")
    assert "raise" not in g.legal_actions(g.current_player())

def test_zero_sum_and_privacy():
    g=GameEngine(5,n_players=2)
    o=g.observe(0); c=g.copy(); c.private_cards[1]=type(c.private_cards[1])(0,0)
    assert o==c.observe(0)
    finish_to_showdown(g); assert sum(g.payoffs())==0

def test_smoke_1000():
    rng=random.Random(91)
    for seed in range(1000):
        g=GameEngine(seed,n_players=2+seed%4)
        while not g.is_terminal():
            p=g.current_player(); g.step(rng.choice(g.legal_actions(p)))
            assert g.pot==sum(g.contributions)
        assert sum(g.payoffs())==0
