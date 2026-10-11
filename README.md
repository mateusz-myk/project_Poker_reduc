# Leduc Poker

## Cel projektu

Projekt buduje niezależny, deterministyczny silnik Leduc Poker dla 2–8 graczy z hot-seat CLI i testami. Docelowe prace badawcze obejmują agentów IS-MCTS i RL oraz turnieje porównawcze; agenci nie są jeszcze zaimplementowani.

## Struktura

- `leduc/` — silnik, renderer, CLI i szczegóły reguł.
- `tests/test_leduc*.py` — testy silnika, wizualizacji, logów i rozliczeń.
- `requirements-dev.txt` — zależność testowa `pytest`.

## Uruchomienie

Z katalogu projektu:

```powershell
python -m leduc.play --players 3 --seed 123
```

Uruchom testy:

```powershell
python -m pytest -q
```

Dokumentacja zasad i API znajduje się w [`leduc/README.md`](leduc/README.md).
