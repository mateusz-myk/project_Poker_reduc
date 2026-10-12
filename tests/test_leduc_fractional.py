from fractions import Fraction
from leduc.engine import Card, GameEngine
from leduc.render import render_showdown

def test_two_way_odd_pot_is_split_exactly():
    game=GameEngine(1,3)
    game.pot=3; game.contributions=[1,1,1]
    game._finish((0,1))
    assert game.payoffs()==(Fraction(1,2),Fraction(1,2),Fraction(-1))
    assert sum(game.payoffs())==0

def test_three_way_four_chip_pot_has_exact_equal_shares():
    game=GameEngine(2,3)
    game.pot=4; game.contributions=[1,1,2]
    game._finish((0,1,2))
    assert tuple(game.payoffs()[i]+game.contributions[i] for i in range(3))==(Fraction(4,3),)*3
    assert sum(game.payoffs())==0

def test_identical_winners_have_equal_payoffs_many_seeds():
    for n_players in (2,3,4):
        for seed in range(100):
            game=GameEngine(seed,n_players)
            while not game.is_terminal(): game.step("call")
            active=[i for i in range(n_players) if not game.folded[i]]
            best=max((int(game.private_cards[i].rank==game.community_card.rank),game.private_cards[i].rank) for i in active)
            winners=[i for i in active if (int(game.private_cards[i].rank==game.community_card.rank),game.private_cards[i].rank)==best]
            assert len({game.payoffs()[i] for i in winners})==1
            assert sum(game.payoffs())==0

def test_tie_showdown_says_split_and_formats_fractions():
    game=GameEngine(3,3)
    game.private_cards=[Card(1,0),Card(1,1),Card(0,2)]
    game.community_card=Card(2,0)
    game.pot=3; game.contributions=[1,1,1]
    game._finish((0,1))
    view=render_showdown(game)
    assert "Remis: Gracz 0:, Gracz 1:, podzial puli po rowno" in view
    assert "REMIS" in view and "WYGRYWA" not in view
    assert "Gracz 0: +1/2" in view and "Gracz 1: +1/2" in view
    assert "Suma wyplat: 0" in view

