# Weather MCP Server 🌤️

A Model Context Protocol (MCP) server providing weather predictions and recommendations, built with FastMCP and backed by the free Open-Meteo API.

## Features

This MCP server exposes four weather tools that can be called by any MCP client (e.g., Databricks Agent Bricks):

### 1. **get_current_weather(location)** 🌡️
Get real-time weather conditions for any location.

**Parameters:**
- `location` (str): City name, address, or location string (e.g., "San Francisco", "London, UK", "Tokyo")

**Returns:**
- Current temperature (Celsius and Fahrenheit)
- Feels-like temperature
- Weather conditions (e.g., "Clear sky", "Moderate rain")
- Humidity, wind speed, wind direction
- Precipitation and pressure
- ISO timestamp of observation

**Example:**
```python
result = get_current_weather("Seattle")
# Returns current conditions including temperature, humidity, wind, etc.
```

### 2. **get_forecast(location, days)** 📅
Get weather forecast for the next N days (up to 16 days).

**Parameters:**
- `location` (str): City name or location string
- `days` (int, optional): Number of days to forecast (1-16, default 7)

**Returns:**
- Location details
- Daily forecasts with:
  - Date
  - Max/min temperatures (°C and °F)
  - Precipitation probability and expected rainfall
  - Weather conditions
  - Wind speed and direction

**Example:**
```python
result = get_forecast("Paris", days=5)
# Returns 5-day forecast for Paris
```

### 3. **predict_umbrella_needed(location, date)** ☂️
Intelligent umbrella recommendation based on forecast data.

**Parameters:**
- `location` (str): City name or location string
- `date` (str, optional): Date in YYYY-MM-DD format (default: today)

**Returns:**
- Boolean recommendation (umbrella needed or not)
- Reasoning and explanation
- Relevant weather details (precipitation probability, conditions)

**Logic:**
An umbrella is recommended if:
- Precipitation probability > 40%, OR
- Forecast shows rain/drizzle/thunderstorm, OR
- Expected precipitation > 2mm

**Example:**
```python
result = predict_umbrella_needed("New York", "2026-08-15")
# Returns: "☂️ Yes, bring an umbrella! 65% chance of precipitation..."
```

### 4. **get_travel_recommendation(location, date)** ✈️
Comprehensive travel recommendation with packing suggestions and activity ideas.

**Parameters:**
- `location` (str): Travel destination city or location
- `date` (str, optional): Date in YYYY-MM-DD format (default: today)

**Returns:**
- Travel score (0-10) based on weather conditions
- Overall recommendation (Excellent/Good/Fair/Poor)
- Packing suggestions (umbrella, sunscreen, warm jacket, etc.)
- Activity recommendations (outdoor vs. indoor)
- Safety precautions and weather warnings
- Detailed weather summary

**Example:**
```python
result = get_travel_recommendation("Barcelona", "2026-08-20")
# Returns comprehensive travel advice with score, packing list, activities
```

## Architecture

### weather_broker.py 🔧
The adapter module containing all HTTP calls and parsing logic:
- `get_geocode(location)`: Convert location names to lat/lon coordinates
- `get_current_weather(location)`: Fetch current weather from Open-Meteo
- `get_forecast(location, days)`: Fetch forecast data from Open-Meteo
- `_weather_code_to_description(code)`: Convert WMO weather codes to human-readable descriptions

**No MCP logic here** - pure HTTP/parsing/data transformation.

### weather_mcp_server.py 🚀
The FastMCP server exposing weather tools:
- Thin `@mcp.tool` decorators wrapping `weather_broker` functions
- Request tracing with session IDs and execution times
- Standardized response format (status, message, result)
- Middleware for capturing end-user identity from Databricks headers

**All business logic is delegated to weather_broker.py.**

## API: Open-Meteo

This server uses the **free Open-Meteo API** (https://open-meteo.com):
- ✅ **No API key required**
- ✅ **No credit card needed**
- ✅ **No rate limits for reasonable use**
- ✅ Provides accurate weather data from national weather services
- ✅ Supports geocoding, current weather, and 16-day forecasts

### Endpoints used:
- **Geocoding API**: `https://geocoding-api.open-meteo.com/v1/search`
- **Weather Forecast API**: `https://api.open-meteo.com/v1/forecast`

## Deployment

### Deploy as Databricks App

1. Navigate to the `weather-mpc` directory:
```bash
cd databricks-lakebase-app-day-3/weather-mpc
```

2. Deploy using Databricks CLI:
```bash
databricks apps deploy weather-mcp-server
```

3. Get the app URL:
```bash
databricks apps get weather-mcp-server
```

4. Register the MCP server URL in your Agent Bricks agent configuration.

### Local Development

Run the server locally for testing:

```bash
cd weather-mpc
pip install -r requirements.txt
python weather_mcp_server.py
```

The server will start on the default FastMCP port and log all tool calls.

## Testing

### Test from Python

```python
import requests

# Assuming server is running locally on port 8000
base_url = "http://localhost:8000"

# Test get_current_weather
response = requests.post(f"{base_url}/tools/get_current_weather", 
                        json={"location": "Seattle"})
print(response.json())

# Test get_forecast
response = requests.post(f"{base_url}/tools/get_forecast",
                        json={"location": "Tokyo", "days": 3})
print(response.json())

# Test predict_umbrella_needed
response = requests.post(f"{base_url}/tools/predict_umbrella_needed",
                        json={"location": "London", "date": "2026-08-15"})
print(response.json())

# Test get_travel_recommendation
response = requests.post(f"{base_url}/tools/get_travel_recommendation",
                        json={"location": "Paris", "date": "2026-09-01"})
print(response.json())
```

## Requirements

- Python 3.8+
- databricks-sdk >= 0.30.0
- fastmcp >= 3.2.0
- requests >= 2.31.0
- python-dotenv >= 1.0.1

See `requirements.txt` for exact versions.

## Response Format

All tools return standardized responses:

```json
{
  "tool_name": "get_current_weather",
  "status": "success",
  "execution_time_ms": 156.42,
  "message": "get_current_weather executed successfully",
  "result": {
    // Actual tool result here
  }
}
```

Error responses:

```json
{
  "tool_name": "get_forecast",
  "status": "error",
  "execution_time_ms": 89.21,
  "message": "get_forecast failed: Location not found",
  "error_details": {
    "error_type": "ValueError",
    "error_message": "Location not found: InvalidCity"
  }
}
```

## Comparison with Alpaca MCP Server

This weather MCP server follows the exact same pattern as `mcp_server/alpaca_mcp_server.py`:

| Aspect | Alpaca MCP Server | Weather MCP Server |
|--------|-------------------|-------------------|
| **Framework** | FastMCP | FastMCP |
| **Adapter Module** | `alpaca_broker.py` | `weather_broker.py` |
| **Tool Decorator** | `@mcp.tool` + `@_trace_tool_call` | `@mcp.tool` + `@_trace_tool_call` |
| **Secrets Management** | Databricks secrets (API keys) | None needed (free API) |
| **Request Tracing** | Session IDs, user email, execution time | Session IDs, user email, execution time |
| **Response Format** | Standardized (status, message, result) | Standardized (status, message, result) |
| **Middleware** | Captures Databricks user headers | Captures Databricks user headers |

## Future Enhancements (Optional)

- 🌪️ **Severe weather alerts**: Fetch and display active weather warnings
- 📊 **Historical weather lookup**: Query past weather data for analysis
- 🌍 **Multi-location comparison**: Compare weather across multiple cities
- 🌡️ **Temperature trends**: Show temperature changes over time
- 🌊 **Marine weather**: Add ocean/coastal weather conditions

## License

MIT License - Free to use and modify.

## Credits

- Built with [FastMCP](https://github.com/jlowin/fastmcp)
- Weather data from [Open-Meteo](https://open-meteo.com)
- Pattern inspired by `mcp_server/alpaca_mcp_server.py`
