import os
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

# Flask configuration
FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')

# Supabase configuration
SUPABASE_URL = "https://ebbdd2e41a3afd79739e1926.supabase.co"
# Use anon key instead of service role key for client-side operations
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImViYmRkMmU0MWEzYWZkNzk3MzllMTkyNiIsInJvbGUiOiJhbm9uIiwiaWF0IjoxNzA1NDY2NTQ5LCJleHAiOjIwMjEwNDI1NDl9.sbp_12194f2d1f5773c7ca30a446c080ebec560acc53"

# Initialize Supabase client
try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("Successfully connected to Supabase")
except Exception as e:
    print(f"Error connecting to Supabase: {str(e)}")
    raise

# Database configuration
SQLALCHEMY_DATABASE_URI = 'sqlite:///books.db'
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Upload configuration
UPLOAD_FOLDER = 'uploads'
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

# Create required directories
REQUIRED_DIRS = ['uploads', 'outputs', 'stitched_content', 'data']
for directory in REQUIRED_DIRS:
    os.makedirs(directory, exist_ok=True) 