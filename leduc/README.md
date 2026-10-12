# Leduc Poker

Uruchom hot-seat: `python -m leduc.play --players 3 --seed 123`. `--ascii` wymusza ASCII; `--unicode` pokazuje ♡ ♧ ♢, a `--debug` ujawnia karty zakryte na potrzeby testowania. Unicode jest domyślnie wyłączony; `--no-color` pozostaje dla zgodności opcji (ANSI nie jest używany).

Renderer przyjmuje, że symbole ♡ i ♧ (Unicode East Asian Width `A`, Ambiguous) oraz ♢ (`N`, Neutral) zajmują po jednej kolumnie, zgodnie z typowym terminalem Windows. Szerokość oblicza helper `visible_len` według tego założenia. Jeśli używana czcionka wyświetla symbole inaczej, wybierz `--ascii`.

Silnik udostępnia sekwencyjne API `GameEngine`: `current_player()`, `legal_actions(player_id)`, `step(action)`, `observe(player_id)`, `copy()`, `is_terminal()` i `payoffs()`. Kolory indeksowane są w stałej kolejności: serce, trefl, karo. Remis dzieli pulę dokładnie po równo: każdy zwycięzca otrzymuje udział będący ułamkiem dokładnym (`Fraction`), a wypłata odejmuje wpłaty gracza. Suma wypłat jest dokładnie równa zero.



## IS-MCTS agents

`leduc.agents.ISMCTSAgent` implements single-observer IS-MCTS. It samples hidden cards from the unseen deck for every simulation, keeps one public action tree for the current decision, then returns the most visited root action. `RandomAgent` is a uniform legal-action baseline, and `leduc.agents.runner.play_hand` runs a complete hand.

```python
from leduc.evaluate import evaluate
print(evaluate(n_sims=100, c=1.4, hands=200, players=3, seed=1))
```

`GameEngine.determinize(observation, rng)` creates a sampled full state without calling reset or replaying a game. The `Observation` interface has no deck-size fields, so pass `n_ranks` and `n_suits` to the method/agent when using a non-default deck. `export_tree()` writes a JSON summary and Graphviz DOT file.


### Reward scaling and evaluation

IS-MCTS scales UCB rewards to [0, 1] using the theoretical payoff range [-max_wplata, (n_players - 1) * max_wplata]. The current engine parameters give `max_wplata = ante + 2 * (2 + 4) = 13`; raw chip payoffs remain in `last_stats` and exported tree JSON. The exploration constant `c` is configurable.

Run the evaluator with multiprocessing using `python -m leduc.evaluate --n-sims 100 --c 1.4 --players 3 --hands 2000 --workers 4 --seed 123`. `--workers` does not affect deal seeds or results. For a paired comparison, add `--paired-c 1.4` or `--paired-n-sims 100`; both configurations use the same deals, seat rotation, and random-opponent seeds, and the report includes the mean paired payoff difference with a 95% confidence interval.

Showdown payout labels use `Gracz N:`, for example `Wyplaty: Gracz 0: -3, Gracz 1: +3/2`.


## Gra z agentem

Dozwolone sÄ… 2 lub 3 miejsca. `--ai-seats` wskazuje miejsca agentĂłw IS-MCTS; pozostaĹ‚e obsĹ‚uguje czĹ‚owiek. JeĹ›li wszystkie miejsca sÄ… AI, program dziaĹ‚a w trybie obserwatora; Enter przechodzi do kolejnej akcji, a `--no-pause` wyĹ›wietla rozdanie bez pauz.

```powershell
python -m leduc.play --players 3 --seed 123 --ai-seats 1,2 --n-sims 200
python -m leduc.play --players 3 --seed 123 --ai-seats 0,1,2 --debug
python -m leduc.evaluate --players 3 --n-sims 1000 --opponents ismcts --opp-n-sims 100 --hands 2000 --seed 2026 --workers 4
```

`--debug` pokazuje wszystkie karty oraz, po ruchu AI, rootowe odwiedziny i Ĺ›rednie wypĹ‚aty w ĹĽetonach dla kaĹĽdej legalnej akcji i czas decyzji. Evaluator raportuje Ĺ›redniÄ… wypĹ‚atÄ™ A z 95% przedziaĹ‚em ufnoĹ›ci, wypĹ‚atÄ™ A na kaĹĽdym miejscu, czasy decyzji A/B i rozdania na sekundÄ™.
