# Integrating Weather MCP Server with Dashboard

This guide shows how to automatically log all weather queries from your MCP server to the dashboard.

## Overview

The dashboard provides a `/api/log` endpoint that accepts POST requests with query data. By adding logging calls to your weather MCP server, all agent queries will automatically appear in the dashboard.

## Step 1: Add Logging Function

Add this function to your `weather_mcp_server.py`:

```python
import requests
import os

# Dashboard URL - use environment variable or default to localhost
DASHBOARD_URL = os.getenv("WEATHER_DASHBOARD_URL", "http://localhost:8002")

def log_to_dashboard(tool_name: str, location: str, parameters: dict, result: dict, execution_time_ms: float):
    """
    Log a weather query to the monitoring dashboard.
    
    Args:
        tool_name: Name of the MCP tool (e.g., "get_current_weather")
        location: Location queried
        parameters: Full parameters passed to the tool
        result: Result returned by the tool
        execution_time_ms: Execution time in milliseconds
    """
    try:
        query_data = {
            "tool_name": tool_name,
            "location": location,
            "parameters": parameters,
            "result": result,
            "execution_time_ms": execution_time_ms
        }
        
        # Non-blocking POST with short timeout
        requests.post(
            f"{DASHBOARD_URL}/api/log",
            json=query_data,
            timeout=1  # 1 second timeout
        )
    except Exception as e:
        # Don't fail the MCP call if logging fails
        # Optionally log the error for debugging
        pass
```

## Step 2: Instrument Your Tools

Modify each MCP tool to log its execution. Here's an example for `get_current_weather`:

### Before:
```python
@mcp_server.tool()
def get_current_weather(location: str) -> Dict:
    """Get current weather for a location."""
    start_time = time.time()
    
    result = weather_broker.get_current_weather(location)
    
    execution_time = (time.time() - start_time) * 1000
    
    return {
        "tool_name": "get_current_weather",
        "status": "success",
        "execution_time_ms": execution_time,
        "result": result
    }
```

### After:
```python
@mcp_server.tool()
def get_current_weather(location: str) -> Dict:
    """Get current weather for a location."""
    start_time = time.time()
    
    result = weather_broker.get_current_weather(location)
    
    execution_time = (time.time() - start_time) * 1000
    
    # Log to dashboard
    log_to_dashboard(
        tool_name="get_current_weather",
        location=location,
        parameters={"location": location},
        result=result,
        execution_time_ms=execution_time
    )
    
    return {
        "tool_name": "get_current_weather",
        "status": "success",
        "execution_time_ms": execution_time,
        "result": result
    }
```

## Step 3: Repeat for All Tools

Add similar logging calls to:
- `get_forecast(location, days)`
- `predict_umbrella_needed(location, date)`
- `get_travel_recommendation(location, date)`

## Step 4: Set Environment Variable

When deploying to Databricks:

1. **Local development**: Dashboard runs at `http://localhost:8002`
2. **Databricks Apps**: Set `WEATHER_DASHBOARD_URL` to your deployed dashboard URL

```bash
# In your app configuration or environment
export WEATHER_DASHBOARD_URL=https://your-workspace.databricks.com/apps/weather-dashboard
```

## Example: Complete Instrumented Tool

Here's a complete example showing all the parts together:

```python
import time
import requests
import os
from typing import Dict, Optional

DASHBOARD_URL = os.getenv("WEATHER_DASHBOARD_URL", "http://localhost:8002")

def log_to_dashboard(tool_name: str, location: str, parameters: dict, result: dict, execution_time_ms: float):
    try:
        query_data = {
            "tool_name": tool_name,
            "location": location,
            "parameters": parameters,
            "result": result,
            "execution_time_ms": execution_time_ms
        }
        requests.post(f"{DASHBOARD_URL}/api/log", json=query_data, timeout=1)
    except:
        pass

@mcp_server.tool()
def predict_umbrella_needed(location: str, date: Optional[str] = None) -> Dict:
    """
    Predict if an umbrella is needed for a location on a specific date.
    
    Args:
        location: City or location name
        date: Date in YYYY-MM-DD format (optional, defaults to today)
    """
    start_time = time.time()
    
    try:
        result = weather_broker.predict_umbrella_needed(location, date)
        execution_time = (time.time() - start_time) * 1000
        
        # Log successful query
        log_to_dashboard(
            tool_name="predict_umbrella_needed",
            location=location,
            parameters={"location": location, "date": date},
            result=result,
            execution_time_ms=execution_time
        )
        
        return {
            "tool_name": "predict_umbrella_needed",
            "status": "success",
            "execution_time_ms": execution_time,
            "result": result
        }
    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        
        # Log failed query too
        log_to_dashboard(
            tool_name="predict_umbrella_needed",
            location=location,
            parameters={"location": location, "date": date},
            result={"error": str(e)},
            execution_time_ms=execution_time
        )
        
        raise
```

## Testing

1. Start the dashboard:
   ```bash
   cd weather-dashboard
   python app.py
   ```

2. Start your MCP server (with logging enabled):
   ```bash
   cd ../weather-mpc
   python weather_mcp_server.py
   ```

3. Make some weather queries through your agent

4. Open `http://localhost:8002` to see queries appear in real-time

## Troubleshooting

### Queries Not Appearing

1. **Check dashboard is running**: Visit `http://localhost:8002/healthz` - should return `{"status": "ok"}`

2. **Check MCP server logs**: Look for any connection errors or exceptions

3. **Verify URL**: Make sure `WEATHER_DASHBOARD_URL` points to the correct address

4. **Test logging directly**:
   ```python
   import requests
   requests.post("http://localhost:8002/api/log", json={
       "tool_name": "test",
       "location": "Test City",
       "parameters": {},
       "result": {},
       "execution_time_ms": 100
   })
   ```

### Dashboard Shows Old Data

The dashboard uses in-memory storage. Restart it to clear:
```bash
# Stop the app (Ctrl+C)
python app.py  # Restart fresh
```

## Performance Considerations

* Logging uses a **1-second timeout** and doesn't block the MCP response
* Failed logging attempts are silently ignored
* No retry logic - if logging fails, the query isn't recorded
* Consider adding retries or queue-based logging for production

## Production Deployment

For production use:

1. **Replace in-memory storage** with Lakebase or Unity Catalog table
2. **Add authentication** to the dashboard API
3. **Use async logging** to avoid any MCP latency
4. **Add monitoring** for the logging mechanism itself
5. **Set up alerts** for logging failures
