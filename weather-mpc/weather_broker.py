"""
Weather data adapter module for Open-Meteo API.

This module handles all HTTP calls and parsing logic for fetching weather data
from the free Open-Meteo API (https://open-meteo.com). No API key required.

Functions:
    - get_current_weather(location): Get current weather conditions
    - get_forecast(location, days): Get weather forecast for N days
    - get_geocode(location): Convert location name to lat/lon coordinates
"""

import requests
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger("weather-broker")

# Open-Meteo API endpoints
GEOCODING_API = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_API = "https://api.open-meteo.com/v1/forecast"


def get_geocode(location: str) -> Dict:
    """
    Convert a location name (city, address) to latitude/longitude coordinates.
    
    Args:
        location: City name, address, or location string (e.g., "San Francisco", "London")
    
    Returns:
        Dict with name, latitude, longitude, country, timezone
    
    Raises:
        ValueError: If location cannot be found
    """
    try:
        params = {
            "name": location,
            "count": 1,
            "language": "en",
            "format": "json"
        }
        
        response = requests.get(GEOCODING_API, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if not data.get("results"):
            raise ValueError(f"Location not found: {location}")
        
        result = data["results"][0]
        return {
            "name": result.get("name", location),
            "latitude": result["latitude"],
            "longitude": result["longitude"],
            "country": result.get("country", "Unknown"),
            "timezone": result.get("timezone", "UTC"),
            "admin1": result.get("admin1", ""),  # State/region
        }
        
    except requests.RequestException as e:
        logger.error(f"Failed to geocode location {location}: {e}")
        raise ValueError(f"Failed to geocode location: {str(e)}")


def get_current_weather(location: str) -> Dict:
    """
    Get current weather conditions for a location.
    
    Args:
        location: City name, address, or location string
    
    Returns:
        Dict with:
            - location: Location info (name, country, lat/lon)
            - temperature: Current temperature in Celsius
            - temperature_f: Current temperature in Fahrenheit
            - conditions: Weather description (e.g., "Clear sky", "Overcast")
            - humidity: Relative humidity percentage
            - wind_speed: Wind speed in km/h
            - wind_speed_mph: Wind speed in mph
            - wind_direction: Wind direction in degrees
            - precipitation: Current precipitation in mm
            - pressure: Surface pressure in hPa
            - as_of: ISO timestamp of observation
    """
    try:
        # First, geocode the location
        geo = get_geocode(location)
        
        # Fetch current weather
        params = {
            "latitude": geo["latitude"],
            "longitude": geo["longitude"],
            "current": [
                "temperature_2m",
                "relative_humidity_2m",
                "apparent_temperature",
                "precipitation",
                "weather_code",
                "surface_pressure",
                "wind_speed_10m",
                "wind_direction_10m"
            ],
            "timezone": "auto",
            "temperature_unit": "celsius",
            "wind_speed_unit": "kmh"
        }
        
        response = requests.get(WEATHER_API, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        current = data["current"]
        
        # Map WMO weather codes to descriptions
        weather_code = current.get("weather_code", 0)
        conditions = _weather_code_to_description(weather_code)
        
        temp_c = current.get("temperature_2m", 0)
        temp_f = (temp_c * 9/5) + 32
        wind_kmh = current.get("wind_speed_10m", 0)
        wind_mph = wind_kmh * 0.621371
        
        return {
            "location": {
                "name": geo["name"],
                "country": geo["country"],
                "latitude": geo["latitude"],
                "longitude": geo["longitude"],
                "timezone": geo["timezone"],
            },
            "temperature": round(temp_c, 1),
            "temperature_f": round(temp_f, 1),
            "feels_like": round(current.get("apparent_temperature", temp_c), 1),
            "conditions": conditions,
            "humidity": current.get("relative_humidity_2m", 0),
            "wind_speed": round(wind_kmh, 1),
            "wind_speed_mph": round(wind_mph, 1),
            "wind_direction": current.get("wind_direction_10m", 0),
            "precipitation": current.get("precipitation", 0),
            "pressure": current.get("surface_pressure", 0),
            "as_of": current.get("time", datetime.now().isoformat()),
        }
        
    except Exception as e:
        logger.error(f"Failed to get current weather for {location}: {e}")
        raise


def get_forecast(location: str, days: int = 7) -> Dict:
    """
    Get weather forecast for the next N days.
    
    Args:
        location: City name, address, or location string
        days: Number of days to forecast (1-16, default 7)
    
    Returns:
        Dict with:
            - location: Location info
            - forecast_days: List of daily forecasts, each with:
                - date: Date string (YYYY-MM-DD)
                - temp_max: Maximum temperature in Celsius
                - temp_max_f: Maximum temperature in Fahrenheit
                - temp_min: Minimum temperature in Celsius
                - temp_min_f: Minimum temperature in Fahrenheit
                - precipitation_probability: Chance of precipitation (0-100%)
                - precipitation_sum: Total precipitation in mm
                - conditions: Weather description
                - wind_speed_max: Maximum wind speed in km/h
                - wind_speed_max_mph: Maximum wind speed in mph
    """
    try:
        # Validate days
        if days < 1:
            days = 1
        elif days > 16:
            days = 16
        
        # Geocode the location
        geo = get_geocode(location)
        
        # Fetch forecast
        params = {
            "latitude": geo["latitude"],
            "longitude": geo["longitude"],
            "daily": [
                "weather_code",
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_sum",
                "precipitation_probability_max",
                "wind_speed_10m_max",
                "wind_direction_10m_dominant"
            ],
            "timezone": "auto",
            "temperature_unit": "celsius",
            "wind_speed_unit": "kmh",
            "forecast_days": days
        }
        
        response = requests.get(WEATHER_API, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        daily = data["daily"]
        forecast_list = []
        
        for i in range(len(daily["time"])):
            temp_max_c = daily["temperature_2m_max"][i]
            temp_min_c = daily["temperature_2m_min"][i]
            temp_max_f = (temp_max_c * 9/5) + 32
            temp_min_f = (temp_min_c * 9/5) + 32
            wind_kmh = daily["wind_speed_10m_max"][i]
            wind_mph = wind_kmh * 0.621371
            
            forecast_list.append({
                "date": daily["time"][i],
                "temp_max": round(temp_max_c, 1),
                "temp_max_f": round(temp_max_f, 1),
                "temp_min": round(temp_min_c, 1),
                "temp_min_f": round(temp_min_f, 1),
                "precipitation_probability": daily["precipitation_probability_max"][i] or 0,
                "precipitation_sum": daily["precipitation_sum"][i] or 0,
                "conditions": _weather_code_to_description(daily["weather_code"][i]),
                "wind_speed_max": round(wind_kmh, 1),
                "wind_speed_max_mph": round(wind_mph, 1),
                "wind_direction": daily["wind_direction_10m_dominant"][i] or 0,
            })
        
        return {
            "location": {
                "name": geo["name"],
                "country": geo["country"],
                "latitude": geo["latitude"],
                "longitude": geo["longitude"],
                "timezone": geo["timezone"],
            },
            "forecast_days": forecast_list,
            "generated_at": datetime.now().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Failed to get forecast for {location}: {e}")
        raise


def _weather_code_to_description(code: int) -> str:
    """
    Convert WMO weather code to human-readable description.
    
    WMO codes: https://open-meteo.com/en/docs
    """
    code_map = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Foggy",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        56: "Light freezing drizzle",
        57: "Dense freezing drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        66: "Light freezing rain",
        67: "Heavy freezing rain",
        71: "Slight snow fall",
        73: "Moderate snow fall",
        75: "Heavy snow fall",
        77: "Snow grains",
        80: "Slight rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        85: "Slight snow showers",
        86: "Heavy snow showers",
        95: "Thunderstorm",
        96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail",
    }
    
    return code_map.get(code, "Unknown")
