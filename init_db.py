from app import app, db, Book
import os

def init_db():
    with app.app_context():
        # Create tables
        db.create_all()
        
        # Check if default book exists
        default_book = Book.query.filter_by(title="Cycles—The Science of Prediction").first()
        if not default_book:
            # Create default book
            default_book = Book(
                title="Cycles—The Science of Prediction",
                author="Edward R. Dewey",
                text_path=os.path.join('stitched_content', 'CyclesThe_Science_of_Prediction_Edward_R._Dewey.txt'),
                word_count=63125  # Update this with the actual word count
            )
            db.session.add(default_book)
            db.session.commit()
            print("Added default book: Cycles—The Science of Prediction")
        else:
            print("Default book already exists")

if __name__ == '__main__':
    init_db() 