"""Hot-seat command-line game with private handoff screens."""
from __future__ import annotations
import argparse, os, sys
from .engine import GameEngine
from .render import render_table, render_showdown, render_handoff

def _clear():
    os.system("cls" if os.name=="nt" else "clear")

def _utf8_or_ascii(requested_unicode):
    if not requested_unicode: return False
    try:
        reconfigure=getattr(sys.stdout,"reconfigure",None)
        if reconfigure: reconfigure(encoding="utf-8",errors="strict")
        else: "♡♧♢".encode(getattr(sys.stdout,"encoding",None) or "ascii")
    except (OSError,ValueError,UnicodeError): return False
    return True

def play(players=3, seed=0, unicode=False, color=False, debug=False):
    unicode=_utf8_or_ascii(unicode)
    game=GameEngine(seed,players)
    while not game.is_terminal():
        p=game.current_player()
        _clear(); print(render_handoff(p)); input()
        _clear()
        obs=game.observe(p)
        print(render_table(obs,players,game.bet_size,unicode,False,game.private_cards if debug else (),game))
        legal=game.legal_actions(p)
        while True:
            raw=input(" Akcja: ").strip().lower()
            action={"f":"fold","c":"call","r":"raise"}.get(raw,raw)
            if action in legal: break
            print("Nielegalna akcja; dostepne skroty: "+", ".join({"fold":"f","call":"c","raise":"r"}[a] for a in legal))
        game.step(action)
    _clear(); print(render_showdown(game,unicode,debug))
    return game

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--players",type=int,default=3); ap.add_argument("--seed",type=int,default=None)
    mode=ap.add_mutually_exclusive_group(); mode.add_argument("--unicode",dest="unicode",action="store_true"); mode.add_argument("--ascii",dest="unicode",action="store_false")
    ap.set_defaults(unicode=True); ap.add_argument("--no-color",action="store_true",help="ANSI-kolory nie sa uzywane")
    ap.add_argument("--debug",action="store_true")
    a=ap.parse_args(); play(a.players,a.seed if a.seed is not None else int.from_bytes(os.urandom(8),"big"),a.unicode,False,a.debug)
if __name__=="__main__": main()

