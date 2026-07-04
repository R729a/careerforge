-- Database Schema for CareerForge AI
-- Supports both SQLite (local development) and PostgreSQL

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Career Roadmaps
CREATE TABLE IF NOT EXISTS roadmaps (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    target_role TEXT NOT NULL,
    duration_months INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Roadmap Milestones
CREATE TABLE IF NOT EXISTS milestones (
    id TEXT PRIMARY KEY,
    roadmap_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    sequence_order INTEGER NOT NULL,
    status TEXT DEFAULT 'pending',
    FOREIGN KEY(roadmap_id) REFERENCES roadmaps(id) ON DELETE CASCADE
);

-- Actionable Tasks
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    milestone_id TEXT NOT NULL,
    title TEXT NOT NULL,
    priority TEXT DEFAULT 'medium',
    estimated_hours REAL,
    status TEXT DEFAULT 'pending',
    scheduled_start TIMESTAMP,
    scheduled_end TIMESTAMP,
    FOREIGN KEY(milestone_id) REFERENCES milestones(id) ON DELETE CASCADE
);

-- Study Quiz Sessions
CREATE TABLE IF NOT EXISTS quiz_sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    subject TEXT NOT NULL,
    score REAL,
    total_questions INTEGER NOT NULL,
    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Security Audit Logs
CREATE TABLE IF NOT EXISTS audit_logs (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    correlation_id TEXT NOT NULL,
    action TEXT NOT NULL,
    target_agent TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    details TEXT
);

-- Courses Database Reference
CREATE TABLE IF NOT EXISTS courses (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    provider TEXT,
    url TEXT,
    skills_taught TEXT
);

-- Skills Database Reference
CREATE TABLE IF NOT EXISTS skills (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    category TEXT
);

-- Pending Approvals Queue
CREATE TABLE IF NOT EXISTS approvals (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    agent TEXT NOT NULL,
    action TEXT NOT NULL,
    payload TEXT NOT NULL, -- JSON string of the proposed actions
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

