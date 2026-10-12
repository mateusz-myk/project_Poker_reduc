"""Helpers for running a single hand."""
from ..engine import GameEngine

def play_hand(env, agents):
    while not env.is_terminal():
        player = env.current_player()
        obs = env.observe(player)
        legal = env.legal_actions(player)
        action = agents[player].act(obs, legal)
        if action not in legal:
            raise ValueError(f"agent {player} selected illegal action {action!r}")
        env.step(action)
    return env.payoffs()
