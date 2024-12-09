from flask import Blueprint, jsonify, session
from models import User
from flask.globals import request
from extentions import db
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity

# =============================
user_bp = Blueprint("user", __name__)


# @user_bp.route('/', methods=["POST", "GET"])
# def index():
#     return jsonify({"status":"success", "Success":"Welcome to Flask API Endpoint"})

@user_bp.route('/', methods=["GET"])
def get_all_users():
    # users = User.query.filter(User.gender.endswith('ale')).all() # filter users 
    # users = User.query.order_by(User.id).all() 
    # users = User.query.limit(1).all() # limit user to 1 record
    users = User.query.order_by(User.created_at).all()
    output = []
    for user in users:
        user_data = {
            'id': user.id, 'email': user.email, 'name': user.name, 
            'gender': user.gender, 'created_at': user.created_at
        }
        output.append(user_data)
    return jsonify(output)

@user_bp.route('/<int:id>', methods=["GET"])
def get_user(id):
    user = User.query.get_or_404(id)
    return jsonify({"email": user.email, "name": user.name, "gender":user.gender})

@user_bp.route('/', methods=['POST'])
def create_user():
    data = request.json
    if not data or not data["email"] or not data["password"] or not data["name"] or not data["gender"]:
        return jsonify({"status":"error", "error": "Invalid data"}), 400
    
    email_exists = User.query.filter_by(email=data['email']).first()
    if email_exists:
        return jsonify({"status":"error", "error": "User email already exists"}), 400
    
    user = User(email=data["email"], name=data["name"], gender=data["gender"])
    user.set_password(data.get("password"))
    db.session.add(user)
    db.session.commit()
    return jsonify({"status":"success", "success": "User created successfully", "id": user.id}), 201
    
@user_bp.route('/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    user = User.query.get(user_id)
    if user is None:
        return jsonify({"status":"error", "error":"User not found"}), 404
    
    db.session.delete(user)
    db.session.commit()
    return jsonify({"status": "success", "success":"User deleted successfully"}), 200

@user_bp.route('/', methods=['PATCH'])
@jwt_required()
def update_user():
    user_id = request.json['id']
    user = User.query.get(user_id)
    if user is None:
        return jsonify({"status":"error", "Error":"User not found"}), 404
    
    db.session.query(User).filter(User.id == user_id).update(request.json)
    db.session.commit()
    return jsonify({"status": "success", "Success":"User updated successfully"}), 200

# Auth
@user_bp.route("/login", methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get("email") or not data.get("password"):
        return jsonify({"status": "error", "error": "Invalid data"}), 400
    
    user_exists = User.query.filter_by(email=data['email']).first()
    if not user_exists or not user_exists.check_password(data["password"]):
        return jsonify({"status": "error", "error": "Invalid credentials"}), 401
    
    access_token = create_access_token(identity={"id":user_exists.id, "email": user_exists.email})
    return jsonify({"status": "success", "token": access_token}), 200

    
@user_bp.route("/profile", methods=["GET"])
@jwt_required()
def profile():
    current_user = get_jwt_identity()
    return jsonify({"user": current_user}), 200
