"""Unit tests for the question-bank YAML loader."""

from pathlib import Path

from app.quiz.bank import load_bank

BANK = """
rubrics:
  - name: short_answer_default
    version: 1
    dimensions:
      - {key: correctness, description: "correct", weight: 0.7}
      - {key: clarity, description: "clear", weight: 0.3}
questions:
  - key: q-one
    kind: mcq
    topic_ids: [llm.attention]
    difficulty: 2
    text: "Why scale by sqrt(d_k)?"
    options: ["a", "b"]
    answer: {correct_index: 1}
  - kind: short
    topic_ids: [ret.hybrid_fusion]
    text: "Why RRF?"
    answer: {reference: "scale-free"}
    rubric: short_answer_default
"""


def test_load_bank_parses_rubrics_and_questions(tmp_path: Path) -> None:
    path = tmp_path / "bank.yaml"
    path.write_text(BANK, encoding="utf-8")
    bank = load_bank(path)

    assert len(bank.rubrics) == 1
    assert bank.rubrics[0].dimensions[0].key == "correctness"

    assert len(bank.questions) == 2
    assert bank.questions[0].kind == "mcq"
    assert bank.questions[0].ext_key() == "q-one"  # explicit key
    # derived key when none given, and stable for the same text
    derived = bank.questions[1].ext_key()
    assert derived.startswith("q_")
    assert derived == bank.questions[1].ext_key()
