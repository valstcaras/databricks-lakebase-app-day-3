"""
Query logger for Weather MCP Dashboard.

Stores weather agent queries in memory (can be extended to use Lakebase).
Tracks all weather tool calls, their parameters, results, and timing.
"""

from datetime import datetime
from collections import defaultdict, deque
from typing import Dict, List
import threading

# Thread-safe in-memory storage
_lock = threading.Lock()
_queries = deque(maxlen=1000)  # Keep last 1000 queries
_stats = defaultdict(int)


def log_query(query_data: Dict):
    """
    Log a weather query from the agent.
    
    Expected format:
    {
        "tool_name": "get_current_weather" | "get_forecast" | "predict_umbrella_needed" | "get_travel_recommendation",
        "location": "San Francisco",
        "parameters": {...},  # Additional params like days, date
        "result": {...},      # The result returned by the tool
        "timestamp": "2026-08-09T10:00:00",
        "execution_time_ms": 234.56
    }
    """
    with _lock:
        # Add timestamp if not present
        if "timestamp" not in query_data:
            query_data["timestamp"] = datetime.utcnow().isoformat()
        
        _queries.appendleft(query_data)
        
        # Update stats
        tool_name = query_data.get("tool_name", "unknown")
        _stats[f"total_{tool_name}"] += 1
        _stats["total_queries"] += 1
        
        # Track locations
        location = query_data.get("location", "unknown")
        _stats[f"location_{location}"] += 1


def get_recent_queries(limit: int = 50) -> List[Dict]:
    """
    Get the N most recent queries.
    
    Returns:
        List of query dictionaries, most recent first
    """
    with _lock:
        return list(_queries)[:limit]


def get_query_stats() -> Dict:
    """
    Get aggregated statistics about queries.
    
    Returns:
        Dict with stats like total queries, queries by tool, top locations, etc.
    """
    with _lock:
        # Separate tool counts and location counts
        tool_counts = {}
        location_counts = {}
        
        for key, value in _stats.items():
            if key.startswith("total_") and key != "total_queries":
                tool_name = key.replace("total_", "")
                tool_counts[tool_name] = value
            elif key.startswith("location_"):
                location = key.replace("location_", "")
                location_counts[location] = value
        
        # Get top locations
        top_locations = sorted(location_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            "total_queries": _stats.get("total_queries", 0),
            "tool_counts": tool_counts,
            "top_locations": [{
                "location": loc,
                "count": count
            } for loc, count in top_locations],
            "recent_count": len(_queries)
        }


def clear_queries():
    """Clear all stored queries and stats (for testing)."""
    with _lock:
        _queries.clear()
        _stats.clear()
