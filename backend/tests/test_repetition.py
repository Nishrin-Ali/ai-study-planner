import pytest
from app.services.papers.repetition import (
    _clean_tokens,
    _token_jaccard_similarity,
    cluster_questions_algorithmically,
)


def test_token_extraction_and_jaccard():
    t1 = _clean_tokens("Explain singly linked list insertion and deletion with code.")
    t2 = _clean_tokens("Describe singly linked list with insertion and deletion operations.")
    sim = _token_jaccard_similarity(t1, t2)
    assert sim > 0.4, f"Expected high similarity between related linked list questions, got {sim}"

    t3 = _clean_tokens("State and prove Bayes theorem with an example.")
    sim_unrelated = _token_jaccard_similarity(t1, t3)
    assert sim_unrelated < 0.2, f"Expected low similarity between linked list and Bayes theorem, got {sim_unrelated}"


def test_cluster_questions_algorithmically():
    sample_questions = [
        {
            "session": "Jan/Feb 2023",
            "text": "Explain stack operations push and pop with array implementation.",
            "marks": 10,
            "paper_id": "seed_bcs304_jan2023",
            "page_number": 1,
        },
        {
            "session": "Jul/Aug 2023",
            "text": "Define stack. Explain push and pop operations with an algorithm.",
            "marks": 8,
            "paper_id": "seed_bcs304_jul2023",
            "page_number": 1,
        },
        {
            "session": "Jan/Feb 2024",
            "text": "Explain circular queue operations with suitable diagram.",
            "marks": 10,
            "paper_id": "seed_bcs304_jan2024",
            "page_number": 1,
        },
    ]

    clusters = cluster_questions_algorithmically(module=2, session_questions=sample_questions)
    assert len(clusters) >= 2, "Expected 2 distinct concept clusters (stack vs queue)"

    # Stack question appeared in 2 sessions
    stack_cluster = next((c for c in clusters if "stack" in c.canonical_question.lower()), None)
    assert stack_cluster is not None
    assert stack_cluster.repetition_count == 2
    assert stack_cluster.repetition_label == "2 times"
    assert len(stack_cluster.sessions) == 2
    assert "Jan/Feb 2023" in stack_cluster.sessions
    assert "Jul/Aug 2023" in stack_cluster.sessions
    assert len(stack_cluster.paper_ids) == 2
