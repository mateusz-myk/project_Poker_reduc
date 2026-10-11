"""Scenario and exhaustive state checks for the Leduc engine."""
from functools import lru_cache
from fractions import Fraction
from leduc.engine import Card, GameEngine


def C(rank, suit):
    return Card(rank, suit)

@lru_cache(maxsize=None)
def seed_for_deal(private_cards, community, n_players=3):
    """Fixture helper: find a seed dealing the requested private and board cards."""
    for seed in range(100_000):
        game=GameEngine(seed,n_players=n_players,n_ranks=3,n_suits=3)
        if tuple(game.private_cards)==tuple(private_cards) and game._hidden_community==community:
            return seed
    raise AssertionError("no seed found for requested deterministic deal")

def game_with_deal(private_cards, community, n_players=3):
    return GameEngine(seed_for_deal(tuple(private_cards),community,n_players),n_players=n_players,n_ranks=3,n_suits=3)
def state(game, contributions, pot, player, legal, round_no, raises):
    assert game.contributions==contributions
    assert game.pot==pot==sum(contributions)
    assert game.current_player()==player
    assert game.round_number==round_no
    assert game.raises==raises
    assert (game.legal_actions(player) if player is not None else None)==legal

def act(game, action, contributions, pot, player, legal, round_no, raises):
    game.step(action)
    state(game,contributions,pot,player,legal,round_no,raises)

def calls(game, n_players=3):
    while not game.is_terminal(): game.step("call")

def test_s1_checks_pair_and_payoffs():
    g=game_with_deal((C(2,0),C(1,0),C(0,0)),C(2,1))
    act(g,"call",[1]*3,3,1,("call","raise"),1,0)
    act(g,"call",[1]*3,3,2,("call","raise"),1,0)
    act(g,"call",[1]*3,3,0,("call","raise"),2,0)
    for p in (0,1): act(g,"call",[1]*3,3,p+1,("call","raise"),2,0)
    g.step("call")
    assert g.is_terminal() and g.payoffs()==(2,-1,-1)

def test_s2_raise_call_fold_and_r2_start():
    g=game_with_deal((C(2,0),C(1,0),C(0,0)),C(2,1))
    act(g,"raise",[3,1,1],5,1,("fold","call","raise"),1,1)
    act(g,"call",[3,3,1],7,2,("fold","call","raise"),1,1)
    act(g,"fold",[3,3,1],7,0,("call","raise"),2,0)

def test_s3_raise_limit_reopen_in_second_round():
    g=game_with_deal((C(2,0),C(1,0),C(0,0)),C(2,1))
    act(g,"raise",[3,1,1],5,1,("fold","call","raise"),1,1)
    act(g,"raise",[3,5,1],9,2,("fold","call"),1,2)
    act(g,"call",[3,5,5],13,0,("fold","call"),1,2)
    act(g,"call",[5,5,5],15,0,("call","raise"),2,0)

def test_s4_fold_closes_r2_and_showdown_payoffs():
    g=game_with_deal((C(2,0),C(0,0),C(1,0)),C(2,1))
    for p in range(3):
        g.step("call"); assert g.contributions==[1,1,1] and g.pot==3
        if p<2: assert g.current_player()==p+1
    assert (g.round_number,g.current_player(),g.raises)==(2,0,0)
    for p in (0,1): g.step("call"); assert g.contributions==[1,1,1] and g.pot==3 and g.current_player()==p+1
    act(g,"raise",[1,1,5],7,0,("fold","call","raise"),2,1)
    act(g,"call",[5,1,5],11,1,("fold","call","raise"),2,1)
    g.step("fold")
    assert g.is_terminal() and g.current_player() is None
    assert g.contributions==[5,1,5] and g.pot==11
    assert g.payoffs()==(6,-1,-5)

def test_s5_fold_before_call_and_showdown():
    g=game_with_deal((C(2,0),C(1,0),C(0,0)),C(2,1))
    for _ in range(3): g.step("call")
    g.step("raise"); assert g.contributions==[5,1,1] and g.pot==7
    g.step("fold"); assert g.current_player()==2 and g.contributions==[5,1,1]
    assert g.legal_actions(2)==("fold","call","raise")
    g.step("call")
    assert g.is_terminal() and g.contributions==[5,1,5] and g.pot==11

def test_s6_fold_to_one_finishes_without_revealing_cards():
    from leduc.render import render_showdown
    g=game_with_deal((C(2,0),C(1,0),C(0,0)),C(2,1))
    g.step("raise"); g.step("fold"); g.step("fold")
    assert g.is_terminal() and g.community_card is None
    assert g.payoffs()==(2,-1,-1)
    view=render_showdown(g)
    assert "[K" not in view and "[Q" not in view and "[J" not in view

def test_s7_two_raises_in_r2_and_calling_sequence():
    g=game_with_deal((C(2,0),C(1,0),C(0,0)),C(2,1))
    for _ in range(3): g.step("call")
    assert (g.round_number,g.current_player(),g.raises)==(2,0,0)
    act(g,"raise",[5,1,1],7,1,("fold","call","raise"),2,1)
    act(g,"raise",[5,9,1],15,2,("fold","call"),2,2)
    act(g,"call",[5,9,9],23,0,("fold","call"),2,2)
    g.step("call")
    assert g.is_terminal() and g.contributions==[9,9,9] and g.pot==27

def test_s8_fold_legality_and_raise_limit():
    g=game_with_deal((C(2,0),C(1,0),C(0,0)),C(2,1))
    assert g.legal_actions(0)==("call","raise")
    g.step("raise"); g.step("raise")
    assert g.legal_actions(2)==("fold","call")

def test_s9_r2_starts_lowest_active_and_turn_order_correction():
    g=game_with_deal((C(2,0),C(1,0),C(0,0)),C(2,1))
    g.step("raise"); g.step("call"); g.step("call")
    assert g.current_player()==0 # G0 remains active and first in R2.
    # Feasible version of the requested fold: G0 checks, G1 raises, G2 calls,
    # then G0 folds; R2 therefore starts with G1, the lowest active ID.
    h=game_with_deal((C(2,0),C(1,0),C(0,0)),C(2,1))
    h.step("call"); h.step("raise"); h.step("call")
    assert h.current_player()==0 and h.legal_actions(0)[0]=="fold"
    h.step("fold")
    assert (h.round_number,h.current_player(),h.raises)==(2,1,0)


def test_screenshot_535_state_is_reachable_across_round_boundary():
    g=game_with_deal((C(2,0),C(1,0),C(0,0)),C(2,1))
    g.step("raise")  # G0: 3,1,1
    g.step("call")   # G1: 3,3,1
    g.step("raise")  # G2 second R1 raise: 3,3,5
    g.step("call")   # G0: 5,3,5
    assert g.legal_actions(1)==("fold","call")
    g.step("fold")
    assert (g.round_number,g.current_player(),g.raises)==(2,0,0)
    assert g.contributions==[5,3,5] and g.pot==13
    g.step("call")   # G0's check is a new-round action.
    assert g.current_player()==2
    assert g.legal_actions(2)==("call","raise")
    assert [(p,a) for p,a,_ in g.history[-4:]]==[(2,"raise"),(0,"call"),(1,"fold"),(0,"call")]
def test_s10_two_way_tie_fractional_payoffs():
    g=game_with_deal((C(2,0),C(0,0),C(2,1)),C(0,2))
    g.step("raise"); g.step("fold"); g.step("call")
    assert g.contributions==[3,1,3] and g.pot==7 and g.round_number==2
    calls(g)
    assert g.payoffs()==(Fraction(1,2),Fraction(-1),Fraction(1,2))
    assert sum(g.payoffs())==0

def test_s11_pair_high_pair_tie_and_three_way_high_tie():
    pair=game_with_deal((C(0,0),C(2,0),C(1,0)),C(0,1))
    calls(pair)
    assert pair.payoffs()[0]>pair.payoffs()[1]
    pair_tie=game_with_deal((C(2,0),C(2,1),C(1,0)),C(2,2))
    calls(pair_tie)
    assert pair_tie.payoffs()[0]==pair_tie.payoffs()[1]
    high_tie=game_with_deal((C(2,0),C(2,1),C(2,2)),C(1,0))
    calls(high_tie)
    assert high_tie.payoffs()==(Fraction(0),)*3

def test_s12_two_player_limit_and_r2_reopens_raise():
    g=game_with_deal((C(2,0),C(1,0)),C(0,0),2)
    act(g,"raise",[3,1],4,1,("fold","call","raise"),1,1)
    act(g,"raise",[3,5],8,0,("fold","call"),1,2)
    act(g,"call",[5,5],10,0,("call","raise"),2,0)


def signature(g):
    return (g.private_cards,g.deck,g._hidden_community,g.community_card,g.pot,tuple(g.contributions),tuple(g.folded),g.round_number,g.raises,g.acted,g.current,g.done,g.payoffs(),tuple(g.history),g.to_json(),g.rng.getstate())

def exhaustive(game):
    nodes=0; leaves=0; screenshot_states=0
    def visit(g,round_start):
        nonlocal nodes,leaves,screenshot_states
        nodes+=1
        assert g.pot==sum(g.contributions)
        active=[i for i in range(g.n_players) if not g.folded[i]]
        assert g.current_player() is None or not g.folded[g.current_player()]
        assert g.raises<=2
        if g.round_number==2 and g.n_players==3 and g.folded[1] and sorted(g.contributions)==[3,5,5]:
            screenshot_states+=1
        replay=GameEngine.replay_json(g.to_json())
        assert signature(replay)==signature(g)
        bet=2 if g.round_number==1 else 4
        for i in range(g.n_players):
            assert g.contributions[i]>=round_start[i]
            assert g.contributions[i]-round_start[i] <= (g.raises+1)*bet
        if g.is_terminal():
            leaves+=1
            assert sum(g.payoffs())==0
            assert sum(g.payoffs()[i]+g.contributions[i] for i in range(g.n_players))==g.pot
            if g.community_card is not None and len(active)>1:
                assert len({g.contributions[i] for i in active})==1
            return
        if set(active).issubset(g.acted) and len({g.contributions[i] for i in active})==1:
            raise AssertionError("engine kept asking after betting round was complete")
        assert g.current_player() in active
        p=g.current_player()
        for action in g.legal_actions(p):
            child=g.copy(); old_round=child.round_number; old_bet=2 if old_round==1 else 4
            old_contrib=tuple(child.contributions); old_max=max(old_contrib[i] for i in active)
            old_raise=child.raises; old_folded=tuple(child.folded)
            child.step(action)
            assert child.pot==sum(child.contributions)
            assert child.raises<=2
            if action=="raise":
                assert child.contributions[p]-old_contrib[p] == old_max-old_contrib[p]+old_bet
                assert max(child.contributions[i] for i in active)==old_max+old_bet
                assert child.raises==old_raise+1
            if child.round_number==old_round:
                for i in range(child.n_players):
                    assert child.contributions[i]-round_start[i] <= (child.raises+1)*old_bet
            else:
                active_after=[i for i in range(child.n_players) if not child.folded[i]]
                assert all(child.contributions[i]==child.contributions[active_after[0]] for i in active_after)
                assert child.round_number==old_round+1 and child.raises==0
                assert child.current_player()==min(active_after)
            if action=="fold": assert old_contrib[p]<max(old_contrib[i] for i in active)
            for i,was_folded in enumerate(old_folded):
                if was_folded: assert child.contributions[i]==old_contrib[i] and i!=child.current_player()
            next_start=tuple(child.contributions) if child.round_number!=old_round else round_start
            visit(child,next_start)
    visit(game,tuple(game.contributions))
    return nodes,leaves,screenshot_states

def test_exhaustive_legal_action_dfs_three_and_two_players():
    three_boards=[((C(2,0),C(1,0),C(0,0)),C(2,1)),((C(2,0),C(2,1),C(1,0)),C(0,2))]
    two_boards=[((C(2,0),C(1,0)),C(0,1)),((C(2,0),C(2,1)),C(1,2))]
    total_nodes=total_leaves=screenshot_states=0
    for hand,board in three_boards:
        nodes,leaves,suspect=exhaustive(game_with_deal(hand,board,3))
        total_nodes+=nodes; total_leaves+=leaves; screenshot_states+=suspect
    for hand,board in two_boards:
        nodes,leaves,suspect=exhaustive(game_with_deal(hand,board,2))
        total_nodes+=nodes; total_leaves+=leaves; screenshot_states+=suspect
    assert total_nodes>0 and total_leaves>0 and screenshot_states>0
    print(f"Leduc exhaustive DFS: {total_nodes} nodes, {total_leaves} terminal states; {screenshot_states} states with 5/3/5 and G1 folded")
