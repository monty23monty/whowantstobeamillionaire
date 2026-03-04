from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from . import db
from .forms import validate_question_payload
from .models import Game, Question, QuestionSet, User


def init_routes(app):
    @app.route("/")
    def index():
        question_sets = QuestionSet.query.all()
        return render_template("index.html", question_sets=question_sets)

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            if not username or not password:
                flash("Username and password are required.", "error")
                return redirect(url_for("register"))
            if User.query.filter_by(username=username).first():
                flash("Username already exists.", "error")
                return redirect(url_for("register"))
            user = User(username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash("Account created. Please log in.", "success")
            return redirect(url_for("login"))
        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                login_user(user)
                return redirect(url_for("dashboard"))
            flash("Invalid credentials.", "error")
            return redirect(url_for("login"))
        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        flash("Logged out.", "success")
        return redirect(url_for("index"))

    @app.route("/dashboard")
    @login_required
    def dashboard():
        my_sets = QuestionSet.query.filter_by(user_id=current_user.id).all()
        my_games = Game.query.filter_by(user_id=current_user.id).order_by(Game.id.desc()).all()
        return render_template("dashboard.html", my_sets=my_sets, my_games=my_games)

    @app.route("/question-sets/new", methods=["GET", "POST"])
    @login_required
    def new_question_set():
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            payload = []
            for i in range(1, 16):
                payload.append(
                    {
                        "text": request.form.get(f"q{i}_text", ""),
                        "option_a": request.form.get(f"q{i}_a", ""),
                        "option_b": request.form.get(f"q{i}_b", ""),
                        "option_c": request.form.get(f"q{i}_c", ""),
                        "option_d": request.form.get(f"q{i}_d", ""),
                        "correct_option": request.form.get(f"q{i}_correct", ""),
                    }
                )
            errors = validate_question_payload(payload)
            if not title:
                flash("Question set title is required.", "error")
                return redirect(url_for("new_question_set"))
            if errors:
                for error in errors:
                    flash(error.message, "error")
                return redirect(url_for("new_question_set"))

            question_set = QuestionSet(title=title, user_id=current_user.id)
            db.session.add(question_set)
            db.session.flush()

            for order, question in enumerate(payload, start=1):
                db.session.add(
                    Question(
                        question_set_id=question_set.id,
                        text=question["text"].strip(),
                        option_a=question["option_a"].strip(),
                        option_b=question["option_b"].strip(),
                        option_c=question["option_c"].strip(),
                        option_d=question["option_d"].strip(),
                        correct_option=question["correct_option"],
                        order=order,
                    )
                )
            db.session.commit()
            flash("Question set created.", "success")
            return redirect(url_for("dashboard"))

        return render_template("new_question_set.html")

    @app.route("/games/new", methods=["GET", "POST"])
    @login_required
    def new_game():
        available_sets = QuestionSet.query.all()
        if request.method == "POST":
            set_id = request.form.get("question_set_id", type=int)
            question_set = QuestionSet.query.get_or_404(set_id)
            if len(question_set.questions) != 15:
                flash("Selected question set must have exactly 15 questions.", "error")
                return redirect(url_for("new_game"))
            game = Game(user_id=current_user.id, question_set_id=question_set.id)
            db.session.add(game)
            db.session.commit()
            return redirect(url_for("play_game", game_id=game.id))
        return render_template("new_game.html", question_sets=available_sets)

    @app.route("/games/<int:game_id>", methods=["GET", "POST"])
    @login_required
    def play_game(game_id):
        game = Game.query.get_or_404(game_id)
        if game.user_id != current_user.id:
            flash("You can only play your own games.", "error")
            return redirect(url_for("dashboard"))

        questions = sorted(game.question_set.questions, key=lambda q: q.order)
        if game.status != "in_progress":
            return render_template("game_over.html", game=game)

        current_index = game.current_question - 1
        current = questions[current_index]

        if request.method == "POST":
            choice = request.form.get("choice")
            if choice == current.correct_option:
                game.winnings = Game.PRIZE_LADDER[current_index]
                if game.current_question == 15:
                    game.status = "won"
                else:
                    game.current_question += 1
            else:
                game.winnings = game.checkpoint_winnings()
                game.status = "lost"
            db.session.commit()
            if game.status == "in_progress":
                return redirect(url_for("play_game", game_id=game.id))
            return redirect(url_for("play_game", game_id=game.id))

        return render_template(
            "play_game.html",
            game=game,
            question=current,
            prize=Game.PRIZE_LADDER[current_index],
        )
