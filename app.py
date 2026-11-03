import re

from flask import Flask, redirect, render_template, request, session, url_for
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from config import Config
from extentions import db, jwt, migrate
from models import User
from resources.user import user_bp


EMAIL_PATTERN = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
USERNAME_PATTERN = re.compile(r"[A-Za-z0-9_]{3,20}")
ALLOWED_GENDERS = {"female", "male", "other"}


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    app.register_blueprint(user_bp, url_prefix="/api/v1/users")

    @app.route("/", methods=["GET", "POST"])
    def login():
        message = ""
        if request.method == "POST":
            username = request.form.get("username", "").strip().lower()
            password = request.form.get("password", "")

            if not username or not password:
                message = "Please fill out the form!"
            else:
                account = User.query.filter_by(username=username).first()
                if account is not None and account.check_password(password):
                    session.clear()
                    session["user_id"] = account.id
                    session["username"] = account.username
                    return redirect(url_for("home"))
                message = "Incorrect username or password"

        return render_template("index.html", msg=message)

    @app.route("/register", methods=["GET", "POST"])
    def register():
        message = ""
        if request.method == "POST":
            username = request.form.get("username", "").strip().lower()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            name = request.form.get("name", "").strip()
            gender = request.form.get("gender", "").strip().lower()

            if not all((username, email, password, name, gender)):
                message = "Please fill out the form!"
            elif not USERNAME_PATTERN.fullmatch(username):
                message = "Username must be 3-20 letters, numbers, or underscores."
            elif len(email) > 30 or not EMAIL_PATTERN.fullmatch(email):
                message = "Please enter a valid email address (maximum 30 characters)."
            elif len(password) < 8:
                message = "Password must be at least 8 characters."
            elif len(name) > 50:
                message = "Name must be 50 characters or fewer."
            elif gender not in ALLOWED_GENDERS:
                message = "Please select a valid gender."
            else:
                account = User.query.filter(
                    or_(User.username == username, User.email == email)
                ).first()
                if account is not None:
                    message = "An account with that username or email already exists."
                else:
                    account = User(
                        username=username,
                        email=email,
                        name=name,
                        gender=gender,
                    )
                    account.set_password(password)
                    db.session.add(account)
                    try:
                        db.session.commit()
                    except IntegrityError:
                        db.session.rollback()
                        message = "An account with that username or email already exists."
                    else:
                        message = "You have successfully registered!"

        return render_template("register.html", msg=message)

    @app.route("/home")
    def home():
        if "user_id" not in session:
            return redirect(url_for("login"))
        return render_template("home.html", username=session["username"])

    @app.route("/profile")
    def profile():
        user_id = session.get("user_id")
        if user_id is None:
            return redirect(url_for("login"))

        account = db.session.get(User, user_id)
        if account is None:
            session.clear()
            return redirect(url_for("login"))

        return render_template("profile.html", account=account)

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=False, port=5000)
