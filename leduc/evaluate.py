"""Evaluate IS-MCTS against random or IS-MCTS opponents."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import math
import statistics
import time

from .engine import GameEngine
from .agents import ISMCTSAgent, RandomAgent
from .agents.runner import play_hand


class _TimedISMCTSAgent(ISMCTSAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.decision_times = []

    def act(self, observation, legal_actions):
        action = super().act(observation, legal_actions)
        self.decision_times.append(self.last_stats["elapsed_seconds"])
        return action


def _summary(values):
    mean = statistics.fmean(values)
    sd = statistics.stdev(values) if len(values) > 1 else 0.0
    return {"mean_payoff": mean, "ci95": 1.96 * sd / math.sqrt(len(values))}


def _agent_seed(seed, index, seat, kind):
    salt = 0xA0761D6478BD642F if kind == "A" else 0xE7037ED1A0B428DB
    return (int(seed) * 1000003 + index * 9176 + seat * 65537 + salt) & ((1 << 64) - 1)


def _run_config(index, seed, n_sims, c, players, opponents="random", opp_n_sims=None, opp_c=None):
    if opponents not in ("random", "ismcts"):
        raise ValueError("opponents must be 'random' or 'ismcts'")
    opp_n_sims = n_sims if opp_n_sims is None else opp_n_sims
    opp_c = c if opp_c is None else opp_c
    seat_a = index % players
    env = GameEngine(seed + index, players)
    agents = []
    for seat in range(players):
        if seat == seat_a:
            agents.append(_TimedISMCTSAgent(n_sims=n_sims, c=c, seed=_agent_seed(seed, index, seat, "A")))
        elif opponents == "ismcts":
            agents.append(_TimedISMCTSAgent(n_sims=opp_n_sims, c=opp_c, seed=_agent_seed(seed, index, seat, "B")))
        else:
            agents.append(RandomAgent(seed=(seed * 2000003 + index * players + seat) & ((1 << 64) - 1)))
    payoffs = tuple(play_hand(env, agents))
    assert sum(payoffs) == 0
    a_time = statistics.fmean(agents[seat_a].decision_times)
    b_times = [statistics.fmean(agent.decision_times) for seat, agent in enumerate(agents)
               if seat != seat_a and isinstance(agent, _TimedISMCTSAgent) and agent.decision_times]
    b_time = statistics.fmean(b_times) if b_times else None
    return {"payoffs": payoffs, "seat_a": seat_a, "a_time": a_time, "b_time": b_time}


def _evaluate_worker(job):
    return _run_config(*job)


def _evaluate_paired_worker(job):
    index, seed, players, n_sims_a, c_a, n_sims_b, c_b, opponents, opp_n_sims, opp_c = job
    result_a = _run_config(index, seed, n_sims_a, c_a, players, opponents, opp_n_sims, opp_c)
    result_b = _run_config(index, seed, n_sims_b, c_b, players, opponents, opp_n_sims, opp_c)
    return result_a, result_b


def _map_jobs(worker, jobs, workers):
    if workers < 1:
        raise ValueError("workers must be at least 1")
    if workers == 1:
        return [worker(job) for job in jobs]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(worker, jobs))


def _seat_summary(rows, seat):
    values = [float(row["payoffs"][seat]) for row in rows if row["seat_a"] == seat]
    return {"hands": len(values), **_summary(values)} if values else {"hands": 0, "mean_payoff": None, "ci95": None}


def evaluate(n_sims=100, c=1.4, hands=200, players=3, seed=1, workers=1, opponents="random", opp_n_sims=None, opp_c=None):
    if players not in (2, 3):
        raise ValueError("players must be 2 or 3")
    if opponents not in ("random", "ismcts"):
        raise ValueError("opponents must be 'random' or 'ismcts'")
    started = time.perf_counter()
    jobs = [(i, seed, n_sims, c, players, opponents, opp_n_sims, opp_c) for i in range(hands)]
    rows = _map_jobs(_evaluate_worker, jobs, workers)
    elapsed = time.perf_counter() - started
    values = [float(row["payoffs"][row["seat_a"]]) for row in rows]
    a_times = [row["a_time"] for row in rows]
    b_times = [row["b_time"] for row in rows if row["b_time"] is not None]
    return {"hands": hands, "players": players, "n_sims": n_sims, "c": c, "opponents": opponents,
            "opp_n_sims": opp_n_sims if opp_n_sims is not None else n_sims,
            "opp_c": opp_c if opp_c is not None else c, **_summary(values),
            "mean_payoff_by_seat": {str(seat): _seat_summary(rows, seat) for seat in range(players)},
            "mean_decision_seconds_a": statistics.fmean(a_times),
            "mean_decision_seconds_b": statistics.fmean(b_times) if b_times else None,
            "hands_per_second": hands / elapsed if elapsed else float("inf"),
            "elapsed_seconds": elapsed, "workers": workers}


def evaluate_paired(n_sims=100, c=0.3, paired_n_sims=None, paired_c=1.4, hands=200, players=3, seed=1, workers=1, opponents="random", opp_n_sims=None, opp_c=None):
    paired_n_sims = n_sims if paired_n_sims is None else paired_n_sims
    started = time.perf_counter()
    jobs = [(i, seed, players, n_sims, c, paired_n_sims, paired_c, opponents, opp_n_sims, opp_c) for i in range(hands)]
    rows = _map_jobs(_evaluate_paired_worker, jobs, workers)
    values_a = [float(row[0]["payoffs"][row[0]["seat_a"]]) for row in rows]
    values_b = [float(row[1]["payoffs"][row[1]["seat_a"]]) for row in rows]
    differences = [a - b for a, b in zip(values_a, values_b)]
    elapsed = time.perf_counter() - started
    return {"hands": hands, "players": players, "workers": workers, "opponents": opponents,
            "configuration_a": {"n_sims": n_sims, "c": c, **_summary(values_a)},
            "configuration_b": {"n_sims": paired_n_sims, "c": paired_c, **_summary(values_b)},
            "mean_difference_a_minus_b": statistics.fmean(differences),
            "ci95_difference": _summary(differences)["ci95"],
            "hands_per_second": hands / elapsed if elapsed else float("inf"), "elapsed_seconds": elapsed}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-sims", type=int, default=100)
    parser.add_argument("--c", type=float, default=1.4)
    parser.add_argument("--hands", type=int, default=200)
    parser.add_argument("--players", type=int, choices=(2, 3), default=3)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--opponents", choices=("random", "ismcts"), default="random")
    parser.add_argument("--opp-n-sims", type=int)
    parser.add_argument("--opp-c", type=float)
    parser.add_argument("--paired-c", type=float)
    parser.add_argument("--paired-n-sims", type=int)
    args = parser.parse_args(argv)
    common = {"hands": args.hands, "players": args.players, "seed": args.seed, "workers": args.workers,
              "opponents": args.opponents, "opp_n_sims": args.opp_n_sims, "opp_c": args.opp_c}
    if args.paired_c is not None or args.paired_n_sims is not None:
        print(evaluate_paired(args.n_sims, args.c, args.paired_n_sims,
                              args.paired_c if args.paired_c is not None else args.c, **common))
    else:
        print(evaluate(args.n_sims, args.c, **common))

if __name__ == "__main__":
    main()
