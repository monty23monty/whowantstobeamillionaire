import pytest

from app import create_app, db
from app.models import Game, QuestionSet


@pytest.fixture
def client():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": False,
        }
    )
    with app.app_context():
        db.create_all()
    with app.test_client() as client:
        yield client


def register(client, username="alice", password="password"):
    return client.post("/register", data={"username": username, "password": password}, follow_redirects=True)


def login(client, username="alice", password="password"):
    return client.post("/login", data={"username": username, "password": password}, follow_redirects=True)


def question_set_payload(title="General Knowledge"):
    data = {"title": title}
    for i in range(1, 16):
        data[f"q{i}_text"] = f"Question {i}?"
        data[f"q{i}_a"] = "A1"
        data[f"q{i}_b"] = "B1"
        data[f"q{i}_c"] = "C1"
        data[f"q{i}_d"] = "D1"
        data[f"q{i}_correct"] = "A"
    return data


def test_register_login_and_dashboard(client):
    register_resp = register(client)
    assert b"Account created" in register_resp.data

    login_resp = login(client)
    assert b"Your Question Sets" in login_resp.data


def test_create_question_set_requires_complete_questions(client):
    register(client)
    login(client)
    payload = question_set_payload()
    payload.pop("q15_text")
    response = client.post("/question-sets/new", data=payload, follow_redirects=True)
    assert b"Question 15: text is required." in response.data


def test_create_question_set_and_start_game(client):
    register(client)
    login(client)
    response = client.post("/question-sets/new", data=question_set_payload(), follow_redirects=True)
    assert b"Question set created." in response.data

    response = client.post("/games/new", data={"question_set_id": 1}, follow_redirects=True)
    assert b"Question 1 of 15" in response.data


def test_gameplay_win_and_loss_paths(client):
    register(client)
    login(client)
    client.post("/question-sets/new", data=question_set_payload(), follow_redirects=True)

    # Loss path: first answer wrong, should lose with zero winnings.
    client.post("/games/new", data={"question_set_id": 1}, follow_redirects=True)
    loss = client.post("/games/1", data={"choice": "B"}, follow_redirects=True)
    assert b"Game Over" in loss.data
    assert b"Final winnings: $0" in loss.data

    # Win path: answer all 15 correctly.
    client.post("/games/new", data={"question_set_id": 1}, follow_redirects=True)
    for _ in range(15):
        client.post("/games/2", data={"choice": "A"}, follow_redirects=True)
    won = client.get("/games/2", follow_redirects=True)
    assert b"won the million" in won.data
    assert b"$1000000" in won.data


def test_cannot_start_game_with_incomplete_set(client):
    register(client)
    login(client)
    payload = question_set_payload("Broken Set")
    client.post("/question-sets/new", data=payload, follow_redirects=True)

    app = client.application
    with app.app_context():
        qset = QuestionSet.query.first()
        qset.questions.pop()
        db.session.commit()

    response = client.post("/games/new", data={"question_set_id": 1}, follow_redirects=True)
    assert b"must have exactly 15 questions" in response.data

