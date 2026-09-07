from __future__ import annotations

from pathlib import Path

from asme.evaluation import evaluate_output


def test_builtin_answer_tag_and_exact_match_programs_are_real_subprocesses() -> None:
    root = Path(__file__).parents[1]
    result = evaluate_output(
        returned_output="work\n<answer>42</answer>\n",
        expected="42",
        extractor=root / "scripts/extractors/answer_tag.py",
        scorer=root / "scripts/scorers/exact_match.py",
    )
    assert result.valid and result.prediction == "42" and result.score == 1.0


def test_builtin_answer_tag_refuses_ambiguous_output_without_a_score() -> None:
    root = Path(__file__).parents[1]
    result = evaluate_output(
        returned_output="<answer>one</answer><answer>two</answer>",
        expected="one",
        extractor=root / "scripts/extractors/answer_tag.py",
        scorer=root / "scripts/scorers/exact_match.py",
    )
    assert not result.valid and result.score is None
