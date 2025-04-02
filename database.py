CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    hash TEXT NOT NULL,  -- for storing the hashed password
    email TEXT NOT NULL UNIQUE,  -- to contact the user
    full_name TEXT,  -- user's full name
    date_of_birth TEXT,  -- storing birthdate in YYYY-MM-DD format
    gender TEXT,  -- optional, you can store the gender
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- when the account was created
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- when the account was last updated
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    hash TEXT NOT NULL,  
    email TEXT NOT NULL UNIQUE,  
    full_name TEXT,  
    date_of_birth TEXT,  
    gender TEXT,  
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  
);
