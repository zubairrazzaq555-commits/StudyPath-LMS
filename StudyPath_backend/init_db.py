"""
Initialize (recreate) the SQLite database for StudyPath_backend.
This script will drop all tables and recreate them based on models registered with the app's SQLAlchemy instance.

WARNING: This will erase existing data. Make a backup before running.
"""
import os, sys
# ensure the app package path is importable when running this script from repo root
sys.path.insert(0, os.path.dirname(__file__))
from app import app
from database import db

if __name__ == '__main__':
    print("Starting DB re-initialization...")
    with app.app_context():
        print("Dropping all tables...")
        db.drop_all()
        print("Creating all tables...")
        db.create_all()
        print("Database re-initialized.\nYou may now create test users via the signup page or a helper script.")
