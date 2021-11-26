from flask import Flask
from flask import jsonify
from flask_sqlalchemy import SQLAlchemy
from flask.globals import request
import datetime
app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db' 
db = SQLAlchemy(app)

class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), unique=True, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def __repr__(self):
        return f"{self.name} - {self.gender}" 

# json_data = [{"name": "James Brown", "gender": "Male"}, {"name":"Toluwani Johnson", "gender": "Female"}, {"name": "John Cena", "gender": "Male"}]

@app.route('/')
def index():
    return jsonify({"status":"success", "Success":"Welcome to Flask API Endpoint"})

@app.route('/users')
def get_all_users():
    # users = Users.query.filter(User.gender.endswith('ale')).all() # filter users 
    # users = Users.query.order_by(User.id).all() 
    # users = Users.query.limit(1).all() # limit user to 1 record
    users = Users.query.all()
    output = []
    for user in users:
        user_data = {'id': user.id, 'name': user.name, 'gender': user.gender, 'created_at': user.created_at}

        output.append(user_data)
    return jsonify(output)

@app.route('/users/<id>')
def get_user(id):
    user = Users.query.get_or_404(id)
    return jsonify({"name": user.name, "gender":user.gender})

@app.route('/users', methods=['POST'])
def create_user():
    user_exists = Users.query.filter_by(name=request.json['name']).first()
    if user_exists is None:
        user = Users(name=request.json['name'], gender=request.json['gender'])
        db.session.add(user)
        db.session.commit()
        return {"status":"success", "id": user.id}
    else:
        return jsonify({"status":"error", "Error":"User already exists"})


@app.route('/users/<id>', methods=['DELETE'])
def delete_user(id):
    user = Users.query.get(id)
    if user is None:
        return jsonify({"status":"error", "Error":"Data not found"})
    db.session.delete(user)
    db.session.commit()
    return {"status": "success", "Success":"Delete is success"}

@app.route('/users', methods=['PATCH'])
def update_user():
    # json_data = request.json
    user_id = request.json['id']
    user = Users.query.get(user_id)
    if user is None:
        return jsonify({"status":"error", "Error":"Data not found"})
    db.session.query(Users).filter(Users.id == user_id).update(request.json)
    db.session.commit()
    return {"status": "success", "Success":"Update is success"}


# if __name__ == '__main__':
#     # run app in debug mode on port 5000
#     app.run(debug=True, port=5000)