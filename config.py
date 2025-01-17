import os
from dotenv import load_dotenv

load_dotenv()

# Supabase Configuration
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://ebbdd2e41a3afd79739e1926.supabase.co')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', 'sbp_ebbdd2e41a3afd79739e1926582987254e50de59')

# Flask Configuration
FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')

# Database Configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///books.db')

# Upload Configuration
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

# Create required directories
REQUIRED_DIRS = ['uploads', 'outputs', 'stitched_content', 'data']
for directory in REQUIRED_DIRS:
    os.makedirs(directory, exist_ok=True) 