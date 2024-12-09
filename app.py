from flask import Flask
from extentions import db, migrate, jwt
from config import Config
from resources.user import user_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    # Register blueprints
    app.register_blueprint(user_bp, url_prefix="/api/v1/users")

    return app

app = create_app()

if __name__ == "__main__":
    # run app in debug mode on port 5000
    app.run(debug=True, port=5000)