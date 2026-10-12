# Leduc Poker

Projekt zawiera deterministyczny silnik Leduc Poker dla 2–3 graczy, hot-seat CLI, agenta IS-MCTS i bazowego agenta losowego. Dalsze prace obejmują RL oraz turnieje porównawcze.

## Struktura

- `leduc/` — silnik, renderer, CLI, agenci oraz ewaluator.
- `tests/` — testy silnika, renderowania, agentów i ewaluacji.
- `requirements-dev.txt` — zależność testowa `pytest`.

## Uruchomienie

```powershell
python -m leduc.play --players 3 --seed 123
python -m pytest -q
```

## Gra z agentem

```powershell
python -m leduc.play --players 3 --seed 123 --ai-seats 1,2 --n-sims 200
python -m leduc.play --players 3 --seed 123 --ai-seats 0,1,2 --debug
python -m leduc.evaluate --players 3 --n-sims 1000 --opponents ismcts --opp-n-sims 100 --hands 2000 --seed 2026 --workers 4
```

`--debug` pokazuje wszystkie karty oraz odwiedziny, średnią wypłatę w żetonach każdej legalnej akcji korzenia i czas decyzji AI. Wypłaty mają format `Wyplaty: Gracz 0: -3, Gracz 1: +3/2`.

Pełny opis reguł, API, agentów i ewaluacji: [`leduc/README.md`](leduc/README.md).
