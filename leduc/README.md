# Leduc Poker

Uruchom hot-seat: `python -m leduc.play --players 3 --seed 123`. `--ascii` wymusza ASCII; `--unicode` pokazuje ♡ ♧ ♢, a `--debug` ujawnia karty zakryte na potrzeby testowania. Unicode jest domyślnie wyłączony; `--no-color` pozostaje dla zgodności opcji (ANSI nie jest używany).

Renderer przyjmuje, że symbole ♡ i ♧ (Unicode East Asian Width `A`, Ambiguous) oraz ♢ (`N`, Neutral) zajmują po jednej kolumnie, zgodnie z typowym terminalem Windows. Szerokość oblicza helper `visible_len` według tego założenia. Jeśli używana czcionka wyświetla symbole inaczej, wybierz `--ascii`.

Silnik udostępnia sekwencyjne API `GameEngine`: `current_player()`, `legal_actions(player_id)`, `step(action)`, `observe(player_id)`, `copy()`, `is_terminal()` i `payoffs()`. Kolory indeksowane są w stałej kolejności: serce, trefl, karo. Remis dzieli pulę dokładnie po równo: każdy zwycięzca otrzymuje udział będący ułamkiem dokładnym (`Fraction`), a wypłata odejmuje wpłaty gracza. Suma wypłat jest dokładnie równa zero.

