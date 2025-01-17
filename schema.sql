-- Enable UUID extension
create extension if not exists "uuid-ossp";

-- Create users table
create table users (
    id uuid references auth.users primary key,
    email text unique not null,
    username text unique not null,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Create books table
create table books (
    id uuid default uuid_generate_v4() primary key,
    title text not null,
    author text not null,
    pdf_path text,
    text_path text,
    word_count integer default 0,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Create user_library table (many-to-many relationship between users and books)
create table user_library (
    user_id uuid references users(id) on delete cascade,
    book_id uuid references books(id) on delete cascade,
    added_at timestamp with time zone default timezone('utc'::text, now()) not null,
    primary key (user_id, book_id)
);

-- Create reading_progress table
create table reading_progress (
    user_id uuid references users(id) on delete cascade,
    book_id uuid references books(id) on delete cascade,
    current_position integer default 0,
    last_read_at timestamp with time zone default timezone('utc'::text, now()) not null,
    primary key (user_id, book_id)
);

-- Set up RLS (Row Level Security) policies
alter table users enable row level security;
alter table books enable row level security;
alter table user_library enable row level security;
alter table reading_progress enable row level security;

-- Users can only read/update their own data
create policy "Users can view own profile"
    on users for select
    using (auth.uid() = id);

create policy "Users can update own profile"
    on users for update
    using (auth.uid() = id);

-- Books are readable by all authenticated users
create policy "Books are readable by all users"
    on books for select
    to authenticated
    using (true);

-- Users can only see books in their library
create policy "Users can view their library"
    on user_library for select
    using (auth.uid() = user_id);

create policy "Users can add books to their library"
    on user_library for insert
    with check (auth.uid() = user_id);

-- Users can only see and update their own reading progress
create policy "Users can view own reading progress"
    on reading_progress for select
    using (auth.uid() = user_id);

create policy "Users can update own reading progress"
    on reading_progress for insert
    with check (auth.uid() = user_id);

create policy "Users can update own reading progress"
    on reading_progress for update
    using (auth.uid() = user_id); 