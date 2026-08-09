"""
Alpaca Markets paper-trading MCP server.

Exposes paper-trading tools over MCP (Model Context Protocol) so a
Databricks Agent Bricks agent can call them like any other tool:
    - get_quote(symbol)
    - stage_trade(account_id, symbol, side, quantity)
    - execute_trade(confirmation_code)
    - get_positions(account_id)
    - get_account_summary(account_id)
    - get_order_history(account_id, limit)
    - get_balance(account_id)
    - get_current_user()
    - add_to_watchlist(symbol, email)
    - get_watchlist(limit, email)
    - remove_from_watchlist(symbol)
    - vector_search(query, limit, search_chunks)
    - get_mcp_traces(session_id, limit)

All MCP tool calls are automatically traced and stored in the
mcp_tool_traces Lakebase table with:
    - Unique session ID per request
    - User email
    - Tool name, input parameters, output results
    - Execution duration and status
    - Timestamps

These tools are backed by Alpaca Markets' real, hosted paper-trading
account (see alpaca_broker.py), so students can safely wire an Agent
Bricks agent to place real (but fake-money) trades without a real
brokerage account or risk of real money moving. account_id is accepted
for signature compatibility but is not used to select an account - Alpaca
paper trading is one account per API key pair.

Swap-in-a-real-broker note: to point this at a different broker instead,
keep the same 5 tool signatures below and replace the alpaca_broker.*
calls inside each tool with calls to that broker's SDK/API - the MCP
surface for the agent does not need to change. The original Lakebase-
simulated engine is preserved in paper_broker.py for reference.

Deploy this as its own Databricks App (same app.yaml + FastMCP entrypoint
pattern documented at
https://docs.databricks.com/aws/en/agents/mcp-tools/custom-mcp), separate
from the dashboard app, so an Agent Bricks agent (or any MCP client) can
register its URL as an external MCP server.

Run locally:
    python alpaca_mcp_server.py
"""

import os
import logging
import random
import uuid
import json
import time
import functools
from contextvars import ContextVar
from datetime import datetime, timedelta

from fastmcp import FastMCP
from sentence_transformers import SentenceTransformer
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

import alpaca_broker
import massive_broker
import lakebase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("alpaca-mcp-server")

# Load embedding model once at startup
_embedding_model = None

def get_embedding_model():
    """Lazy-load the embedding model (expensive operation, only on first use)."""
    global _embedding_model
    if _embedding_model is None:
        logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL)
    return _embedding_model

# Table names from environment variables
NEWS_TABLE_NAME = os.environ.get("NEWS_TABLE_NAME", "ticker_news_documents")
EMBEDDINGS_TABLE_NAME = os.environ.get("EMBEDDINGS_TABLE_NAME", "ticker_news_embeddings")
CHUNK_EMBEDDINGS_TABLE_NAME = os.environ.get("CHUNK_EMBEDDINGS_TABLE_NAME", "ticker_news_chunk_embeddings")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

# Context variable to store request headers for accessing end-user identity
_request_context: ContextVar[dict] = ContextVar('request_context', default={})

# Context variable to store session ID for tracing
_session_id: ContextVar[str] = ContextVar('session_id', default=None)

# In-memory storage for staged trades with confirmation codes
# Format: {code: {account_id, symbol, side, quantity, quote, staged_at}}
_staged_trades: dict[str, dict] = {}


def _get_end_user_email() -> str:
    """Get the actual end user's email from request headers, or fallback to service principal."""
    # Try to get from X-Forwarded-User header (Databricks App context)
    headers = _request_context.get()
    forwarded_user = headers.get('x-forwarded-user')
    if forwarded_user:
        return forwarded_user
    
    # Fallback: use service principal (local development or non-App contexts)
    from databricks.sdk import WorkspaceClient
    w = WorkspaceClient()
    return w.current_user.me().user_name or 'zach@dataexpert.io'


def _init_tracing_table():
    """Initialize the MCP tracing table in Lakebase if it doesn't exist."""
    try:
        sql = """
        CREATE TABLE IF NOT EXISTS mcp_tool_traces (
            id SERIAL PRIMARY KEY,
            session_id VARCHAR(255) NOT NULL,
            user_email VARCHAR(255),
            tool_name VARCHAR(255) NOT NULL,
            input_params JSONB,
            output_result JSONB,
            status VARCHAR(50) NOT NULL,
            error_message TEXT,
            duration_ms FLOAT,
            created_at TIMESTAMP DEFAULT NOW()
        )
        """
        lakebase.run_write(sql, ())
        logger.info("MCP tracing table initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize tracing table: {e}")


def _trace_tool_call(func):
    """Decorator to trace MCP tool calls and store them in Lakebase.
    
    Wraps all tool results in a standardized format with:
    - tool_name: Name of the tool that was executed
    - status: 'success' or 'error'
    - execution_time_ms: Duration of execution
    - message: Brief description of the execution result
    - result: The actual tool result (for success) or error details (for errors)
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Get session ID and user email
        session_id = _session_id.get() or str(uuid.uuid4())
        user_email = None
        try:
            user_email = _get_end_user_email()
        except:
            pass
        
        tool_name = func.__name__
        start_time = time.time()
        
        # Capture input parameters
        input_params = {
            'args': [str(arg) for arg in args],
            'kwargs': {k: str(v) for k, v in kwargs.items()}
        }
        
        try:
            # Execute the actual tool
            result = func(*args, **kwargs)
            duration_ms = (time.time() - start_time) * 1000
            
            # Create standardized response wrapper
            standardized_result = {
                "tool_name": tool_name,
                "status": "success",
                "execution_time_ms": round(duration_ms, 2),
                "message": f"{tool_name} executed successfully",
                "result": result
            }
            
            # Store trace in Lakebase
            try:
                sql = """
                INSERT INTO mcp_tool_traces 
                (session_id, user_email, tool_name, input_params, output_result, status, duration_ms)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                lakebase.run_write(
                    sql,
                    (
                        session_id,
                        user_email,
                        tool_name,
                        json.dumps(input_params),
                        json.dumps(standardized_result),
                        'success',
                        duration_ms
                    )
                )
            except Exception as trace_error:
                logger.warning(f"Failed to store trace: {trace_error}")
            
            return standardized_result
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            
            # Create standardized error response
            standardized_error = {
                "tool_name": tool_name,
                "status": "error",
                "execution_time_ms": round(duration_ms, 2),
                "message": f"{tool_name} failed: {str(e)}",
                "error_details": {
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }
            }
            
            # Store error trace
            try:
                sql = """
                INSERT INTO mcp_tool_traces 
                (session_id, user_email, tool_name, input_params, output_result, status, error_message, duration_ms)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                lakebase.run_write(
                    sql,
                    (
                        session_id,
                        user_email,
                        tool_name,
                        json.dumps(input_params),
                        json.dumps(standardized_error),
                        'error',
                        str(e),
                        duration_ms
                    )
                )
            except Exception as trace_error:
                logger.warning(f"Failed to store error trace: {trace_error}")
            
            # Return the standardized error instead of raising
            return standardized_error
    
    return wrapper


mcp = FastMCP("alpaca-paper-trading")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Middleware to capture HTTP headers containing end-user identity and generate session IDs."""
    async def dispatch(self, request: Request, call_next):
        # Generate a unique session ID for this request
        session_id = str(uuid.uuid4())
        _session_id.set(session_id)
        
        # Capture headers that Databricks injects with user identity
        headers = {
            'x-forwarded-user': request.headers.get('x-forwarded-user'),
            'x-forwarded-email': request.headers.get('x-forwarded-email'),
        }
        _request_context.set(headers)
        
        # Log the session start
        logger.info(f"New MCP session: {session_id} for user: {headers.get('x-forwarded-user', 'unknown')}")
        
        response = await call_next(request)
        return response


@mcp.tool
@_trace_tool_call
def get_quote(symbol: str) -> dict:
    """
    Get the latest real quote for a stock ticker symbol from Massive.com.

    Args:
        symbol: Stock ticker symbol, e.g. "AAPL".

    Returns:
        A dict with symbol, price, as_of (ISO timestamp), volume, change, and change_percent.
    """
    return massive_broker.get_quote(symbol)


@mcp.tool
@_trace_tool_call
def stage_trade(account_id: str, symbol: str, side: str, quantity: float) -> dict:
    """
    Stage a trade for review before execution. Gets a quote, calculates the
    total cost, and generates a 5-digit confirmation code.
    
    The trade will NOT be executed until execute_trade is called with the
    confirmation code. Staged trades expire after 10 minutes.

    Args:
        account_id: Accepted for signature compatibility; not used to
            select an account (Alpaca paper trading is one account per
            API key pair).
        symbol: Stock ticker symbol, e.g. "AAPL".
        side: "BUY" or "SELL".
        quantity: Number of shares to trade (must be positive).

    Returns:
        A dict with trade summary, estimated cost, and a 5-digit confirmation
        code to use with execute_trade.
    """
    try:
        # Validate inputs
        if side.upper() not in ["BUY", "SELL"]:
            return {"status": "error", "message": "side must be BUY or SELL"}
        if quantity <= 0:
            return {"status": "error", "message": "quantity must be positive"}
        
        symbol = symbol.strip().upper()
        side = side.upper()
        
        # Get current quote
        quote = massive_broker.get_quote(symbol)
        
        # Calculate estimated cost
        estimated_cost = quote["price"] * quantity
        
        # Generate 5-digit confirmation code
        code = f"{random.randint(10000, 99999)}"
        
        # Store staged trade
        _staged_trades[code] = {
            "account_id": account_id,
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "quote": quote,
            "staged_at": datetime.now(),
            "estimated_cost": estimated_cost,
        }
        
        return {
            "status": "staged",
            "confirmation_code": code,
            "summary": {
                "action": f"{side} {quantity} shares of {symbol}",
                "current_price": quote["price"],
                "estimated_cost": f"${estimated_cost:,.2f}",
                "quote_as_of": quote["as_of"],
            },
            "message": f"Trade staged. To execute, call execute_trade with confirmation code: {code}",
            "expires_in": "10 minutes",
        }
    except Exception as e:
        logger.exception(f"Failed to stage trade for {symbol}")
        return {
            "status": "error",
            "message": f"Failed to stage trade: {str(e)}",
        }


@mcp.tool
@_trace_tool_call
def execute_trade(confirmation_code: str) -> dict:
    """
    Execute a previously staged trade using its 5-digit confirmation code.
    
    This places a real market order (paper trade) against the configured
    Alpaca paper trading account. The trade must have been staged first
    using stage_trade.

    Args:
        confirmation_code: The 5-digit code returned by stage_trade.

    Returns:
        A dict describing the executed order (id, symbol, side, quantity,
        price, notional, status, created_at) or an error if the code is
        invalid or expired.
    """
    try:
        # Verify confirmation code exists
        if confirmation_code not in _staged_trades:
            return {
                "status": "error",
                "message": "Invalid confirmation code. Please stage a trade first using stage_trade.",
            }
        
        # Retrieve staged trade
        staged = _staged_trades[confirmation_code]
        
        # Check if trade has expired (10 minutes)
        if datetime.now() - staged["staged_at"] > timedelta(minutes=10):
            del _staged_trades[confirmation_code]
            return {
                "status": "error",
                "message": "Confirmation code has expired. Please stage the trade again.",
            }
        
        # Execute the trade
        result = alpaca_broker.place_order(
            staged["account_id"],
            staged["symbol"],
            staged["side"],
            staged["quantity"]
        )
        
        # Remove staged trade after successful execution
        del _staged_trades[confirmation_code]
        
        return result
        
    except Exception as e:
        logger.exception(f"Failed to execute trade with code {confirmation_code}")
        return {
            "status": "error",
            "message": f"Failed to execute trade: {str(e)}",
        }


@mcp.tool
@_trace_tool_call
def get_positions(account_id: str) -> list[dict]:
    """
    Get all open positions for the Alpaca paper trading account.

    Args:
        account_id: Accepted for signature compatibility; not used to
            select an account.

    Returns:
        A list of dicts, each with symbol, quantity, avg_cost, updated_at.
    """
    return alpaca_broker.get_positions(account_id)


@mcp.tool
@_trace_tool_call
def get_account_summary(account_id: str) -> dict:
    """
    Get a full account summary for the Alpaca paper trading account: cash
    balance, open positions marked-to-market, total market value, and
    total equity (cash + market value).

    Args:
        account_id: Accepted for signature compatibility; not used to
            select an account.

    Returns:
        A dict with account_id, cash_balance, positions, market_value,
        total_equity.
    """
    return alpaca_broker.get_account_summary(account_id)


@mcp.tool
@_trace_tool_call
def get_order_history(account_id: str, limit: int = 50) -> list[dict]:
    """
    Get recent orders for the Alpaca paper trading account, most recent first.

    Args:
        account_id: Accepted for signature compatibility; not used to
            select an account.
        limit: Max number of orders to return (default 50).

    Returns:
        A list of dicts, each with id, symbol, side, quantity, price,
        notional, status, created_at.
    """
    return alpaca_broker.get_order_history(account_id, limit)


@mcp.tool
@_trace_tool_call
def get_balance(account_id: str) -> dict:
    """
    Get the current cash balance and buying power for the Alpaca paper 
    trading account.

    Args:
        account_id: Accepted for signature compatibility; not used to
            select an account.

    Returns:
        A dict with account_id, cash_balance, buying_power, and currency.
    """
    return alpaca_broker.get_account_summary(account_id)


@mcp.tool
@_trace_tool_call
def get_current_user() -> dict:
    """
    Get information about the currently authenticated end user accessing the MCP server.
    
    When running as a Databricks App, this returns the actual end user making the
    request (from X-Forwarded-User header), not the service principal running the app.

    Returns:
        A dict with user_name (email from X-Forwarded-User header), 
        forwarded_email, and source ("request_header" or "service_principal").
    """
    try:
        # First, try to get the end user from the request headers
        # Databricks injects X-Forwarded-User with the actual user's email
        headers = _request_context.get()
        forwarded_user = headers.get('x-forwarded-user')
        forwarded_email = headers.get('x-forwarded-email')
        
        if forwarded_user:
            return {
                "status": "success",
                "user_name": forwarded_user,
                "forwarded_email": forwarded_email,
                "source": "request_header",
            }
        
        # Fallback: return the service principal if headers aren't available
        # (e.g., when running locally or in non-App contexts)
        from databricks.sdk import WorkspaceClient
        w = WorkspaceClient()
        user = w.current_user.me()
        return {
            "status": "success",
            "user_name": user.user_name,
            "display_name": user.display_name,
            "active": user.active,
            "source": "service_principal",
        }
    except Exception as e:
        logger.exception("Failed to get current user")
        return {
            "status": "error",
            "message": f"Failed to get current user: {str(e)}",
        }


@mcp.tool
@_trace_tool_call
def add_to_watchlist(symbol: str, email: str = 'valeria.s.caras@gmail.com') -> dict:
    """
    Add a stock to the watchlist by fetching its current quote from Massive.com
    and storing it in the Lakebase watchlist table.
    
    Uses the authenticated user's email as the user_id.
    
    Args:
        symbol: Stock ticker symbol, e.g. "AAPL".
    
    Returns:
        A dict with the quote data and confirmation that it was added to the watchlist.
    """
    try:
        # Get the actual end user's email (not the service principal)
        user_email = email
        
        # Get quote from Massive.com
        quote = massive_broker.get_quote(symbol)
        
        # Store in Lakebase watchlist table
        sql = """
        INSERT INTO watchlist (email, symbol, latest_price, updated_at)
        VALUES (%s, %s, %s, NOW())
        ON CONFLICT (email, symbol) 
        DO UPDATE SET 
            latest_price = EXCLUDED.latest_price,
            updated_at = NOW()
        """
        
        lakebase.run_write(
            sql,
            (
                user_email,
                quote["symbol"],
                quote["price"]
            ),
        )
        
        return {
            "status": "success",
            "message": f"Added {symbol} to watchlist for {user_email}",
            "user_email": user_email,
            "quote": quote,
        }
    except Exception as e:
        logger.exception(f"Failed to add {symbol} to watchlist")
        return {
            "status": "error",
            "message": f"Failed to add {symbol} to watchlist: {str(e)}",
        }


@mcp.tool
@_trace_tool_call
def get_watchlist(limit: int = 100, email: str = 'zach@dataexpert.io') -> dict:
    """
    Retrieve all stocks in the authenticated user's watchlist from Lakebase.
    
    Uses the authenticated user's email as the user_id.
    
    Args:
        limit: Maximum number of entries to return (default: 100).
        email: authenticate user's email
    
    Returns:
        A dict with watchlist entries sorted by most recently added.
    """
    try:
        # Get the actual end user's email (not the service principal)
        
        sql = """
        SELECT 
            symbol,
            latest_price,
            updated_at
        FROM watchlist
        WHERE email = %s
        LIMIT %s
        """
        
        rows = lakebase.run_query(sql, (email, limit))
        
        return {
            "status": "success",
            "user_email": email,
            "count": len(rows),
            "watchlist": rows,
        }
    except Exception as e:
        logger.exception(f"Failed to retrieve watchlist")
        return {
            "status": "error",
            "message": f"Failed to retrieve watchlist: {str(e)}",
        }


@mcp.tool
@_trace_tool_call
def remove_from_watchlist(symbol: str) -> dict:
    """
    Remove a stock from the authenticated user's watchlist.
    
    Uses the authenticated user's email as the user_id.
    
    Args:
        symbol: Stock ticker symbol to remove, e.g. "AAPL".
    
    Returns:
        A dict with status and confirmation message.
    """
    try:
        # Get the actual end user's email (not the service principal)
        user_email = _get_end_user_email()
        
        symbol = symbol.strip().upper()
        
        sql = """
        DELETE FROM watchlist
        WHERE email = %s AND symbol = %s
        """
        
        rows_affected = lakebase.run_write(sql, (user_email, symbol))
        
        if rows_affected > 0:
            return {
                "status": "success",
                "message": f"Removed {symbol} from watchlist",
                "symbol": symbol,
                "user_email": user_email,
            }
        else:
            return {
                "status": "not_found",
                "message": f"{symbol} was not in the watchlist",
                "symbol": symbol,
                "user_email": user_email,
            }
    except Exception as e:
        logger.exception(f"Failed to remove {symbol} from watchlist")
        return {
            "status": "error",
            "message": f"Failed to remove {symbol} from watchlist: {str(e)}",
        }


@mcp.tool
@_trace_tool_call
def get_mcp_traces(session_id: str = None, limit: int = 100) -> dict:
    """
    Retrieve MCP tool call traces from Lakebase for monitoring and debugging.
    
    Args:
        session_id: Optional session ID to filter traces (if None, returns recent traces)
        limit: Maximum number of traces to return (default 100)
    
    Returns:
        A dict with traces, including tool names, parameters, results, and durations
    """
    try:
        if session_id:
            sql = """
            SELECT 
                id,
                session_id,
                user_email,
                tool_name,
                input_params,
                output_result,
                status,
                error_message,
                duration_ms,
                created_at
            FROM mcp_tool_traces
            WHERE session_id = %s
            ORDER BY created_at DESC
            LIMIT %s
            """
            rows = lakebase.run_query(sql, (session_id, limit))
        else:
            sql = """
            SELECT 
                id,
                session_id,
                user_email,
                tool_name,
                input_params,
                output_result,
                status,
                error_message,
                duration_ms,
                created_at
            FROM mcp_tool_traces
            ORDER BY created_at DESC
            LIMIT %s
            """
            rows = lakebase.run_query(sql, (limit,))
        
        return {
            "status": "success",
            "count": len(rows),
            "session_id_filter": session_id,
            "traces": rows,
        }
    except Exception as e:
        logger.exception("Failed to retrieve traces")
        return {
            "status": "error",
            "message": f"Failed to retrieve traces: {str(e)}",
        }


@mcp.tool
@_trace_tool_call
def get_stock_information(stock_query: str, limit: int = 10, search_chunks: bool = True) -> dict:
    """
    Queries information of a given stock.
    
    Accepts a text query, computes its embedding, and returns the most similar
    documents and chunks from Lakebase using pgvector's cosine similarity.
    
    Args:
        query: Natural language search query (e.g. "tech company earnings")
        limit: Maximum number of results to return (default 10)
        search_chunks: Whether to search chunk-level embeddings in addition to documents
    
    Returns:
        A dict with query, documents, chunks, and model name
    """
    if not stock_query or not stock_query.strip():
        return {"error": "Query text is required"}
    
    try:
        # Compute embedding for the query
        model = get_embedding_model()
        query_embedding = model.encode(stock_query)
        
        # Convert to list for JSON serialization and postgres array format
        embedding_list = query_embedding.tolist()
        
        # Search document-level embeddings
        doc_results = lakebase.run_query(
            f"""
            SELECT 
                e.id,
                e.ticker,
                e.title,
                e.published_utc,
                e.model_name,
                1 - (e.embedding <=> %s::vector) as similarity,
                d.description,
                d.article_url,
                d.sentiment
            FROM {EMBEDDINGS_TABLE_NAME} e
            LEFT JOIN {NEWS_TABLE_NAME} d ON e.id = d.id
            ORDER BY e.embedding <=> %s::vector
            LIMIT %s
            """,
            (str(embedding_list), str(embedding_list), limit),
        )
        
        chunk_results = []
        if search_chunks:
            # Search chunk-level embeddings
            chunk_results = lakebase.run_query(
                f"""
                SELECT 
                    c.id,
                    c.article_id,
                    c.ticker,
                    c.chunk_index,
                    c.chunk_text,
                    c.model_name,
                    1 - (c.embedding <=> %s::vector) as similarity,
                    d.title,
                    d.article_url,
                    d.published_utc
                FROM {CHUNK_EMBEDDINGS_TABLE_NAME} c
                LEFT JOIN {NEWS_TABLE_NAME} d ON c.article_id = d.id
                ORDER BY c.embedding <=> %s::vector
                LIMIT %s
                """,
                (str(embedding_list), str(embedding_list), limit),
            )
        
        return {
            "query": stock_query,
            "documents": doc_results,
            "chunks": chunk_results,
            "model": EMBEDDING_MODEL
        }
        
    except Exception as e:
        logger.exception("Vector search failed")
        return {"error": str(e)}


if __name__ == "__main__":
    # Initialize the tracing table
    _init_tracing_table()
    
    # Add middleware to capture request headers for end-user identity
    # This must be done before mcp.run() is called
    if hasattr(mcp, 'app') and mcp.app is not None:
        mcp.app.add_middleware(RequestContextMiddleware)
    
    # Databricks Apps route external HTTP traffic to this port via app.yaml;
    # streamable-http is the transport Databricks' MCP client/gateway expects
    # (see the "Host your own MCP" doc linked in the module docstring above).
    port = int(os.getenv("DATABRICKS_APP_PORT", os.getenv("PORT", 8000)))
    mcp.run(transport="http", host="0.0.0.0", port=port)
