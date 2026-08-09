# Weather MCP Server - Quick Start Guide 🚀

Get your weather MCP server up and running in 5 minutes!

## Prerequisites

- Databricks workspace
- Databricks CLI installed and configured
- Python 3.8+ (for local testing)

## Step 1: Verify Installation

Check that all required files are present:

```bash
cd databricks-lakebase-app-day-3/weather-mpc
ls -la
```

You should see:
- `weather_mcp_server.py` - Main MCP server
- `weather_broker.py` - API adapter
- `requirements.txt` - Dependencies
- `app.yaml` - App configuration
- `README.md` - Full documentation
- `test_weather.py` - Test suite

## Step 2: Test Locally (Optional)

Before deploying, test that everything works:

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
python test_weather.py
```

Expected output:
```
✅ Success!
   Location: San Francisco, United States
   Temperature: 13.9°C (57.0°F)
   Conditions: Foggy
   ...
```

## Step 3: Deploy to Databricks

Deploy as a Databricks App:

```bash
# Deploy the app
databricks apps deploy weather-mcp-server

# Check status
databricks apps get weather-mcp-server

# View logs
databricks apps logs weather-mcp-server
```

## Step 4: Get the MCP Server URL

```bash
databricks apps get weather-mcp-server
```

Look for the `url` field in the output. It will look like:
```
https://<workspace-url>/serving-endpoints/weather-mcp-server/...
```

## Step 5: Register with Agent Bricks

1. Open your Agent Bricks agent configuration
2. Add a new external MCP server
3. Paste the URL from Step 4
4. Save the configuration

## Step 6: Test from Agent

Ask your agent questions like:

- "What's the weather in New York?"
- "Give me a 7-day forecast for Tokyo"
- "Do I need an umbrella in Seattle tomorrow?"
- "Should I travel to Barcelona next week?"

## Available MCP Tools

Your agent can now call these tools:

### 1. `get_current_weather(location)`
```
Agent: get_current_weather("Paris")
Returns: Current temp, conditions, humidity, wind, etc.
```

### 2. `get_forecast(location, days)`
```
Agent: get_forecast("London", days=5)
Returns: 5-day forecast with daily details
```

### 3. `predict_umbrella_needed(location, date)`
```
Agent: predict_umbrella_needed("Seattle", "2026-08-15")
Returns: Yes/No + reasoning + weather details
```

### 4. `get_travel_recommendation(location, date)`
```
Agent: get_travel_recommendation("Barcelona", "2026-08-20")
Returns: Travel score, packing list, activities, precautions
```

## Troubleshooting

### App won't start
```bash
# Check logs for errors
databricks apps logs weather-mcp-server --follow

# Verify requirements are installed
databricks apps get weather-mcp-server
```

### "Location not found" errors
- Make sure location names are spelled correctly
- Try with country: "London, UK" instead of just "London"
- Use major city names for best results

### API timeouts
- Open-Meteo is free and reliable, but check your internet connection
- The broker has a 10-second timeout for each API call
- Retry the request if it times out

### Agent can't reach MCP server
- Verify the URL is correct
- Check that the app is running: `databricks apps get weather-mcp-server`
- Ensure the agent configuration has the correct endpoint URL

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Explore the [weather_broker.py](weather_broker.py) to customize API calls
- Extend with new tools (historical weather, alerts, etc.)
- Monitor usage via app logs

## Support

For issues or questions:
1. Check the logs: `databricks apps logs weather-mcp-server`
2. Review the [README.md](README.md) for detailed info
3. Test locally with `test_weather.py` to isolate issues

---

**Built with:**
- [FastMCP](https://github.com/jlowin/fastmcp) - MCP framework
- [Open-Meteo](https://open-meteo.com) - Free weather API
- Pattern inspired by `mcp_server/alpaca_mcp_server.py`
