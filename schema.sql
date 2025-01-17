-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create users table
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    username TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- Create books table
CREATE TABLE books (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    pdf_path TEXT,
    text_path TEXT,
    word_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- Create user_library table (many-to-many relationship between users and books)
CREATE TABLE user_library (
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    book_id UUID REFERENCES books(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    PRIMARY KEY (user_id, book_id)
);

-- Create reading_progress table
CREATE TABLE reading_progress (
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    book_id UUID REFERENCES books(id) ON DELETE CASCADE,
    current_word INTEGER DEFAULT 0,
    last_read TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    PRIMARY KEY (user_id, book_id)
);

-- Create storage bucket for PDFs and processed text files
INSERT INTO storage.buckets (id, name) VALUES ('books', 'books');

-- Enable Row Level Security
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE books ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_library ENABLE ROW LEVEL SECURITY;
ALTER TABLE reading_progress ENABLE ROW LEVEL SECURITY;

-- Create policies for users table
CREATE POLICY "Users can view their own profile"
    ON users FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY "Users can update their own profile"
    ON users FOR UPDATE
    USING (auth.uid() = id);

-- Create policies for books table
CREATE POLICY "Books are readable by all authenticated users"
    ON books FOR SELECT
    USING (auth.role() = 'authenticated');

CREATE POLICY "Users can create books"
    ON books FOR INSERT
    WITH CHECK (auth.role() = 'authenticated');

-- Create policies for user_library table
CREATE POLICY "Users can view their own library"
    ON user_library FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can add books to their library"
    ON user_library FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can remove books from their library"
    ON user_library FOR DELETE
    USING (auth.uid() = user_id);

-- Create policies for reading_progress table
CREATE POLICY "Users can view their own reading progress"
    ON reading_progress FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can update their own reading progress"
    ON reading_progress FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own reading progress"
    ON reading_progress FOR UPDATE
    USING (auth.uid() = user_id); 