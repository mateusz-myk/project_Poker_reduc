"""Evaluate IS-MCTS against random play, optionally with paired comparisons."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import math
import statistics
import time

from .engine import GameEngine
from .agents import ISMCTSAgent, RandomAgent
from .agents.runner import play_hand


def _summary(values):
    mean = statistics.fmean(values)
    sd = statistics.stdev(values) if len(values) > 1 else 0.0
    return {"mean_payoff": mean, "ci95": 1.96 * sd / math.sqrt(len(values))}


def _run_config(index, seed, n_sims, c, players):
    seat = index % players
    game_seed = seed + index
    env = GameEngine(game_seed, players)
    agents = []
    for player in range(players):
        if player == seat:
            agents.append(ISMCTSAgent(n_sims=n_sims, c=c, seed=seed * 1000003 + index))
        else:
            agents.append(RandomAgent(seed=seed * 2000003 + index * players + player))
    payoff = play_hand(env, agents)
    timing = sum(a.last_stats["elapsed_seconds"] for a in agents if isinstance(a, ISMCTSAgent))
    return float(payoff[seat]), timing


def _evaluate_worker(job):
    return _run_config(*job)


def _evaluate_paired_worker(job):
    index, seed, players, n_sims_a, c_a, n_sims_b, c_b = job
    # Same deal, seat, random opponents, and agent RNG seed for both configurations.
    payoff_a, time_a = _run_config(index, seed, n_sims_a, c_a, players)
    payoff_b, time_b = _run_config(index, seed, n_sims_b, c_b, players)
    return payoff_a, payoff_b, time_a, time_b


def _map_jobs(worker, jobs, workers):
    if workers < 1:
        raise ValueError("workers must be at least 1")
    if workers == 1:
        return [worker(job) for job in jobs]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(worker, jobs))


def evaluate(n_sims=100, c=1.4, hands=200, players=3, seed=1, workers=1):
    started = time.perf_counter()
    jobs = [(i, seed, n_sims, c, players) for i in range(hands)]
    rows = _map_jobs(_evaluate_worker, jobs, workers)
    values = [row[0] for row in rows]
    elapsed = time.perf_counter() - started
    return {"hands": hands, "players": players, "n_sims": n_sims, "c": c, **_summary(values),
            "mean_decision_seconds": statistics.fmean(row[1] for row in rows),
            "hands_per_second": hands / elapsed if elapsed else float("inf"),
            "elapsed_seconds": elapsed, "workers": workers}


def evaluate_paired(n_sims=100, c=0.3, paired_n_sims=None, paired_c=1.4, hands=200, players=3, seed=1, workers=1):
    paired_n_sims = n_sims if paired_n_sims is None else paired_n_sims
    started = time.perf_counter()
    jobs = [(i, seed, players, n_sims, c, paired_n_sims, paired_c) for i in range(hands)]
    rows = _map_jobs(_evaluate_paired_worker, jobs, workers)
    values_a = [row[0] for row in rows]
    values_b = [row[1] for row in rows]
    differences = [a - b for a, b in zip(values_a, values_b)]
    elapsed = time.perf_counter() - started
    return {"hands": hands, "players": players, "workers": workers,
            "configuration_a": {"n_sims": n_sims, "c": c, **_summary(values_a)},
            "configuration_b": {"n_sims": paired_n_sims, "c": paired_c, **_summary(values_b)},
            "mean_difference_a_minus_b": statistics.fmean(differences),
            "ci95_difference": _summary(differences)["ci95"],
            "mean_decision_seconds_a": statistics.fmean(row[2] for row in rows),
            "mean_decision_seconds_b": statistics.fmean(row[3] for row in rows),
            "hands_per_second": hands / elapsed if elapsed else float("inf"), "elapsed_seconds": elapsed}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-sims", type=int, default=100)
    parser.add_argument("--c", type=float, default=1.4)
    parser.add_argument("--hands", type=int, default=200)
    parser.add_argument("--players", type=int, default=3)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--paired-c", type=float)
    parser.add_argument("--paired-n-sims", type=int)
    args = parser.parse_args(argv)
    common = {"hands": args.hands, "players": args.players, "seed": args.seed, "workers": args.workers}
    if args.paired_c is not None or args.paired_n_sims is not None:
        print(evaluate_paired(args.n_sims, args.c, args.paired_n_sims,
                              args.paired_c if args.paired_c is not None else args.c, **common))
    else:
        print(evaluate(args.n_sims, args.c, **common))

if __name__ == "__main__":
    main()
