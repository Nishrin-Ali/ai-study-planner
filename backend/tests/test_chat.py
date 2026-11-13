import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.routers.chat import detect_language, generate_fallback_reply


client = TestClient(app)


def test_detect_language():
    assert detect_language("Explain stack push and pop operations") == "en"
    assert detect_language("Dayavittu explain madi hege work agatte") == "kn"
    assert detect_language("ನಮಸ್ಕಾರ, ಇದನ್ನು ಕನ್ನಡದಲ್ಲಿ ವಿವರಿಸಿ") == "kn"
    assert detect_language("Bhaiya ye concept kaise yaad rakhein") == "hi"
    assert detect_language("नमस्ते, यह कैसे काम करता है?") == "hi"


def test_fallback_reply_generation():
    reply_en = generate_fallback_reply(
        user_message="Give an example",
        question_text="Stack Operations",
        context_material="Push and Pop operations with array implementation",
        attribution="Notes page 3",
        grounded=True,
    )
    assert len(reply_en) > 50
    assert "Stack Operations" in reply_en

    reply_kn = generate_fallback_reply(
        user_message="ದಯವಿಟ್ಟು ವಿವರಿಸಿ",
        question_text="Queue Operations",
        context_material="",
        attribution="",
        grounded=False,
    )
    assert "Queue Operations" in reply_kn


def test_chat_endpoint_graceful():
    # First create a valid plan
    plan_payload = {
        "course_code": "BCS304",
        "course_title": "Data Structures and Applications",
        "branch": "CSE",
        "semester": 3,
        "scheme": "2022",
        "num_modules": 2,
        "num_days": 2,
        "only_important_questions": False,
    }
    plan_res = client.post("/api/plan", json=plan_payload)
    assert plan_res.status_code == 201
    plan_id = plan_res.json()["plan_id"]

    # Make request to chat endpoint with stream=false
    payload = {
        "plan_id": plan_id,
        "question_text": "Singly Linked List",
        "user_message": "Explain simply like a senior",
        "history": [],
        "stream": False,
    }
    res = client.post("/api/chat", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "reply" in data
    assert len(data["reply"]) > 20
    assert "source_attribution" in data
