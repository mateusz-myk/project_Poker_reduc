from pathlib import Path
from leduc.engine import GameEngine
from leduc.render import render_card, render_table, visible_len

def test_prompt_is_single_and_action_line_is_indented():
    g=GameEngine(1)
    view=render_table(g.observe(0),3,g.bet_size,game=g)
    assert "Akcja:" not in view
    assert view.splitlines()[-1].startswith(" ")
    cli=Path("leduc/play.py").read_text(encoding="utf-8")
    assert cli.count("Akcja:")==1

def test_hidden_card_pattern_has_fixed_width():
    expected=["+-----+","| ? ? |","|  ?  |","| ? ? |","+-----+"]
    assert render_card(None).splitlines()==expected
    assert len({visible_len(line) for line in expected})==1

def test_zero_bet_is_called_check_in_history_and_prompt():
    g=GameEngine(3,n_players=2)
    g.step("call")
    view=render_table(g.observe(1),2,g.bet_size,game=g)
    assert "G0 check" in view
    assert "Do wyrownania: 0 zetonow (mozesz czekac)" in view
    assert "call = check" not in view

def test_raise_counter_is_rendered():
    g=GameEngine(4)
    assert "Podbicia: 0/2" in render_table(g.observe(0),3,g.bet_size,game=g)
    g.step("raise")
    assert "Podbicia: 1/2" in render_table(g.observe(1),3,g.bet_size,game=g)
