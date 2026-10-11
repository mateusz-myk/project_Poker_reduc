"""Pure, privacy-preserving text renderers for Leduc Poker."""
from __future__ import annotations
import textwrap
from .engine import Card, GameEngine, Observation
import re

def strip_ansi(text): return re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", text)
def visible_len(text): return len(strip_ansi(text))

# Suit indices map to hearts, clubs, diamonds in both display modes.
SUIT_SYMBOLS = {"ascii": ("H", "C", "D"), "unicode": ("♡", "♧", "♢")}
CARD_WIDTH = 7
SCREEN_WIDTH = 60

def rank_symbol(rank: int) -> str:
    return "JQK"[rank] if rank < 3 else str(rank + 1)

def suit_symbol(suit: int, unicode: bool = False) -> str:
    return SUIT_SYMBOLS["unicode" if unicode else "ascii"][suit % 3]

def compact_card(card: Card | None, unicode: bool = False) -> str:
    return "[??]" if card is None else f"[{rank_symbol(card.rank)}{suit_symbol(card.suit, unicode)}]"

def render_card(card: Card | None, unicode: bool = False) -> str:
    if card is None: return '\n'.join(("+-----+", "| ? ? |", "|  ?  |", "| ? ? |", "+-----+"))
    rank, suit = rank_symbol(card.rank), suit_symbol(card.suit, unicode)
    return '\n'.join(("+-----+", f"| {rank:<3} |", f"|  {suit}  |", f"|   {rank} |", "+-----+"))

def _history_rows(game: GameEngine):
    """Replay actions to annotate each entry with round and chips added."""
    replay=GameEngine(game.seed,game.n_players,game.n_ranks,game.n_suits)
    rows=[]
    for action in game.log["actions"]:
        p=replay.current_player(); before=replay.contributions[p]; rnd=replay.round_number
        owed=max(replay.contributions[i] for i in range(replay.n_players) if not replay.folded[i])-before
        replay.step(action)
        shown_action="check" if action=="call" and owed==0 else action
        rows.append((rnd,p,shown_action,replay.contributions[p]-before))
    return rows

def _wrapped_history(game: GameEngine):
    records=_history_rows(game)
    if not records: return ["  (brak akcji)"]
    output=[]
    for rnd in (1,2):
        items=[f"G{p} {action}" for r,p,action,_ in records if r==rnd]
        if not items: continue
        line=f"  R{rnd}: "
        for item in items:
            suffix=("" if line.endswith(": ") else ", ")+item
            if visible_len(line+suffix)>SCREEN_WIDTH:
                output.append(line); line="       "+item
            else: line+=suffix
        output.append(line)
    return output

def render_table(obs: Observation, n_players: int, bet_size: int, unicode=False, color=False, debug_cards=(), game: GameEngine|None=None):
    common=render_card(obs.community_card,unicode).splitlines()
    own=render_card(obs.private_card,unicode).splitlines()
    raises=game.raises if game is not None else 0
    header=f" LEDUC | R{obs.round_number}/2 | Bet {bet_size} | Pula {obs.pot} | Podbicia: {raises}/2"
    lines=["="*SCREEN_WIDTH,header,"="*SCREEN_WIDTH," KARTA WSPOLNA          TWOJA KARTA (Gracz "+str(obs.player_id)+")"]
    lines.extend(" "+a+"                "+b for a,b in zip(common,own))
    lines += ["-"*SCREEN_WIDTH," Gr  Wplacono  Status    Karta"]
    for i in range(n_players):
        mark=">" if i==obs.current_player else " "
        status="FOLD" if obs.folded[i] else "aktywny"
        if debug_cards: shown=compact_card(debug_cards[i],unicode)
        elif obs.folded[i]: shown="[--]"
        elif i==obs.player_id: shown=compact_card(obs.private_card,unicode)
        else: shown="[??]"
        lines.append(f"{mark} {i:<2} {obs.contributions[i]:>6}    {status:<8}  {shown}")
    lines.append("-"*SCREEN_WIDTH); lines.append(" Historia:")
    lines.extend(_wrapped_history(game) if game is not None else ["  Historia niedostepnia"])
    lines.append("-"*SCREEN_WIDTH)
    owed=max(obs.contributions[i] for i in range(n_players) if not obs.folded[i])-obs.contributions[obs.player_id]
    lines.append(f" Do wyrownania: {owed} zetonow"+(" (mozesz czekac)" if owed==0 else ""))
    if owed: actions=f" [f] fold (0)   [c] call (+{owed})"
    else: actions=" [c] check (0)"
    if game is not None and game.raises<2: actions+=f"   [r] raise (+{owed+bet_size})"
    lines.append(actions)
    return '\n'.join(lines)

def render_handoff(player_id: int):
    return f"Teraz Gracz {player_id} — naciśnij Enter"

def _format_payoff(value):
    from fractions import Fraction
    value=Fraction(value)
    sign="+" if value>=0 else "-"
    amount=abs(value)
    return sign+(str(amount.numerator) if amount.denominator==1 else f"{amount.numerator}/{amount.denominator}")

def _payout_line(paid):
    payout="Wyplaty: "+", ".join(f"Gracz {i} {_format_payoff(v)}" for i,v in enumerate(paid))
    return textwrap.wrap(payout,width=SCREEN_WIDTH,subsequent_indent="  ")
def render_showdown(game: GameEngine, unicode=False, debug=False):
    paid=game.payoffs(); active=[i for i in range(game.n_players) if not game.folded[i]]
    lines=["SHOWDOWN"]
    if len(active)==1:
        lines += ["Koniec po foldzie",f"Wygrywa: Gracz {active[0]}","Suma wyplat: "+str(sum(paid))]
        lines.extend(_payout_line(paid))
        return '\n'.join(lines)
    lines.append("Karta wspolna: "+compact_card(game.community_card,unicode))
    best=max((int(game.private_cards[i].rank==game.community_card.rank),game.private_cards[i].rank) for i in active)
    winners=[i for i in active if (int(game.private_cards[i].rank==game.community_card.rank),game.private_cards[i].rank)==best]
    lines.append("Remis: "+", ".join(f"Gracz {i}" for i in winners)+", podzial puli po rowno" if len(winners)>1 else f"Wygrywa: Gracz {winners[0]}")
    for i in range(game.n_players):
        if game.folded[i] and not debug:
            lines.append(f"G{i} FOLD{'':24}{_format_payoff(paid[i])}"); continue
        if game.folded[i]:
            lines.append(f"G{i} FOLD {compact_card(game.private_cards[i],unicode):<7}{_format_payoff(paid[i])}"); continue
        card=compact_card(game.private_cards[i],unicode)
        pair=game.private_cards[i].rank==game.community_card.rank
        detail=f"{'PARA' if pair else 'wysoka karta'} ({rank_symbol(game.private_cards[i].rank)})"
        label=("REMIS" if len(winners)>1 else "WYGRYWA") if i in winners else ""
        lines.append(f"G{i} {card:<6} {detail:<20} {label:<9} {_format_payoff(paid[i])}")
    lines.append("Suma wyplat: "+str(sum(paid)))
    lines.extend(_payout_line(paid))
    return '\n'.join(lines)









