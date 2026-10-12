"""Single-observer IS-MCTS for Leduc Poker."""
from __future__ import annotations
from dataclasses import dataclass, field
import json, math, random, time
from pathlib import Path
from ..engine import GameEngine

_ACTION_ORDER = {"fold": 0, "call": 1, "raise": 2}

def uniform_rollout_policy(state, legal_actions, rng):
    return rng.choice(tuple(legal_actions))

@dataclass
class _Node:
    path: tuple[str, ...]
    player: int
    legal: tuple[str, ...]
    visits: int
    rewards: list[float]
    children: dict[str, "_Node"] = field(default_factory=dict)

class ISMCTSAgent:
    def __init__(self, n_sims=200, c=1.4, rollout_policy=None, seed=None, n_ranks=3, n_suits=3):
        if n_sims < 1 or c < 0:
            raise ValueError("n_sims must be positive and c nonnegative")
        self.n_sims, self.c = int(n_sims), float(c)
        self.rollout_policy = rollout_policy or uniform_rollout_policy
        self.rng = random.Random(seed)
        self.n_ranks, self.n_suits = n_ranks, n_suits
        self.last_stats = {}
        self._root = None
        self._root_obs = None

    @staticmethod
    def _legal(state):
        return state.legal_actions(state.current_player())

    def act(self, observation, legal_actions):
        start = time.perf_counter()
        legal_actions = tuple(legal_actions)
        if len(legal_actions) == 1:
            action = legal_actions[0]
            self.last_stats = {"n_sims": 0, "nodes": 1, "max_depth": 0, "elapsed_seconds": time.perf_counter()-start,
                               "root_actions": {action: {"visits": 0, "mean_payoff": None}}}
            return action
        root = _Node((), observation.player_id, legal_actions, 0, [0.0]*len(observation.contributions))
        self._root, self._root_obs = root, observation
        self._payoff_range = len(observation.contributions) * GameEngine.max_player_contribution()
        max_depth = 0
        public_progress = GameEngine._public_betting_progress(observation)
        for _ in range(self.n_sims):
            state = GameEngine.determinize(
                observation, self.rng, self.n_ranks, self.n_suits,
                public_progress=public_progress,
            )
            node = root
            path = []
            depth = 0
            while not state.is_terminal():
                player = state.current_player()
                actions = self._legal(state)
                if node.player != player or set(node.legal) != set(actions):
                    raise RuntimeError("public tree state diverged")
                unexpanded = [a for a in node.legal if a not in node.children]
                if unexpanded:
                    action = unexpanded[0]
                    state.step(action)
                    path.append(action)
                    child_legal = () if state.is_terminal() else self._legal(state)
                    child_player = -1 if state.is_terminal() else state.current_player()
                    child = _Node(tuple(path), child_player, child_legal, 0, [0.0]*len(observation.contributions))
                    node.children[action] = child
                    node = child
                    depth += 1
                    break
                action = self._select(node, player)
                state.step(action)
                path.append(action)
                node = node.children[action]
                depth += 1
            while not state.is_terminal():
                actions = self._legal(state)
                action = self.rollout_policy(state, actions, self.rng)
                if action not in actions:
                    raise ValueError("rollout policy returned an illegal action")
                state.step(action)
            rewards = state.payoffs_float()
            for visited in [root] + self._nodes_for_path(root, path):
                visited.visits += 1
                for i, value in enumerate(rewards):
                    visited.rewards[i] += value
            max_depth = max(max_depth, depth)
        ranked = []
        for action in root.legal:
            child = root.children.get(action)
            visits = child.visits if child else 0
            mean = child.rewards[observation.player_id] / visits if visits else float("-inf")
            ranked.append((visits, mean, -_ACTION_ORDER[action], action))
        action = max(ranked)[3]
        self.last_stats = {"n_sims": self.n_sims, "nodes": self._decision_nodes(root), "max_depth": max_depth,
                           "elapsed_seconds": time.perf_counter()-start,
                           "root_actions": {a: {"visits": (root.children[a].visits if a in root.children else 0),
                                                 "mean_payoff": (root.children[a].rewards[observation.player_id] / root.children[a].visits if a in root.children and root.children[a].visits else None)} for a in root.legal}}
        return action

    def _select(self, node, player):
        log_parent = math.log(max(1, node.visits))
        def score(action):
            child = node.children[action]
            raw_mean = child.rewards[player] / child.visits
            normalized_mean = (raw_mean + GameEngine.max_player_contribution()) / self._payoff_range
            return normalized_mean + self.c * math.sqrt(log_parent / child.visits)
        return max(node.legal, key=score)

    @staticmethod
    def _nodes_for_path(root, path):
        node = root
        result = []
        for action in path:
            node = node.children[action]
            result.append(node)
        return result

    @staticmethod
    def _decision_nodes(node):
        return (1 if node.player >= 0 else 0) + sum(ISMCTSAgent._decision_nodes(c) for c in node.children.values())

    def export_tree(self, min_visits=1, prefix="leduc_tree"):
        if self._root is None:
            raise RuntimeError("act() must be called before exporting the tree")
        nodes, edges = [], []
        def visit(node, parent=None, action=None):
            if node.visits < min_visits and parent is not None:
                return
            ident = "n" + ("root" if not node.path else "_".join(node.path))
            means = [x/node.visits for x in node.rewards] if node.visits else []
            entry = {"id": ident, "path": list(node.path), "player": node.player, "visits": node.visits, "mean_payoffs": means}
            nodes.append(entry)
            if parent is not None:
                edges.append({"source": parent, "target": ident, "action": action, "visits": node.visits})
            for a, child in node.children.items():
                visit(child, ident, a)
        visit(self._root)
        data = {"nodes": nodes, "edges": edges}
        Path(str(prefix)+".json").write_text(json.dumps(data, indent=2))
        lines = ["digraph ISMCTS {", "  node [shape=box];"]
        for node in nodes:
            label = f"{node['id']}\\nN={node['visits']}"
            mean = node["mean_payoffs"][self._root_obs.player_id] if node["mean_payoffs"] else 0
            max_wplata = GameEngine.max_player_contribution()
            value = (mean + max_wplata) / (len(self._root_obs.contributions) * max_wplata)
            value = min(1.0, max(0.0, value))
            red = round(232 * (1 - value) + 112 * value)
            green = round(132 * (1 - value) + 194 * value)
            blue = round(132 * (1 - value) + 132 * value)
            color = f"#{red:02x}{green:02x}{blue:02x}"
            lines.append(f'  "{node["id"]}" [label="{label}", style=filled, fillcolor="{color}"];')
        for edge in edges:
            width = 1 + math.log1p(edge["visits"])
            lines.append(f'  "{edge["source"]}" -> "{edge["target"]}" [label="{edge["action"]} ({edge["visits"]})", penwidth={width:.2f}];')
        lines.append("}")
        Path(str(prefix)+".dot").write_text("\n".join(lines))
        return data
