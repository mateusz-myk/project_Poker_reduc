"""Uniform random legal-action baseline."""
import random

class RandomAgent:
    def __init__(self, seed=None):
        self.rng = random.Random(seed)
    def act(self, observation, legal_actions):
        return self.rng.choice(tuple(legal_actions))
