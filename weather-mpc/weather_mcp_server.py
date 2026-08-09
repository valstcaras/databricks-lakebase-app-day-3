"""
Weather Predictions MCP Server.

Exposes weather prediction and forecasting tools over MCP (Model Context Protocol)
so a Databricks Agent Bricks agent can call them like any other tool:
    - get_current_weather(location)
    - get_forecast(location, days)
    - predict_umbrella_needed(location, date)
    - get_travel_recommendation(location, date)

Built with FastMCP and backed by the free Open-Meteo API (no API key required).
All HTTP/parsing logic is delegated to weather_broker.py - MCP tool functions
stay thin and focused on standardization and response formatting.

Deploy this as its own Databricks App (same app.yaml + FastMCP entrypoint
pattern) so an Agent Bricks agent can register its URL as an external MCP server.

Run locally:
    python weather_mcp_server.py
"""

import os
import logging
import functools
import time
import uuid
import json
from contextvars import ContextVar
from datetime import datetime, timedelta

from fastmcp import FastMCP
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

import weather_broker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("weather-mcp-server")

# Context variable to store request headers for accessing end-user identity
_request_context: ContextVar[dict] = ContextVar('request_context', default={})

# Context variable to store session ID for tracing
_session_id: ContextVar[str] = ContextVar('session_id', default=None)


def _get_end_user_email() -> str:
    """Get the actual end user's email from request headers, or fallback to service principal."""
    # Try to get from X-Forwarded-User header (Databricks App context)
    headers = _request_context.get()
    forwarded_user = headers.get('x-forwarded-user')
    if forwarded_user:
        return forwarded_user
    
    # Fallback: use service principal (local development or non-App contexts)
    try:
        from databricks.sdk import WorkspaceClient
        w = WorkspaceClient()
        return w.current_user.me().user_name or 'unknown@databricks.com'
    except:
        return 'unknown@databricks.com'


def _trace_tool_call(func):
    """Decorator to trace MCP tool calls and standardize response format.
    
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
            
            logger.info(f"Tool {tool_name} executed successfully in {duration_ms:.2f}ms for user {user_email}")
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
            
            logger.error(f"Tool {tool_name} failed after {duration_ms:.2f}ms: {e}")
            
            # Return the standardized error instead of raising
            return standardized_error
    
    return wrapper


mcp = FastMCP("weather-predictions")


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
def get_current_weather(location: str) -> dict:
    """
    Get current weather conditions for a location.

    Args:
        location: City name, address, or location string (e.g., "San Francisco", 
                 "London, UK", "New York"). Can also be a zip code or coordinates.

    Returns:
        A dict with current weather including:
        - location: Location details (name, country, lat/lon)
        - temperature: Current temperature in Celsius and Fahrenheit
        - feels_like: Apparent temperature
        - conditions: Weather description (e.g., "Clear sky", "Moderate rain")
        - humidity: Relative humidity percentage
        - wind_speed: Wind speed in km/h and mph
        - wind_direction: Wind direction in degrees
        - precipitation: Current precipitation in mm
        - pressure: Surface pressure in hPa
        - as_of: ISO timestamp of observation
    """
    return weather_broker.get_current_weather(location)


@mcp.tool
@_trace_tool_call
def get_forecast(location: str, days: int = 7) -> dict:
    """
    Get weather forecast for the next N days.

    Args:
        location: City name, address, or location string (e.g., "Seattle", 
                 "Tokyo, Japan").
        days: Number of days to forecast (1-16, default 7). Maximum 16 days.

    Returns:
        A dict with:
        - location: Location details
        - forecast_days: List of daily forecasts, each containing:
            - date: Date string (YYYY-MM-DD)
            - temp_max/temp_min: Max/min temperatures (Celsius and Fahrenheit)
            - precipitation_probability: Chance of precipitation (0-100%)
            - precipitation_sum: Total precipitation in mm
            - conditions: Weather description
            - wind_speed_max: Maximum wind speed (km/h and mph)
            - wind_direction: Dominant wind direction in degrees
        - generated_at: ISO timestamp when forecast was generated
    """
    return weather_broker.get_forecast(location, days)


@mcp.tool
@_trace_tool_call
def predict_umbrella_needed(location: str, date: str = None) -> dict:
    """
    Predict whether an umbrella will be needed at a location on a specific date.
    
    This is a derived judgment call based on forecast data. An umbrella is
    recommended if precipitation probability exceeds 40% or if heavy rain
    conditions are forecast.

    Args:
        location: City name, address, or location string.
        date: Date string in YYYY-MM-DD format. If not provided, uses today.
              Can be up to 16 days in the future.

    Returns:
        A dict with:
        - location: Location details
        - date: The date being checked
        - umbrella_needed: Boolean - True if umbrella recommended
        - recommendation: Human-readable recommendation message
        - reasoning: Explanation of why umbrella is/isn't needed
        - weather_details: Relevant weather details (precipitation, conditions)
    """
    # Parse target date
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return {
                "error": "Invalid date format. Use YYYY-MM-DD.",
                "date_provided": date
            }
    else:
        target_date = datetime.now()
    
    # Calculate days from now
    days_from_now = (target_date.date() - datetime.now().date()).days
    
    if days_from_now < 0:
        return {
            "error": "Cannot predict for past dates. Please provide today or a future date.",
            "date_requested": target_date.strftime("%Y-%m-%d")
        }
    
    if days_from_now > 16:
        return {
            "error": "Forecast only available for up to 16 days in the future.",
            "date_requested": target_date.strftime("%Y-%m-%d")
        }
    
    # Get forecast
    forecast_data = weather_broker.get_forecast(location, min(days_from_now + 1, 16))
    
    # Find the matching day
    target_date_str = target_date.strftime("%Y-%m-%d")
    day_forecast = None
    for day in forecast_data["forecast_days"]:
        if day["date"] == target_date_str:
            day_forecast = day
            break
    
    if not day_forecast:
        return {
            "error": "No forecast data available for the requested date.",
            "date_requested": target_date_str
        }
    
    # Apply umbrella logic
    precip_prob = day_forecast["precipitation_probability"]
    conditions = day_forecast["conditions"].lower()
    precip_sum = day_forecast["precipitation_sum"]
    
    # Umbrella needed if:
    # 1. Precipitation probability > 40%, OR
    # 2. Rain/drizzle/thunderstorm in conditions, OR
    # 3. Expected precipitation > 2mm
    umbrella_needed = (
        precip_prob > 40 or 
        any(word in conditions for word in ["rain", "drizzle", "thunderstorm", "shower"]) or
        precip_sum > 2
    )
    
    # Generate reasoning
    if umbrella_needed:
        reasons = []
        if precip_prob > 40:
            reasons.append(f"{precip_prob}% chance of precipitation")
        if precip_sum > 2:
            reasons.append(f"{precip_sum}mm of rain expected")
        if any(word in conditions for word in ["rain", "drizzle", "thunderstorm", "shower"]):
            reasons.append(f"forecast shows {conditions}")
        
        reasoning = "Umbrella recommended: " + ", ".join(reasons)
        recommendation = f"☂️ Yes, bring an umbrella! {reasoning}"
    else:
        recommendation = f"☀️ No umbrella needed. Low chance of rain ({precip_prob}%) with {conditions}."
        reasoning = f"Low precipitation risk: {precip_prob}% probability, {conditions}"
    
    return {
        "location": forecast_data["location"],
        "date": target_date_str,
        "umbrella_needed": umbrella_needed,
        "recommendation": recommendation,
        "reasoning": reasoning,
        "weather_details": {
            "precipitation_probability": precip_prob,
            "precipitation_sum": precip_sum,
            "conditions": day_forecast["conditions"],
            "temp_max": day_forecast["temp_max"],
            "temp_min": day_forecast["temp_min"],
        }
    }


@mcp.tool
@_trace_tool_call
def get_travel_recommendation(location: str, date: str = None) -> dict:
    """
    Get travel recommendation for a location on a specific date based on
    weather conditions.
    
    Analyzes forecast data to provide a travel suitability score and specific
    recommendations for outdoor activities, packing, and precautions.

    Args:
        location: City name, address, or location string for travel destination.
        date: Date string in YYYY-MM-DD format. If not provided, uses today.
              Can be up to 16 days in the future.

    Returns:
        A dict with:
        - location: Location details
        - date: The date being analyzed
        - travel_score: Numerical score (0-10) for travel suitability
        - overall_recommendation: Brief summary (Excellent/Good/Fair/Poor conditions)
        - packing_suggestions: List of items to bring
        - activity_recommendations: Suggested activities based on weather
        - precautions: Safety warnings or precautions to take
        - weather_summary: Detailed weather information for the date
    """
    # Parse target date
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return {
                "error": "Invalid date format. Use YYYY-MM-DD.",
                "date_provided": date
            }
    else:
        target_date = datetime.now()
    
    # Calculate days from now
    days_from_now = (target_date.date() - datetime.now().date()).days
    
    if days_from_now < 0:
        return {
            "error": "Cannot provide recommendations for past dates.",
            "date_requested": target_date.strftime("%Y-%m-%d")
        }
    
    if days_from_now > 16:
        return {
            "error": "Forecast only available for up to 16 days in the future.",
            "date_requested": target_date.strftime("%Y-%m-%d")
        }
    
    # Get forecast
    forecast_data = weather_broker.get_forecast(location, min(days_from_now + 1, 16))
    
    # Find the matching day
    target_date_str = target_date.strftime("%Y-%m-%d")
    day_forecast = None
    for day in forecast_data["forecast_days"]:
        if day["date"] == target_date_str:
            day_forecast = day
            break
    
    if not day_forecast:
        return {
            "error": "No forecast data available for the requested date.",
            "date_requested": target_date_str
        }
    
    # Analyze weather for travel score
    precip_prob = day_forecast["precipitation_probability"]
    temp_max = day_forecast["temp_max"]
    temp_min = day_forecast["temp_min"]
    conditions = day_forecast["conditions"].lower()
    wind_speed = day_forecast["wind_speed_max"]
    
    # Calculate travel score (0-10)
    score = 10.0
    
    # Temperature comfort (ideal: 15-25°C)
    if temp_max > 35 or temp_max < 0:
        score -= 3
    elif temp_max > 30 or temp_max < 5:
        score -= 2
    elif temp_max < 10 or temp_max > 28:
        score -= 1
    
    # Precipitation impact
    if precip_prob > 70:
        score -= 3
    elif precip_prob > 50:
        score -= 2
    elif precip_prob > 30:
        score -= 1
    
    # Severe weather
    if "thunderstorm" in conditions or "heavy" in conditions:
        score -= 2
    
    # Wind impact
    if wind_speed > 50:
        score -= 2
    elif wind_speed > 35:
        score -= 1
    
    score = max(0, min(10, score))
    
    # Generate recommendations
    if score >= 8:
        overall = "🌟 Excellent conditions for travel"
    elif score >= 6:
        overall = "👍 Good conditions for travel"
    elif score >= 4:
        overall = "⚠️ Fair conditions - some weather challenges"
    else:
        overall = "❌ Poor conditions - consider rescheduling"
    
    # Packing suggestions
    packing = []
    if precip_prob > 30:
        packing.append("Umbrella or rain jacket")
    if temp_max > 25:
        packing.extend(["Sunscreen", "Hat", "Light clothing", "Water bottle"])
    elif temp_max < 15:
        packing.extend(["Warm jacket", "Layers", "Gloves (if below 5°C)"])
    if wind_speed > 30:
        packing.append("Windbreaker")
    
    # Activity recommendations
    activities = []
    if score >= 7 and precip_prob < 30:
        activities.extend(["Outdoor sightseeing", "Walking tours", "Parks and gardens"])
    if precip_prob > 40 or score < 6:
        activities.extend(["Indoor museums", "Shopping centers", "Indoor attractions"])
    if temp_max > 28:
        activities.append("Water activities or air-conditioned venues")
    
    # Precautions
    precautions = []
    if "thunderstorm" in conditions:
        precautions.append("⚡ Severe weather alert: Stay indoors during thunderstorms")
    if wind_speed > 50:
        precautions.append("💨 High winds: Secure loose items, avoid exposed areas")
    if temp_max > 35:
        precautions.append("🌡️ Extreme heat: Stay hydrated, avoid midday sun")
    elif temp_max < 0:
        precautions.append("❄️ Freezing temperatures: Dress warmly, watch for ice")
    if precip_prob > 70:
        precautions.append("🌧️ High chance of rain: Plan indoor backup activities")
    
    return {
        "location": forecast_data["location"],
        "date": target_date_str,
        "travel_score": round(score, 1),
        "overall_recommendation": overall,
        "packing_suggestions": packing if packing else ["Standard travel items"],
        "activity_recommendations": activities if activities else ["Flexible planning recommended"],
        "precautions": precautions if precautions else ["No special precautions needed"],
        "weather_summary": {
            "conditions": day_forecast["conditions"],
            "temperature_range": f"{day_forecast['temp_min']}°C to {day_forecast['temp_max']}°C "
                                f"({day_forecast['temp_min_f']}°F to {day_forecast['temp_max_f']}°F)",
            "precipitation_probability": f"{precip_prob}%",
            "expected_rainfall": f"{day_forecast['precipitation_sum']}mm",
            "max_wind_speed": f"{wind_speed} km/h ({day_forecast['wind_speed_max_mph']} mph)",
        }
    }


if __name__ == "__main__":
    # Add middleware to capture request headers for end-user identity
    # This must be done before mcp.run() is called
    if hasattr(mcp, 'app') and mcp.app is not None:
        mcp.app.add_middleware(RequestContextMiddleware)
    
    logger.info("Starting Weather Predictions MCP Server...")
    logger.info("Exposing tools: get_current_weather, get_forecast, predict_umbrella_needed, get_travel_recommendation")
    
    # Databricks Apps route external HTTP traffic to this port via app.yaml;
    # streamable-http is the transport Databricks' MCP client/gateway expects
    port = int(os.getenv("DATABRICKS_APP_PORT", os.getenv("PORT", 8000)))
    mcp.run(transport="http", host="0.0.0.0", port=port)
