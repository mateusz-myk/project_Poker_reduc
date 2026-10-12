"""Focused tests for IS-MCTS review fixes."""
import shutil
import subprocess

from leduc.agents.ismcts import ISMCTSAgent
from leduc.engine import Card, GameEngine
from leduc.evaluate import evaluate, evaluate_paired
from leduc.render import render_showdown, render_table


def test_dot_export_is_line_separated_and_graphviz_parseable(tmp_path):
    game = GameEngine(734)
    agent = ISMCTSAgent(n_sims=24, seed=13)
    agent.act(game.observe(0), game.legal_actions(0))
    dot_path = tmp_path / "tree.dot"
    output = agent.export_tree(prefix=str(tmp_path / "tree"))
    text = dot_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    assert lines[0] == "digraph ISMCTS {"
    assert lines[-1] == "}"
    assert len(lines) == len(output["nodes"]) + len(output["edges"]) + 3
    assert "\\nN=" in text  # escaped line break is retained inside node labels
    assert not any(line in ("\n", "\\n") for line in lines)
    dot = shutil.which("dot")
    if dot:
        svg = tmp_path / "tree.svg"
        subprocess.run([dot, "-Tsvg", str(dot_path), "-o", str(svg)], check=True, capture_output=True)
        assert svg.is_file() and svg.stat().st_size > 0


def test_default_maximum_player_contribution_is_parameterized():
    assert GameEngine.max_player_contribution() == 13


def test_evaluator_worker_count_does_not_change_results():
    serial = evaluate(n_sims=10, hands=12, players=3, seed=910, workers=1)
    for workers in (2, 3):
        parallel = evaluate(n_sims=10, hands=12, players=3, seed=910, workers=workers)
        assert parallel["mean_payoff"] == serial["mean_payoff"]
        assert parallel["ci95"] == serial["ci95"]


def test_paired_evaluation_reports_paired_difference():
    result = evaluate_paired(n_sims=10, c=0.7, paired_c=1.4, hands=12, players=3, seed=911, workers=1)
    assert result["configuration_a"]["n_sims"] == result["configuration_b"]["n_sims"] == 10
    assert isinstance(result["mean_difference_a_minus_b"], float)
    assert result["ci95_difference"] >= 0


def test_player_labels_use_colon_without_pipe_wrapping():
    game = GameEngine(8, 3)
    while len(game.history) < 1:
        game.step("call")
    player = game.current_player()
    table = render_table(game.observe(player), game.n_players, game.bet_size, game=game)
    game.private_cards = [Card(1, 0), Card(1, 1), Card(0, 2)]
    game.community_card = Card(2, 0)
    game._finish((0, 1))
    showdown = render_showdown(game)
    assert "|Gracz" not in table + showdown
    assert "Remis: Gracz 0:, Gracz 1:" in showdown
    assert "Wyplaty: Gracz 0:" in showdown
