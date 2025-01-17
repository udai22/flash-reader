from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from stitch_content import ContentStitcher
import fitz  # PyMuPDF
import json
import shutil
import logging
from auth import auth
from models import db, User, Book  # Import Book from models
from config import FLASK_SECRET_KEY
from functools import wraps

# Get base directory
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(BASE_DIR, 'app.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY

# Register auth blueprint
app.register_blueprint(auth, url_prefix='/auth')

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(BASE_DIR, "books.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'outputs'), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'stitched_content'), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'data'), exist_ok=True)

# Initialize SQLAlchemy with app
db.init_app(app)

# Initialize database
with app.app_context():
    db.create_all()
    logger.info("Database initialized")

@app.after_request
def add_security_headers(response):
    """Add security headers including CSP"""
    # Add CSP header with more permissive but still secure settings
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.tailwindcss.com; "  # Allow Tailwind and necessary JS
        "style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://cdn.jsdelivr.net; "  # Allow Tailwind CSS
        "img-src 'self' data: blob:; "  # Allow data URLs for images
        "font-src 'self' data: https://cdn.tailwindcss.com; "  # Allow fonts
        "connect-src 'self' https://cdn.tailwindcss.com; "  # Allow connections to Tailwind
        "worker-src 'self' blob:; "  # Allow web workers
        "frame-src 'self'; "  # Allow iframes from same origin
        "object-src 'none'; "  # Disable object/embed tags
        "base-uri 'self'"  # Restrict base URI
    )
    # Add other security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response

def process_pdf(book_id):
    """Process the PDF and create the text version"""
    try:
        logger.info(f"Starting to process PDF for book_id: {book_id}")
        
        book = Book.query.get(book_id)
        if not book:
            logger.error(f"Book not found with id: {book_id}")
            return False

        # Update status
        book.processing_status = 'processing'
        db.session.commit()
        logger.info(f"Processing PDF file: {book.pdf_path}")

        # Verify PDF file exists
        if not os.path.exists(book.pdf_path):
            logger.error(f"PDF file not found at path: {book.pdf_path}")
            raise FileNotFoundError(f"PDF file not found: {book.pdf_path}")

        # Extract text using ContentStitcher
        stitcher = ContentStitcher()
        pdf_filename = os.path.basename(book.pdf_path)
        json_filename = f"{os.path.splitext(pdf_filename)[0]}.json"
        text_filename = f"{os.path.splitext(pdf_filename)[0]}.txt"
        text_path = os.path.join('stitched_content', text_filename)
        
        # Check if processed text already exists
        if os.path.exists(text_path):
            logger.info(f"Found existing processed text at: {text_path}")
            with open(text_path, 'r', encoding='utf-8') as f:
                content = f.read()
                word_count = len(content.split())
            
            book.text_path = text_path
            book.word_count = word_count
            book.processing_status = 'completed'
            db.session.commit()
            return True
            
        logger.info(f"Creating JSON file: {json_filename}")
        
        # First, extract text from PDF and create JSON
        doc = fitz.open(book.pdf_path)
        pages_data = []
        
        for page_num in range(len(doc)):
            logger.debug(f"Processing page {page_num + 1} of {len(doc)}")
            page = doc[page_num]
            text = page.get_text()
            
            # Create the DeepSeek-style response
            deepseek_response = {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps({
                                "content": text,
                                "page": page_num + 1,
                                "chapter": "",
                                "words": text.split()
                            })
                        }
                    }
                ]
            }
            
            # Create JSON structure for this page
            page_data = {
                "page_number": page_num + 1,
                "deepseek_output": [deepseek_response]
            }
            pages_data.append(page_data)
        
        doc.close()
        
        # Save the JSON file
        json_path = os.path.join('outputs', json_filename)
        logger.debug(f"Saving JSON with {len(pages_data)} pages")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(pages_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"JSON file created successfully at: {json_path}")
        
        # Process the file with ContentStitcher
        logger.info("Starting ContentStitcher processing")
        stitcher.stitch_content(json_filename)
        
        logger.info(f"Checking for processed text file at: {text_path}")
        
        if os.path.exists(text_path):
            # Count words
            with open(text_path, 'r', encoding='utf-8') as f:
                content = f.read()
                word_count = len(content.split())
            
            logger.info(f"Text file processed successfully. Word count: {word_count}")
            
            # Update book record
            book.text_path = text_path
            book.word_count = word_count
            book.processing_status = 'completed'
            db.session.commit()
            return True
        
        logger.error("Text file was not created by ContentStitcher")
        book.processing_status = 'failed'
        db.session.commit()
        return False

    except Exception as e:
        logger.exception(f"Error processing PDF: {str(e)}")
        if book:
            book.processing_status = 'failed'
            db.session.commit()
        return False

def get_default_books():
    """Get or create the default books for the current user"""
    user_id = session.get('user_id')
    if not user_id:
        return []

    # Create directories if they don't exist
    os.makedirs(os.path.join(BASE_DIR, 'stitched_content'), exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, 'outputs'), exist_ok=True)
    
    default_books = []
    
    # Create welcome book if it doesn't exist for this user
    welcome_book = Book.query.filter_by(title='Welcome to Flash Reader', user_id=user_id).first()
    if not welcome_book:
        default_path = os.path.join(BASE_DIR, 'stitched_content', f'welcome_{user_id}.txt')
        default_content = """Welcome to Flash Reader!

This is a modern web-based speed reading application that helps you read faster and more efficiently. You can:
- Upload your own PDF files for reading
- Adjust reading speed (WPM)
- Toggle between single word and phrase mode
- Track your progress
- Use keyboard shortcuts for easy control

Try adjusting the speed using the up/down arrow keys, or press space to start/pause reading.

To upload your own PDF, return to the home page and use the upload button. Your PDF will be processed and made available for speed reading.

Enjoy reading at your own pace!"""

        with open(default_path, 'w', encoding='utf-8') as f:
            f.write(default_content)
        
        word_count = len(default_content.split())
        
        welcome_book = Book(
            title='Welcome to Flash Reader',
            author='Flash Reader Team',
            text_path=default_path,
            pdf_path='',  # No PDF for default book
            processing_status='completed',
            word_count=word_count,
            user_id=user_id
        )
        db.session.add(welcome_book)
        db.session.commit()
        logger.info(f"Created welcome book entry for user {user_id}")
    
    default_books.append(welcome_book)

    # Create Philosophia Ultima book if it doesn't exist for this user
    philosophia_book = Book.query.filter_by(title='Philosophia Ultima', user_id=user_id).first()
    if not philosophia_book:
        # First check in outputs directory, then in data directory
        json_path = os.path.join(BASE_DIR, 'outputs', 'Philosophia_Ultima.json')
        if not os.path.exists(json_path):
            json_path = os.path.join(BASE_DIR, 'data', 'Philosophia_Ultima.json')
            # If found in data, copy to outputs
            if os.path.exists(json_path):
                os.makedirs(os.path.join(BASE_DIR, 'outputs'), exist_ok=True)
                shutil.copy2(json_path, os.path.join(BASE_DIR, 'outputs', 'Philosophia_Ultima.json'))
                json_path = os.path.join(BASE_DIR, 'outputs', 'Philosophia_Ultima.json')
        
        text_path = os.path.join(BASE_DIR, 'stitched_content', f'Philosophia_Ultima_{user_id}.txt')
        
        # Process the JSON file using ContentStitcher
        if os.path.exists(json_path):
            stitcher = ContentStitcher()
            stitcher.stitch_content('Philosophia_Ultima.json')
            
            if os.path.exists(text_path):
                with open(text_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    word_count = len(content.split())
                
                philosophia_book = Book(
                    title='Philosophia Ultima',
                    author='Osho',
                    text_path=text_path,
                    pdf_path='',  # No PDF path needed
                    processing_status='completed',
                    word_count=word_count,
                    user_id=user_id
                )
                db.session.add(philosophia_book)
                db.session.commit()
                logger.info(f"Created Philosophia Ultima book entry for user {user_id}")
    
    if philosophia_book:
        default_books.append(philosophia_book)

    # Create Cycles book if it doesn't exist for this user
    cycles_book = Book.query.filter_by(title='Cycles—The Science of Prediction', user_id=user_id).first()
    if not cycles_book:
        cycles_path = os.path.join(BASE_DIR, 'stitched_content', 'Cycles—The Science of Prediction, Edward R. Dewey.txt')
        if os.path.exists(cycles_path):
            # Create a user-specific copy
            user_cycles_path = os.path.join(BASE_DIR, 'stitched_content', f'Cycles_{user_id}.txt')
            shutil.copy2(cycles_path, user_cycles_path)
            
            with open(user_cycles_path, 'r', encoding='utf-8') as f:
                content = f.read()
                word_count = len(content.split())
            
            cycles_book = Book(
                title='Cycles—The Science of Prediction',
                author='Edward R. Dewey',
                text_path=user_cycles_path,
                pdf_path='',  # No PDF path needed
                processing_status='completed',
                word_count=word_count,
                user_id=user_id
            )
            db.session.add(cycles_book)
            db.session.commit()
            logger.info(f"Created Cycles book entry for user {user_id}")
    
    if cycles_book:
        default_books.append(cycles_book)

    return default_books

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    # Get books for the current user
    user_id = session['user_id']
    default_books = get_default_books()
    books = Book.query.filter_by(user_id=user_id).order_by(Book.upload_date.desc()).all()
    return render_template('index.html', books=books)

@app.route('/login')
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/register')
def register():
    if 'user_id' in session:
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        logger.error("No file part in request")
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        logger.error("No selected file")
        return jsonify({'error': 'No selected file'}), 400
    
    if not file.filename.lower().endswith('.pdf'):
        logger.error("File is not a PDF")
        return jsonify({'error': 'File must be a PDF'}), 400

    try:
        user_id = session['user_id']
        
        # Create user-specific upload directory
        user_upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], str(user_id))
        os.makedirs(user_upload_dir, exist_ok=True)
        
        # Save PDF file in user's directory
        filename = secure_filename(file.filename)
        pdf_path = os.path.join(user_upload_dir, filename)
        logger.info(f"Saving uploaded file to: {pdf_path}")
        file.save(pdf_path)

        # Create book record
        book = Book(
            title=os.path.splitext(filename)[0],
            pdf_path=pdf_path,
            processing_status='pending',
            user_id=user_id
        )
        db.session.add(book)
        db.session.commit()
        logger.info(f"Created book record with id: {book.id} for user {user_id}")

        # Process PDF
        logger.info(f"Starting PDF processing for book id: {book.id}")
        process_pdf(book.id)

        return jsonify({
            'message': 'File uploaded successfully',
            'book': book.to_dict()
        })

    except Exception as e:
        logger.exception(f"Error in upload_file: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/book/<int:book_id>')
@login_required
def view_book(book_id):
    book = Book.query.get_or_404(book_id)
    return render_template('reader.html', book=book)

@app.route('/api/book/<int:book_id>/content')
def get_book_content(book_id):
    book = Book.query.get_or_404(book_id)
    
    # If text not available, try processing
    if not book.text_path or not os.path.exists(book.text_path):
        if book.pdf_path and os.path.exists(book.pdf_path):
            logger.info(f"Text not found for book {book_id}, attempting to process PDF")
            success = process_pdf(book_id)
            if not success:
                return jsonify({'error': 'Failed to process PDF'}), 500
        else:
            return jsonify({'error': 'Text content not available'}), 404

    with open(book.text_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    return jsonify({
        'content': content,
        'word_count': book.word_count,
        'current_position': book.current_position
    })

@app.route('/api/book/<int:book_id>/position', methods=['POST'])
def update_position(book_id):
    book = Book.query.get_or_404(book_id)
    data = request.get_json()
    
    if 'position' in data:
        book.current_position = data['position']
        db.session.commit()
        return jsonify({'success': True})
    
    return jsonify({'error': 'Position not provided'}), 400

@app.route('/api/book/<int:book_id>/status')
def get_processing_status(book_id):
    book = Book.query.get_or_404(book_id)
    return jsonify({
        'status': book.processing_status,
        'word_count': book.word_count
    })

if __name__ == '__main__':
    # Create required directories if they don't exist
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('outputs', exist_ok=True)
    os.makedirs('stitched_content', exist_ok=True)
    
    # Get port from environment variable (for Replit) or use default
    port = int(os.environ.get('PORT', 5000))
    
    # Run the app
    app.run(
        host='0.0.0.0',  # Required for Replit
        port=port,
        debug=False  # Set to False for production
    ) 