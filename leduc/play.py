"""Hot-seat Leduc Poker with optional IS-MCTS seats."""
from __future__ import annotations
import argparse
import os
import random
import sys
from fractions import Fraction
from .engine import GameEngine
from .render import render_table, render_showdown, render_handoff, compact_card
from .agents.ismcts import ISMCTSAgent

_MASK64 = (1 << 64) - 1

def _clear():
    os.system("cls" if os.name == "nt" else "clear")

def _utf8_or_ascii(requested_unicode):
    if not requested_unicode: return False
    try:
        reconfigure=getattr(sys.stdout,"reconfigure",None)
        if reconfigure: reconfigure(encoding="utf-8",errors="strict")
        else: "â™ˇâ™§â™˘".encode(getattr(sys.stdout,"encoding",None) or "ascii")
    except (OSError,ValueError,UnicodeError): return False
    return True

def _parse_ai_seats(value, players):
    if value is None or value == "":
        return ()
    try:
        seats = tuple(int(part.strip()) for part in value.split(",")) if isinstance(value, str) else tuple(value)
    except (ValueError, TypeError):
        raise ValueError("--ai-seats must be a comma-separated list of seat numbers") from None
    if len(set(seats)) != len(seats):
        raise ValueError("--ai-seats cannot contain duplicate seats")
    if any(seat < 0 or seat >= players for seat in seats):
        raise ValueError(f"AI seats must be between 0 and {players - 1}")
    return tuple(sorted(seats))

def _seat_seed(agent_seed, hand_number, seat):
    return (int(agent_seed) ^ (hand_number * 0x9E3779B97F4A7C15) ^ (seat * 0xD1B54A32D192ED03)) & _MASK64

def _signed(value):
    value = Fraction(value)
    sign = "+" if value >= 0 else "-"
    amount = abs(value)
    return sign + (str(amount.numerator) if amount.denominator == 1 else f"{amount.numerator}/{amount.denominator}")

def _ai_debug_lines(player, agent):
    stats = agent.last_stats
    lines = [f"Debug AI Gracz {player}: czas {stats.get('elapsed_seconds', 0.0):.3f} s"]
    for action, item in stats.get("root_actions", {}).items():
        mean = item.get("mean_payoff")
        mean_text = "brak" if mean is None else f"{mean:+.3f}"
        lines.append(f"  {action}: odwiedziny {item.get('visits', 0)}, srednia {mean_text} zet.")
    return lines

def play(players=3, seed=0, unicode=False, color=False, debug=False, ai_seats=(),
         n_sims=200, c=1.4, agent_seed=None, no_pause=False):
    if players not in (2, 3):
        raise ValueError("players must be 2 or 3")
    ai_seats = _parse_ai_seats(ai_seats, players)
    base_seed = int(seed)
    agent_seed = base_seed if agent_seed is None else int(agent_seed)
    unicode=_utf8_or_ascii(unicode)
    human_seats = tuple(p for p in range(players) if p not in ai_seats)
    observer_mode = not human_seats
    session_scores = [Fraction(0) for _ in range(players)]
    hand_number = 0
    last_game = None
    try:
        while True:
            hand_seed = base_seed + hand_number
            game=GameEngine(hand_seed,players)
            last_game = game
            agents = {seat: ISMCTSAgent(n_sims=n_sims, c=c, seed=_seat_seed(agent_seed, hand_number, seat))
                      for seat in ai_seats}
            pending_ai_lines = []
            while not game.is_terminal():
                p=game.current_player()
                obs=game.observe(p)
                legal=game.legal_actions(p)
                if p in agents:
                    if observer_mode:
                        _clear()
                        print(render_table(obs,players,game.bet_size,unicode,False,
                                           game.private_cards if debug else (),game,ai_seats))
                    owed=max(game.contributions[i] for i in range(players) if not game.folded[i])-game.contributions[p]
                    action=agents[p].act(obs,legal)
                    game.step(action)
                    shown_action="check" if action=="call" and owed==0 else action
                    action_line=f"Gracz {p} (AI): {shown_action}"
                    if observer_mode:
                        print(action_line)
                        if debug:
                            for line in _ai_debug_lines(p,agents[p]): print(line)
                        if not no_pause:
                            input("Enter â€” nastepna akcja")
                    else:
                        pending_ai_lines.append(action_line)
                        if debug: pending_ai_lines.extend(_ai_debug_lines(p,agents[p]))
                    continue

                _clear()
                if len(human_seats) > 1:
                    print(render_handoff(p))
                    input()
                    _clear()
                for line in pending_ai_lines: print(line)
                pending_ai_lines.clear()
                print(render_table(obs,players,game.bet_size,unicode,False,
                                   game.private_cards if debug else (),game,ai_seats))
                while True:
                    raw=input(" Akcja: ").strip().lower()
                    action={"f":"fold","c":"call","r":"raise"}.get(raw,raw)
                    if action in legal: break
                    print("Nielegalna akcja; dostepne skroty: "+", ".join({"fold":"f","call":"c","raise":"r"}[a] for a in legal))
                game.step(action)

            for line in pending_ai_lines: print(line)
            print(f"Rozdanie {hand_number + 1}")
            print(render_showdown(game,unicode,debug))
            for seat in human_seats:
                session_scores[seat] += game.payoffs()[seat]
            if human_seats:
                print("Wynik sesji: "+", ".join(f"Gracz {p}: {_signed(session_scores[p])}" for p in human_seats))
            hand_number += 1
            again=input("Kolejne rozdanie? [t/N] ").strip().lower()
            if again not in ("t","tak","y","yes"):
                return last_game
    except KeyboardInterrupt:
        print("\nSesja przerwana.")
        return last_game

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--players",type=int,choices=(2,3),default=3)
    ap.add_argument("--seed",type=int,default=None)
    ap.add_argument("--ai-seats",default="",help="miejsca AI, np. 1,2; puste oznacza samych ludzi")
    ap.add_argument("--n-sims",type=int,default=200)
    ap.add_argument("--c",type=float,default=1.4)
    ap.add_argument("--agent-seed",type=int,default=None)
    ap.add_argument("--no-pause",action="store_true",help="bez pauz w trybie obserwatora")
    mode=ap.add_mutually_exclusive_group()
    mode.add_argument("--unicode",dest="unicode",action="store_true")
    mode.add_argument("--ascii",dest="unicode",action="store_false")
    ap.set_defaults(unicode=True)
    ap.add_argument("--no-color",action="store_true",help="ANSI-kolory nie sa uzywane")
    ap.add_argument("--debug",action="store_true")
    a=ap.parse_args()
    seed=a.seed if a.seed is not None else int.from_bytes(os.urandom(8),"big")
    try:
        seats=_parse_ai_seats(a.ai_seats,a.players)
    except ValueError as error:
        ap.error(str(error))
    play(a.players,seed,a.unicode,False,a.debug,seats,a.n_sims,a.c,a.agent_seed,a.no_pause)
if __name__=="__main__": main()
