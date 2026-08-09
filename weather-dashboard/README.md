# Weather Dashboard 🌤️

A monitoring dashboard that displays recent weather queries and predictions made by Agent Bricks through the Weather MCP server.

## Features

* **Real-time Monitoring**: View all weather queries as they happen
* **Query Statistics**: Track total queries by tool type (current weather, forecasts, umbrella predictions, travel recommendations)
* **Location Analytics**: See which locations are queried most frequently
* **Detailed Results**: View full query parameters and results for each request
* **Auto-refresh**: Dashboard updates automatically every 5 seconds

## Dashboard Views

### Summary Cards
- Total queries across all tools
- Breakdown by query type:
  - Current weather checks
  - Weather forecasts
  - Umbrella predictions
  - Travel recommendations

### Top Locations
Shows the most frequently queried locations with query counts

### Recent Queries
Detailed view of the last 20 queries with:
- Tool type and icon
- Location
- Timestamp
- Key results (temperature, conditions, precipitation, etc.)

## Running Locally

```bash
cd weather-dashboard
pip install -r requirements.txt
python app.py
```

The dashboard will be available at `http://localhost:8002`

## Deploy as Databricks App

1. From the Databricks workspace, navigate to this folder
2. Create a new Databricks App pointing to this directory
3. The app will automatically use `app.yaml` configuration
4. Deploy and access via the provided app URL

## Integration with Weather MCP Server

The dashboard logs queries in two ways:

### Option 1: Automatic Logging (Recommended)
Modify your `weather_mcp_server.py` to POST query data to the dashboard:

```python
import requests

DASHBOARD_URL = "http://localhost:8002/api/log"

def log_to_dashboard(tool_name, location, parameters, result, execution_time):
    try:
        requests.post(DASHBOARD_URL, json={
            "tool_name": tool_name,
            "location": location,
            "parameters": parameters,
            "result": result,
            "execution_time_ms": execution_time
        }, timeout=1)
    except:
        pass  # Don't fail the MCP call if logging fails
```

### Option 2: Manual Testing
Use the included test script to generate sample queries:

```bash
python test_dashboard.py
```

## Architecture

```
weather-dashboard/
├── app.py                 # Flask web server with API endpoints
├── query_logger.py        # In-memory query storage and statistics
├── templates/
│   └── index.html        # Dashboard UI
├── requirements.txt       # Python dependencies
├── app.yaml              # Databricks App configuration
└── README.md             # This file
```

## API Endpoints

- `GET /` - Dashboard UI
- `GET /api/queries?limit=N` - Get recent queries (default: 50)
- `GET /api/stats` - Get aggregated statistics
- `POST /api/log` - Log a new query (called by MCP server)
- `GET /healthz` - Health check

## Storage

Currently uses in-memory storage (last 1000 queries). To persist data:

1. **Extend to Lakebase**: Modify `query_logger.py` to write to a Lakebase Postgres table
2. **Use Unity Catalog**: Store queries in a Delta table for analysis
3. **Add persistence**: Use SQLite or other lightweight database

## Future Enhancements

- [ ] Add filtering by location, tool type, or date range
- [ ] Export query history to CSV
- [ ] Add charts/graphs for query trends over time
- [ ] Location map visualization
- [ ] Query performance metrics
- [ ] Alert on unusual query patterns
