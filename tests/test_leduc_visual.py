import unicodedata
from leduc.engine import GameEngine
from leduc.render import render_card, render_table, render_showdown, render_handoff, visible_len

def _assert_width(text, limit=60):
    assert max(map(visible_len,text.splitlines()),default=0)<=limit

def test_render_cards_symbols_and_alignment():
    for rank in range(3):
        for suit in range(3):
            card=type(GameEngine().private_cards[0])(rank,suit)
            for mode in (False,True):
                lines=render_card(card,mode).splitlines()
                assert len({visible_len(line) for line in lines})==1
                assert ("HCD"[suit] if not mode else "♡♧♢"[suit]) in render_card(card,mode)
    assert unicodedata.east_asian_width("♡")=="A"
    assert unicodedata.east_asian_width("♧")=="A"
    assert unicodedata.east_asian_width("♢")=="N"

def test_table_privacy_and_widths():
    for n in (2,3):
        for mode in (False,True):
            g=GameEngine(10,n_players=n)
            table=render_table(g.observe(0),n,g.bet_size,mode,game=g)
            assert "Card(" not in table
            assert all(f"[{rank}{suit}]" not in table for i,c in enumerate(g.private_cards[1:],1) for rank in "JQK" for suit in "HCD" if rank=="JQK"[c.rank] and suit=="HCD"[c.suit])
            _assert_width(table)
            _assert_width(render_handoff(0))

def test_showdown_has_no_repr_and_signed_payoffs():
    g=GameEngine(2,n_players=2)
    while not g.is_terminal(): g.step("call")
    for mode in (False,True):
        view=render_showdown(g,mode)
        assert "Card(" not in view and "Suma wyplat: 0" in view
        _assert_width(view)

