from leduc.engine import GameEngine

def _act(game, action, expected_delta, expected_total, expected_pot):
    player=game.current_player(); before=game.contributions[player]
    game.step(action)
    assert game.contributions[player]-before==expected_delta
    assert tuple(game.contributions)==expected_total
    assert game.pot==expected_pot

def test_suspected_raise_call_fold_path_ends_round():
    g=GameEngine(7,3)
    _act(g,"raise",2,(3,1,1),5)
    _act(g,"call",2,(3,3,1),7)
    _act(g,"call",2,(3,3,3),9)
    assert g.round_number==2
    _act(g,"call",0,(3,3,3),9)
    _act(g,"call",0,(3,3,3),9)
    _act(g,"raise",4,(3,3,7),13)
    _act(g,"call",4,(7,3,7),17)
    _act(g,"fold",0,(7,3,7),17)
    assert g.is_terminal() and g.current_player() is None
    assert g.payoffs()==(-7,-3,10)

def test_raise_then_call_then_second_raise_costs():
    g=GameEngine(8,2)
    _act(g,"raise",2,(3,1),4)
    _act(g,"call",2,(3,3),6)
    assert g.round_number==2
    _act(g,"raise",4,(7,3),10)
    _act(g,"call",4,(7,7),14)
    assert g.is_terminal() and sum(g.payoffs())==0
