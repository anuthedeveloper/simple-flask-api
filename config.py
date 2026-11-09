import os
import secrets
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_hex(32)
    
    DATABASE_URI = os.getenv('DATABASE_URI', 'sqlite:///testapidb.db')
    # Support PostgreSQL through Psycopg 3.
    if DATABASE_URI.startswith("postgres://"):
        DATABASE_URI = DATABASE_URI.replace(
            "postgres://",
            "postgresql+psycopg://",
            1
        )
    elif DATABASE_URI.startswith("postgresql://"):
        DATABASE_URI = DATABASE_URI.replace(
            "postgresql://",
            "postgresql+psycopg://",
            1
        )

    SQLALCHEMY_DATABASE_URI = DATABASE_URI
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SQLALCHEMY_ENGINE_OPTIONS = (
        {
            "pool_pre_ping": True,
            "pool_recycle": 300,
            "pool_size": 1,
            "max_overflow": 0,
        }
        if DATABASE_URI.startswith("postgresql")
        else {}
    )
   
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY") or SECRET_KEY

