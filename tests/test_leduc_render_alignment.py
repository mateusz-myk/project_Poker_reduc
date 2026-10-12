from leduc.engine import GameEngine
from leduc.render import compact_card, render_showdown, render_table, visible_len


def _fold_one_player(game):
    game.step("raise")
    while sum(not folded for folded in game.folded) > 1:
        game.step("fold")


def _columns(lines, words):
    return {word: [line.index(word) for line in lines] for word in words}


def test_table_columns_are_fixed_for_ai_fold_player_count_and_card_modes():
    for players in (2, 3):
        for unicode in (False, True):
            game = GameEngine(317, n_players=players)
            _fold_one_player(game)
            for ai_seats in ((), (0,), tuple(range(players))):
                observer = next(i for i, folded in enumerate(game.folded) if not folded)
                table = render_table(game.observe(observer), players,
                                     game.bet_size, unicode, game=game, ai_seats=ai_seats)
                assert "Bet " not in table
                assert "Zaklad " in table
                assert all("AI" not in line or "Gracz " in line for line in table.splitlines())
                rows = [line for line in table.splitlines() if "Gracz " in line and ("aktywny" in line or "FOLD" in line)]
                assert len(rows) == players
                assert len(set(line.index("aktywny") if "aktywny" in line else line.index("FOLD") for line in rows)) == 1
                assert len(set(line.index("[--]") if "[--]" in line else line.index("[??]") if "[??]" in line else line.index("[", 2) for line in rows)) == 1
                for seat, row in enumerate(rows):
                    assert f"Gracz {seat} (AI):" in row if seat in ai_seats else f"Gracz {seat}:" in row
                    if not game.folded[seat]:
                        assert "aktywny" in row
                folded = next(i for i, is_folded in enumerate(game.folded) if is_folded)
                assert compact_card(game.private_cards[folded], unicode) not in table
                assert max(map(visible_len, table.splitlines())) <= 60


def test_showdown_has_fixed_columns_and_winner_lines_without_colon():
    for players in (2, 3):
        for unicode in (False, True):
            game = GameEngine(12, n_players=players)
            _fold_one_player(game)
            view = render_showdown(game, unicode)
            winner = next(i for i, folded in enumerate(game.folded) if not folded)
            assert f"Wygrywa: Gracz {winner}:" not in view
            assert f"Wygrywa: Gracz {winner}\n" in view
            folded = next(i for i, is_folded in enumerate(game.folded) if is_folded)
            assert "FOLD" in next(line for line in view.splitlines() if line.startswith(f"Gracz {folded}:"))
            assert compact_card(game.private_cards[folded], unicode) not in view


def test_all_showdown_rows_keep_detail_and_result_columns_aligned():
    for players in (2, 3):
        for unicode in (False, True):
            game = GameEngine(912, n_players=players)
            while not game.is_terminal():
                game.step("call")
            for debug in (False, True):
                rows = [line for line in render_showdown(game, unicode, debug).splitlines()
                        if line.startswith("Gracz ") and ("PARA" in line or "wysoka karta" in line or "FOLD" in line)]
                assert len(rows) == players
                assert len({line.index("PARA") if "PARA" in line else line.index("wysoka karta") if "wysoka karta" in line else line.index("FOLD") for line in rows}) == 1
                assert len({line.rfind("+") if "+" in line else line.rfind("-") for line in rows}) == 1
