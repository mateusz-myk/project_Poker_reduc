"""Sequential three-player Leduc Poker engine."""
from __future__ import annotations
import copy, json, random
from fractions import Fraction
from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True)
class Card:
    rank: int
    suit: int

@dataclass(frozen=True)
class Observation:
    player_id: int
    private_card: Card
    community_card: Card | None
    pot: int
    contributions: tuple[int, ...]
    folded: tuple[bool, ...]
    round_number: int
    history: tuple[tuple[int, str, int], ...]
    current_player: int

class Agent(Protocol):
    def act(self, observation: Observation, legal_actions: tuple[str, ...]) -> str: ...

class GameEngine:
    ANTE = 1
    MAX_RAISES_PER_ROUND = 2
    ROUND_BET_SIZES = (2, 4)

    @classmethod
    def max_player_contribution(cls):
        return cls.ANTE + cls.MAX_RAISES_PER_ROUND * sum(cls.ROUND_BET_SIZES)

    def __init__(self, seed: int = 0, n_players: int = 3, n_ranks: int = 3, n_suits: int = 3):
        self.reset(seed, n_players, n_ranks, n_suits)

    def reset(self, seed: int = 0, n_players: int = 3, n_ranks: int = 3, n_suits: int = 3):
        if not 2 <= n_players <= 8 or n_ranks < 1 or n_suits < 1 or n_players + 1 > n_ranks*n_suits:
            raise ValueError("invalid player or deck configuration")
        self.seed, self.n_players, self.n_ranks, self.n_suits = int(seed), n_players, n_ranks, n_suits
        self.rng = random.Random(self.seed)
        self.deck = [Card(r, s) for r in range(n_ranks) for s in range(n_suits)]
        self.rng.shuffle(self.deck)
        self.private_cards = self.deck[:n_players]
        self.community_card = None
        self._hidden_community = self.deck[n_players]
        self.contributions = [self.ANTE] * n_players
        self.pot = n_players
        self.folded = [False] * n_players
        self.round_number = 1
        self.bet_size = self.ROUND_BET_SIZES[0]
        self.raises = 0
        self.acted: set[int] = set()
        self.current = 0
        self.history: list[tuple[int,str,int]] = []
        self.done = False
        self._payoffs: tuple[Fraction,...] | None = None
        self.log = {"version":1,"seed":self.seed,"n_players":n_players,"n_ranks":n_ranks,"n_suits":n_suits,"actions":[]}
        return self.observe(0)

    @classmethod
    def _public_betting_progress(cls, obs: Observation):
        """Reduce public betting history to metadata omitted from Observation."""
        n = len(obs.contributions)
        totals = [cls.ANTE] * n
        folded = [False] * n
        acted = set()
        raises = 0
        current = 0
        round_no = 1
        bet_size = cls.ROUND_BET_SIZES[0]
        for p, action, before in obs.history:
            if p != current or totals[p] != before:
                raise ValueError("inconsistent observation history")
            active = [i for i in range(n) if not folded[i]]
            max_paid = max(totals[i] for i in active)
            if action == "fold":
                folded[p] = True
            elif action == "call":
                totals[p] = max_paid
            elif action == "raise":
                totals[p] = max_paid + bet_size
                raises += 1
                acted = {p}
            else:
                raise ValueError("unknown action in observation")
            acted.add(p)
            active = [i for i in range(n) if not folded[i]]
            if len(active) == 1:
                break
            max_paid = max(totals[i] for i in active)
            if set(active).issubset(acted) and all(totals[i] == max_paid for i in active):
                if round_no == 1:
                    round_no = 2
                    bet_size = cls.ROUND_BET_SIZES[1]
                    raises, acted = 0, set()
                    current = min(active)
                    continue
                break
            for offset in range(1, n + 1):
                candidate = (p + offset) % n
                if candidate in active and candidate not in acted:
                    current = candidate
                    break
            else:
                current = next((p + k) % n for k in range(1, n + 1) if (p + k) % n in active)
        if (tuple(totals) != obs.contributions or tuple(folded) != obs.folded
                or round_no != obs.round_number or current != obs.current_player):
            raise ValueError("observation does not match its public history")
        return tuple(totals), tuple(folded), frozenset(acted), raises, round_no, bet_size, current

    @classmethod
    def determinize(cls, obs: Observation, rng: random.Random, n_ranks: int = 3, n_suits: int = 3, public_progress=None):
        """Build a sampled full state consistent with a public observation."""
        n = len(obs.contributions)
        if not 2 <= n <= 8 or n + 1 > n_ranks * n_suits:
            raise ValueError("invalid player or deck configuration")
        known = [obs.private_card]
        if obs.community_card is not None:
            known.append(obs.community_card)
        deck = [Card(r, s) for r in range(n_ranks) for s in range(n_suits)]
        unseen = [c for c in deck if c not in known]
        needed = n - 1 + (obs.community_card is None)
        sampled = rng.sample(unseen, needed)
        private = [None] * n
        private[obs.player_id] = obs.private_card
        for i, card in zip((i for i in range(n) if i != obs.player_id), sampled):
            private[i] = card
        hidden = obs.community_card if obs.community_card is not None else sampled[-1]
        # Betting metadata can be precomputed once for all simulations at a decision.
        if public_progress is None:
            public_progress = cls._public_betting_progress(obs)
        totals, folded, acted, raises, round_no, bet_size, current = public_progress
        game = object.__new__(cls)
        game.seed, game.n_players, game.n_ranks, game.n_suits = 0, n, n_ranks, n_suits
        game.rng = random.Random(rng.getrandbits(64))
        game.deck = deck
        game.private_cards = private
        game.community_card = obs.community_card
        game._hidden_community = hidden
        game.contributions = list(totals)
        game.pot = obs.pot
        game.folded = list(folded)
        game.round_number, game.bet_size = round_no, bet_size
        game.raises, game.acted, game.current = raises, set(acted), current
        game.history = list(obs.history)
        game.done, game._payoffs = False, None
        game.log = {"version": 1, "seed": 0, "n_players": n, "n_ranks": n_ranks, "n_suits": n_suits, "actions": [a for _, a, _ in obs.history]}
        return game

    def copy(self): return copy.deepcopy(self)
    def current_player(self): return None if self.done else self.current
    def is_terminal(self): return self.done
    def payoffs(self): return self._payoffs if self.done else None
    def payoffs_float(self):
        """Return terminal payoffs as floats for consumers that require them."""
        return None if self._payoffs is None else tuple(float(value) for value in self._payoffs)

    def legal_actions(self, player_id: int):
        self._check_turn(player_id)
        max_paid = max(self.contributions[i] for i in range(self.n_players) if not self.folded[i])
        owed = self.contributions[player_id] < max_paid
        actions = ["call"]
        if owed: actions.insert(0,"fold")
        if self.raises < self.MAX_RAISES_PER_ROUND: actions.append("raise")
        return tuple(actions)

    def observe(self, player_id: int):
        self._check_player(player_id)
        return Observation(player_id,self.private_cards[player_id],self.community_card,self.pot,tuple(self.contributions),tuple(self.folded),self.round_number,tuple(self.history),self.current)

    def step(self, action: str):
        if self.done: raise RuntimeError("game is already finished")
        p=self.current
        if action not in self.legal_actions(p): raise ValueError(f"illegal action {action!r}")
        self.log["actions"].append(action)
        self.history.append((p,action,self.contributions[p]))
        if action == "fold": self.folded[p]=True
        elif action == "call":
            max_paid=max(self.contributions[i] for i in range(self.n_players) if not self.folded[i])
            amount=max_paid-self.contributions[p]
            self.contributions[p]+=amount; self.pot+=amount
        else:
            max_paid=max(self.contributions[i] for i in range(self.n_players) if not self.folded[i])
            amount=max_paid-self.contributions[p]+self.bet_size
            self.contributions[p]+=amount; self.pot+=amount
            self.raises+=1
            self.acted={p}
        self.acted.add(p)
        active=[i for i in range(self.n_players) if not self.folded[i]]
        if len(active)==1: self._finish((active[0],)); return self.observe(p)
        max_paid=max(self.contributions[i] for i in active)
        if set(active).issubset(self.acted) and all(self.contributions[i]==max_paid for i in active):
            if self.round_number==1:
                self.round_number=2; self.bet_size=self.ROUND_BET_SIZES[1]; self.raises=0; self.acted=set()
                self.community_card=self._hidden_community
                self.current=min(active)
                return self.observe(p)
            self._finish(self._showdown_winners(active)); return self.observe(p)
        self.current=self._next(active)
        return self.observe(p)

    def _next(self, active):
        for n in range(1,self.n_players+1):
            i=(self.current+n)%self.n_players
            if i in active and i not in self.acted: return i
        for n in range(1,self.n_players+1):
            i=(self.current+n)%self.n_players
            if i in active: return i
        raise RuntimeError("no active player")

    def _showdown_winners(self, active):
        def score(i):
            pair=self.private_cards[i].rank==self.community_card.rank
            return (int(pair),self.private_cards[i].rank)
        best=max(score(i) for i in active)
        return tuple(i for i in active if score(i)==best)

    def _finish(self, winners):
        shares=[Fraction(0) for _ in range(self.n_players)]
        share=Fraction(self.pot,len(winners))
        for i in winners: shares[i]=share
        self._payoffs=tuple(shares[i]-self.contributions[i] for i in range(self.n_players))
        assert sum(self._payoffs,Fraction(0))==0
        self.done=True
    def _check_player(self,p):
        if not isinstance(p,int) or not 0<=p<self.n_players: raise ValueError("invalid player id")
    def _check_turn(self,p):
        self._check_player(p)
        if self.done or p!=self.current: raise ValueError("not this player's turn")

    def to_json(self): return json.dumps(self.log,sort_keys=True,separators=(",",":"))
    @classmethod
    def replay_json(cls,payload):
        data=json.loads(payload); game=cls(data["seed"],data["n_players"],data["n_ranks"],data["n_suits"])
        for action in data["actions"]: game.step(action)
        return game




