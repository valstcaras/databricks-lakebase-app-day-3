-- Watchlist table schema for storing stock watchlist data
-- Run this SQL against your Lakebase Postgres database to create the watchlist table

CREATE TABLE IF NOT EXISTS watchlist (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    latest_price DECIMAL(12, 2),
    updated_at TIMESTAMP,
    CONSTRAINT unique_user_symbol UNIQUE (email, symbol)
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_watchlist_email ON watchlist(email);
CREATE INDEX IF NOT EXISTS idx_watchlist_symbol ON watchlist(symbol);
CREATE INDEX IF NOT EXISTS idx_watchlist_updated_at ON watchlist(updated_at DESC);
-- MCP Tool Traces table for logging all MCP tool executions
-- output_result JSONB should follow standardized format:
-- {
--   "tool_name": "<tool_name>",
--   "success": true/false,
--   "message": "<execution message>",
--   "data": { ... optional additional data ... },
--   "timestamp": "<ISO 8601 timestamp>"
-- }
CREATE TABLE IF NOT EXISTS mcp_tool_traces (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    user_email VARCHAR(255),
    tool_name VARCHAR(255) NOT NULL,
    input_params JSONB,
    output_result JSONB NOT NULL,  -- Standardized: {"tool_name": str, "success": bool, "message": str, "data": {}, "timestamp": str}
    status VARCHAR(50) NOT NULL,  -- 'success', 'error', 'pending'
    error_message TEXT,
    duration_ms FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT valid_status CHECK (status IN ('success', 'error', 'pending'))
);

-- Create indexes for better query performance on traces
CREATE INDEX IF NOT EXISTS idx_mcp_traces_session ON mcp_tool_traces(session_id);
CREATE INDEX IF NOT EXISTS idx_mcp_traces_tool ON mcp_tool_traces(tool_name);
CREATE INDEX IF NOT EXISTS idx_mcp_traces_status ON mcp_tool_traces(status);
CREATE INDEX IF NOT EXISTS idx_mcp_traces_created ON mcp_tool_traces(created_at DESC);

-- Example of properly formatted trace log:
-- INSERT INTO mcp_tool_traces (session_id, user_email, tool_name, input_params, output_result, status, duration_ms)
-- VALUES (
--   'session-123',
--   'user@example.com',
--   'get_stock_price',
--   '{"symbol": "AAPL"}',
--   '{"tool_name": "get_stock_price", "success": true, "message": "Successfully fetched stock price", "data": {"symbol": "AAPL", "price": 150.25}, "timestamp": "2024-01-15T10:30:00Z"}',
--   'success',
--   125.5
-- );
