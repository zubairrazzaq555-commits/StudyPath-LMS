"""
Project-level DB initializer for StudyPath app.
This script will remove the old StudyPath_backend/database.db (if present)
and create a fresh database using the models defined in StudyPath_backend/database.py.

Run from the `studypath_app` directory:
    python init_db.py
"""
import os
import sys
import shutil
import importlib.util

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Backend directory is sibling of this folder
BACKEND_DIR = os.path.normpath(os.path.join(BASE_DIR, '..', 'StudyPath_backend'))
DB_FILE = os.path.join(BACKEND_DIR, 'database.db')

if not os.path.exists(BACKEND_DIR):
    print(f"❌ Backend directory not found: {BACKEND_DIR}")
    sys.exit(1)

# Add backend to sys.path so imports like 'engine' can be resolved
sys.path.insert(0, BACKEND_DIR)

print(f"✅ Using backend at: {BACKEND_DIR}")

# Remove existing database file (backup first)
if os.path.exists(DB_FILE):
    bak = DB_FILE + '.bak'
    print(f"📦 Backing up existing DB to {bak}")
    try:
        shutil.copy2(DB_FILE, bak)
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        sys.exit(1)
    print(f"🗑️  Removing existing DB: {DB_FILE}")
    try:
        os.remove(DB_FILE)
    except Exception as e:
        print(f"❌ Failed to remove DB file: {e}")
        sys.exit(1)

# Create a minimal Flask app and load only the database models
from flask import Flask

print("🔧 Creating minimal Flask app for initialization...")
temp_app = Flask(__name__)
temp_app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_FILE}'
temp_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

print("📥 Loading database models...")
try:
    # Load database module directly
    def load_module_from_path(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None:
            raise ImportError(f"Cannot load spec for {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module
    
    db_path = os.path.join(BACKEND_DIR, 'database.py')
    backend_db_module = load_module_from_path('backend_db', db_path)
    db = backend_db_module.db
    
except Exception as e:
    print(f"❌ Failed to load database module: {e}")
    sys.exit(1)

# Initialize the database with our minimal app
print("🔐 Initializing db with Flask app...")
db.init_app(temp_app)

print("🔨 Creating database schema...")
with temp_app.app_context():
    print("   • Dropping all existing tables...")
    db.drop_all()
    print("   • Creating all tables from models...")
    db.create_all()

print("✅ Database initialized successfully!")
print("🎉 You can now run the app or create a test user via the signup page.")

