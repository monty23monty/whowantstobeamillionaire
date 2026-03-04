from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from . import db, login_manager


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    question_sets = db.relationship("QuestionSet", backref="creator", lazy=True)
    games = db.relationship("Game", backref="player", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class QuestionSet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    questions = db.relationship("Question", backref="question_set", lazy=True, cascade="all, delete-orphan")


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_set_id = db.Column(db.Integer, db.ForeignKey("question_set.id"), nullable=False)
    text = db.Column(db.String(300), nullable=False)
    option_a = db.Column(db.String(200), nullable=False)
    option_b = db.Column(db.String(200), nullable=False)
    option_c = db.Column(db.String(200), nullable=False)
    option_d = db.Column(db.String(200), nullable=False)
    correct_option = db.Column(db.String(1), nullable=False)
    order = db.Column(db.Integer, nullable=False)


class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    question_set_id = db.Column(db.Integer, db.ForeignKey("question_set.id"), nullable=False)
    current_question = db.Column(db.Integer, default=1, nullable=False)
    status = db.Column(db.String(20), default="in_progress", nullable=False)
    winnings = db.Column(db.Integer, default=0, nullable=False)

    question_set = db.relationship("QuestionSet", lazy=True)

    PRIZE_LADDER = [
        100,
        200,
        300,
        500,
        1000,
        2000,
        4000,
        8000,
        16000,
        32000,
        64000,
        125000,
        250000,
        500000,
        1000000,
    ]

    def checkpoint_winnings(self):
        if self.current_question <= 1:
            return 0
        reached = self.current_question - 1
        if reached >= 10:
            return 32000
        if reached >= 5:
            return 1000
        return 0
