from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from config import supabase
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = SQLAlchemy()

TABLES = {
    'users': 'users',
    'books': 'books',
    'reading_progress': 'reading_progress',
    'user_library': 'user_library'
}

STORAGE_BUCKET = 'books'

def handle_supabase_operation(operation):
    """Wrapper to handle Supabase operations with proper error handling"""
    try:
        return operation()
    except Exception as e:
        logger.error(f"Supabase operation failed: {str(e)}")
        raise

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), nullable=False)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @staticmethod
    def create(email, password, username):
        # Check if user already exists
        if User.query.filter_by(email=email).first():
            raise ValueError('Email already registered')
        
        user = User(email=email, password=password, username=username)
        db.session.add(user)
        db.session.commit()
        return user

    @staticmethod
    def get_by_email(email):
        return User.query.filter_by(email=email).first()

    @staticmethod
    def get_by_id(user_id):
        return User.query.get(user_id)

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'username': self.username,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }

class Book(db.Model):
    __tablename__ = 'books'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(200))
    pdf_path = db.Column(db.String(500))
    text_path = db.Column(db.String(500))
    word_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    processing_status = db.Column(db.String(20), default='pending')
    current_position = db.Column(db.Integer, default=0)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)

    @staticmethod
    def create(title, author, user_id, pdf_file=None, text_content=None, word_count=0):
        """Create a new book with optional PDF and text content"""
        try:
            book = Book(
                title=title,
                author=author,
                user_id=user_id,
                word_count=word_count
            )
            db.session.add(book)
            db.session.commit()
            
            # Upload PDF if provided
            if pdf_file:
                def upload_pdf():
                    pdf_path = f"pdfs/{book.id}.pdf"
                    supabase.storage.from_(STORAGE_BUCKET).upload(
                        pdf_path,
                        pdf_file
                    )
                    return pdf_path
                
                book.pdf_path = handle_supabase_operation(upload_pdf)
            
            # Upload text content if provided
            if text_content:
                def upload_text():
                    text_path = f"texts/{book.id}.txt"
                    supabase.storage.from_(STORAGE_BUCKET).upload(
                        text_path,
                        text_content.encode()
                    )
                    return text_path
                
                book.text_path = handle_supabase_operation(upload_text)
            
            if pdf_file or text_content:
                db.session.commit()
            
            return book
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to create book: {str(e)}")
            raise Exception(f"Failed to create book: {str(e)}")

    def get_pdf_url(self):
        """Get temporary URL for PDF download"""
        if not self.pdf_path:
            return None
            
        def get_url():
            response = supabase.storage.from_(STORAGE_BUCKET).create_signed_url(
                self.pdf_path,
                3600  # URL valid for 1 hour
            )
            return response['signedURL']
            
        return handle_supabase_operation(get_url)

    def get_text_content(self):
        """Get text content from storage"""
        if not self.text_path:
            return None
            
        def get_content():
            response = supabase.storage.from_(STORAGE_BUCKET).download(self.text_path)
            return response.decode()
            
        return handle_supabase_operation(get_content)

    def update_text_content(self, text_content):
        """Update text content in storage"""
        try:
            if self.text_path:
                def remove_old():
                    supabase.storage.from_(STORAGE_BUCKET).remove([self.text_path])
                handle_supabase_operation(remove_old)
            
            def upload_new():
                text_path = f"texts/{self.id}.txt"
                supabase.storage.from_(STORAGE_BUCKET).upload(
                    text_path,
                    text_content.encode()
                )
                return text_path
                
            self.text_path = handle_supabase_operation(upload_new)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to update text content: {str(e)}")
            raise Exception(f"Failed to update text content: {str(e)}")

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'author': self.author,
            'pdf_path': self.pdf_path,
            'text_path': self.text_path,
            'word_count': self.word_count,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'user_id': self.user_id
        }

class ReadingProgress:
    def __init__(self, user_id, book_id, current_word=0, last_read=None):
        self.user_id = user_id
        self.book_id = book_id
        self.current_word = current_word
        self.last_read = last_read or datetime.utcnow()

    @staticmethod
    def save_progress(user_id, book_id, current_word):
        """Save reading progress"""
        try:
            progress_data = {
                'user_id': user_id,
                'book_id': book_id,
                'current_word': current_word,
                'last_read': datetime.utcnow().isoformat()
            }
            response = supabase.table(TABLES['reading_progress']).upsert(progress_data).execute()
            progress_data = response.data[0]
            return ReadingProgress(
                progress_data['user_id'],
                progress_data['book_id'],
                progress_data['current_word'],
                progress_data['last_read']
            )
        except Exception as e:
            raise Exception(f"Failed to save reading progress: {str(e)}")

    @staticmethod
    def get_progress(user_id, book_id):
        """Get reading progress"""
        try:
            response = supabase.table(TABLES['reading_progress']).select("*").eq('user_id', user_id).eq('book_id', book_id).execute()
            if response.data:
                progress_data = response.data[0]
                return ReadingProgress(
                    progress_data['user_id'],
                    progress_data['book_id'],
                    progress_data['current_word'],
                    progress_data['last_read']
                )
            return None
        except Exception as e:
            raise Exception(f"Failed to get reading progress: {str(e)}")

    def to_dict(self):
        """Convert reading progress object to dictionary"""
        return {
            'user_id': self.user_id,
            'book_id': self.book_id,
            'current_word': self.current_word,
            'last_read': self.last_read
        } 