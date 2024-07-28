CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS Conversations (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    content TEXT NOT NULL,
    content_vector VECTOR(1536),
    token_count INT,
    conversation TEXT NOT NULL,
    result BOOLEAN DEFAULT FALSE
);
