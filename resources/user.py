import re

from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

from extentions import db
from models import User
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity

user_bp = Blueprint("user", __name__)
EMAIL_PATTERN = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
USERNAME_PATTERN = re.compile(r"[A-Za-z0-9_]{3,20}")
ALLOWED_GENDERS = {"female", "male", "other"}

@user_bp.route('/', methods=["GET"])
def get_all_users():
    users = User.query.order_by(User.created_at).all()
    output = []
    for user in users:
        user_data = {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "gender": user.gender,
            "created_at": user.created_at,
        }
        output.append(user_data)
    return jsonify(output)


@user_bp.route('/<int:id>', methods=["GET"])
def get_user(id):
    user = User.query.get_or_404(id)
    return jsonify({"email": user.email, "name": user.name, "gender": user.gender})


@user_bp.route('/', methods=['POST'])
def create_user():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"status": "error", "error": "A JSON object is required"}), 400

    email = data.get("email")
    password = data.get("password")
    name = data.get("name")
    gender = data.get("gender")
    username = data.get("username")
    if not all(isinstance(value, str) and value.strip() for value in (email, password, name, gender)):
        return jsonify({"status": "error", "error": "Email, password, name, and gender are required"}), 400

    email = email.strip().lower()
    name = name.strip()
    gender = gender.strip().lower()
    if len(email) > 30 or not EMAIL_PATTERN.fullmatch(email):
        return jsonify({"status": "error", "error": "Invalid email address"}), 400
    if len(password) < 8:
        return jsonify({"status": "error", "error": "Password must be at least 8 characters"}), 400
    if len(name) > 50:
        return jsonify({"status": "error", "error": "Name must be 50 characters or fewer"}), 400
    if gender not in ALLOWED_GENDERS:
        return jsonify({"status": "error", "error": "Invalid gender"}), 400
    if username is not None:
        if not isinstance(username, str) or not USERNAME_PATTERN.fullmatch(username.strip()):
            return jsonify({"status": "error", "error": "Invalid username"}), 400
        username = username.strip().lower()

    user = User(email=email, username=username, name=name, gender=gender)
    user.set_password(password)
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"status": "error", "error": "An account with that email or username already exists"}), 409

    return jsonify({"status": "success", "success": "User created successfully", "id": user.id}), 201


@user_bp.route('/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    try:
        requesting_user_id = int(get_jwt_identity())
    except (TypeError, ValueError):
        return jsonify({"status": "error", "error": "Invalid token identity"}), 401
    if requesting_user_id != user_id:
        return jsonify({"status": "error", "error": "You can only delete your own account"}), 403

    user = db.session.get(User, user_id)
    if user is None:
        return jsonify({"status": "error", "error": "User not found"}), 404

    db.session.delete(user)
    db.session.commit()
    return jsonify({"status": "success", "success": "User deleted successfully"}), 200


@user_bp.route('/', methods=['PATCH'])
@jwt_required()
def update_user():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or type(data.get("id")) is not int:
        return jsonify({"status": "error", "error": "A JSON object with an integer id is required"}), 400

    allowed_fields = {"email", "gender", "name", "password", "username"}
    fields = set(data) - {"id"}
    if not fields or not fields.issubset(allowed_fields):
        return jsonify({"status": "error", "error": "No valid profile fields provided"}), 400

    user_id = data["id"]
    try:
        requesting_user_id = int(get_jwt_identity())
    except (TypeError, ValueError):
        return jsonify({"status": "error", "error": "Invalid token identity"}), 401
    if requesting_user_id != user_id:
        return jsonify({"status": "error", "error": "You can only update your own account"}), 403

    user = db.session.get(User, user_id)
    if user is None:
        return jsonify({"status": "error", "error": "User not found"}), 404

    if "email" in fields:
        email = data["email"]
        if not isinstance(email, str):
            return jsonify({"status": "error", "error": "Invalid email address"}), 400
        email = email.strip().lower()
        if len(email) > 30 or not EMAIL_PATTERN.fullmatch(email):
            return jsonify({"status": "error", "error": "Invalid email address"}), 400
        user.email = email

    if "name" in fields:
        name = data["name"]
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > 50:
            return jsonify({"status": "error", "error": "Invalid name"}), 400
        user.name = name.strip()

    if "gender" in fields:
        gender = data["gender"]
        if not isinstance(gender, str) or gender.strip().lower() not in ALLOWED_GENDERS:
            return jsonify({"status": "error", "error": "Invalid gender"}), 400
        user.gender = gender.strip().lower()

    if "username" in fields:
        username = data["username"]
        if not isinstance(username, str) or not USERNAME_PATTERN.fullmatch(username.strip()):
            return jsonify({"status": "error", "error": "Invalid username"}), 400
        user.username = username.strip().lower()

    if "password" in fields:
        password = data["password"]
        if not isinstance(password, str) or len(password) < 8:
            return jsonify({"status": "error", "error": "Password must be at least 8 characters"}), 400
        user.set_password(password)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"status": "error", "error": "An account with that email or username already exists"}), 409

    return jsonify({"status": "success", "success": "User updated successfully"}), 200

# Auth
@user_bp.route("/login", methods=['POST'])
def login():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get("email"), str) or not isinstance(data.get("password"), str):
        return jsonify({"status": "error", "error": "Email and password are required"}), 400

    email = data["email"].strip().lower()
    user = User.query.filter_by(email=email).first()
    if user is None or not user.check_password(data["password"]):
        return jsonify({"status": "error", "error": "Invalid credentials"}), 401

    access_token = create_access_token(identity=str(user.id))
    return jsonify({"status": "success", "token": access_token}), 200

@user_bp.route("/profile", methods=["GET"])
@jwt_required()
def profile():
    try:
        user_id = int(get_jwt_identity())
    except (TypeError, ValueError):
        return jsonify({"status": "error", "error": "Invalid token identity"}), 401

    user = db.session.get(User, user_id)
    if user is None:
        return jsonify({"status": "error", "error": "User not found"}), 404

    return jsonify({
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "name": user.name,
            "gender": user.gender,
        }
    }), 200
