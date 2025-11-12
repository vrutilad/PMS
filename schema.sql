-- Users
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'customer'
);

-- Slots
CREATE TABLE IF NOT EXISTS slots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    status TEXT NOT NULL DEFAULT 'free'
);

-- Parkings (TIMESTAMP as TEXT for readability)
CREATE TABLE IF NOT EXISTS parkings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_number TEXT NOT NULL,
    slot TEXT NOT NULL,
    entry_time TEXT NOT NULL, 
    exit_time TEXT,           
    user_id INTEGER,
    paid_amount REAL DEFAULT 0,  
    paid INTEGER DEFAULT 0,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

-- Password reset tokens
CREATE TABLE IF NOT EXISTS reset_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    token TEXT,
    created_at TEXT,  
    used INTEGER DEFAULT 0,
    FOREIGN KEY(user_id) REFERENCES users(id)
);