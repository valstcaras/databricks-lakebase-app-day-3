# Weather MCP Server - API Examples

This document shows example requests and responses for each MCP tool.

## 1. get_current_weather()

### Request
```json
{
  "location": "San Francisco"
}
```

### Response
```json
{
  "tool_name": "get_current_weather",
  "status": "success",
  "execution_time_ms": 234.56,
  "message": "get_current_weather executed successfully",
  "result": {
    "location": {
      "name": "San Francisco",
      "country": "United States",
      "latitude": 37.7749,
      "longitude": -122.4194,
      "timezone": "America/Los_Angeles"
    },
    "temperature": 13.9,
    "temperature_f": 57.0,
    "feels_like": 13.2,
    "conditions": "Foggy",
    "humidity": 100,
    "wind_speed": 14.8,
    "wind_speed_mph": 9.2,
    "wind_direction": 270,
    "precipitation": 0.0,
    "pressure": 1013.2,
    "as_of": "2026-08-09T10:00:00"
  }
}
```

---

## 2. get_forecast()

### Request
```json
{
  "location": "London",
  "days": 3
}
```

### Response
```json
{
  "tool_name": "get_forecast",
  "status": "success",
  "execution_time_ms": 312.78,
  "message": "get_forecast executed successfully",
  "result": {
    "location": {
      "name": "London",
      "country": "United Kingdom",
      "latitude": 51.5074,
      "longitude": -0.1278,
      "timezone": "Europe/London"
    },
    "forecast_days": [
      {
        "date": "2026-08-09",
        "temp_max": 31.8,
        "temp_max_f": 89.2,
        "temp_min": 19.1,
        "temp_min_f": 66.4,
        "precipitation_probability": 2,
        "precipitation_sum": 0.0,
        "conditions": "Overcast",
        "wind_speed_max": 18.5,
        "wind_speed_max_mph": 11.5,
        "wind_direction": 225
      },
      {
        "date": "2026-08-10",
        "temp_max": 26.8,
        "temp_max_f": 80.2,
        "temp_min": 19.2,
        "temp_min_f": 66.6,
        "precipitation_probability": 0,
        "precipitation_sum": 0.0,
        "conditions": "Overcast",
        "wind_speed_max": 15.2,
        "wind_speed_max_mph": 9.4,
        "wind_direction": 180
      },
      {
        "date": "2026-08-11",
        "temp_max": 24.5,
        "temp_max_f": 76.1,
        "temp_min": 17.5,
        "temp_min_f": 63.5,
        "precipitation_probability": 0,
        "precipitation_sum": 0.0,
        "conditions": "Partly cloudy",
        "wind_speed_max": 12.8,
        "wind_speed_max_mph": 8.0,
        "wind_direction": 200
      }
    ],
    "generated_at": "2026-08-09T10:15:23"
  }
}
```

---

## 3. predict_umbrella_needed()

### Request (Rainy Day)
```json
{
  "location": "Seattle",
  "date": "2026-08-15"
}
```

### Response (Umbrella Needed)
```json
{
  "tool_name": "predict_umbrella_needed",
  "status": "success",
  "execution_time_ms": 298.45,
  "message": "predict_umbrella_needed executed successfully",
  "result": {
    "location": {
      "name": "Seattle",
      "country": "United States",
      "latitude": 47.6062,
      "longitude": -122.3321,
      "timezone": "America/Los_Angeles"
    },
    "date": "2026-08-15",
    "umbrella_needed": true,
    "recommendation": "☂️ Yes, bring an umbrella! Umbrella recommended: 65% chance of precipitation, forecast shows moderate rain",
    "reasoning": "Umbrella recommended: 65% chance of precipitation, forecast shows moderate rain",
    "weather_details": {
      "precipitation_probability": 65,
      "precipitation_sum": 5.2,
      "conditions": "Moderate rain",
      "temp_max": 18.5,
      "temp_min": 12.3
    }
  }
}
```

### Request (Sunny Day)
```json
{
  "location": "Los Angeles",
  "date": "2026-08-15"
}
```

### Response (No Umbrella Needed)
```json
{
  "tool_name": "predict_umbrella_needed",
  "status": "success",
  "execution_time_ms": 276.12,
  "message": "predict_umbrella_needed executed successfully",
  "result": {
    "location": {
      "name": "Los Angeles",
      "country": "United States",
      "latitude": 34.0522,
      "longitude": -118.2437,
      "timezone": "America/Los_Angeles"
    },
    "date": "2026-08-15",
    "umbrella_needed": false,
    "recommendation": "☀️ No umbrella needed. Low chance of rain (5%) with clear sky.",
    "reasoning": "Low precipitation risk: 5% probability, clear sky",
    "weather_details": {
      "precipitation_probability": 5,
      "precipitation_sum": 0.0,
      "conditions": "Clear sky",
      "temp_max": 28.5,
      "temp_min": 21.2
    }
  }
}
```

---

## 4. get_travel_recommendation()

### Request (Good Travel Conditions)
```json
{
  "location": "Barcelona",
  "date": "2026-08-20"
}
```

### Response (Excellent Conditions)
```json
{
  "tool_name": "get_travel_recommendation",
  "status": "success",
  "execution_time_ms": 342.89,
  "message": "get_travel_recommendation executed successfully",
  "result": {
    "location": {
      "name": "Barcelona",
      "country": "Spain",
      "latitude": 41.3851,
      "longitude": 2.1734,
      "timezone": "Europe/Madrid"
    },
    "date": "2026-08-20",
    "travel_score": 8.5,
    "overall_recommendation": "🌟 Excellent conditions for travel",
    "packing_suggestions": [
      "Sunscreen",
      "Hat",
      "Light clothing",
      "Water bottle"
    ],
    "activity_recommendations": [
      "Outdoor sightseeing",
      "Walking tours",
      "Parks and gardens"
    ],
    "precautions": [
      "No special precautions needed"
    ],
    "weather_summary": {
      "conditions": "Mainly clear",
      "temperature_range": "20.5°C to 29.8°C (68.9°F to 85.6°F)",
      "precipitation_probability": "10%",
      "expected_rainfall": "0.0mm",
      "max_wind_speed": "15.2 km/h (9.4 mph)"
    }
  }
}
```

### Request (Poor Travel Conditions)
```json
{
  "location": "London",
  "date": "2026-11-15"
}
```

### Response (Fair/Poor Conditions)
```json
{
  "tool_name": "get_travel_recommendation",
  "status": "success",
  "execution_time_ms": 367.23,
  "message": "get_travel_recommendation executed successfully",
  "result": {
    "location": {
      "name": "London",
      "country": "United Kingdom",
      "latitude": 51.5074,
      "longitude": -0.1278,
      "timezone": "Europe/London"
    },
    "date": "2026-11-15",
    "travel_score": 4.5,
    "overall_recommendation": "⚠️ Fair conditions - some weather challenges",
    "packing_suggestions": [
      "Umbrella or rain jacket",
      "Warm jacket",
      "Layers",
      "Windbreaker"
    ],
    "activity_recommendations": [
      "Indoor museums",
      "Shopping centers",
      "Indoor attractions"
    ],
    "precautions": [
      "🌧️ High chance of rain: Plan indoor backup activities"
    ],
    "weather_summary": {
      "conditions": "Moderate rain",
      "temperature_range": "6.2°C to 10.5°C (43.2°F to 50.9°F)",
      "precipitation_probability": "75%",
      "expected_rainfall": "8.5mm",
      "max_wind_speed": "28.5 km/h (17.7 mph)"
    }
  }
}
```

---

## Error Response Example

### Request (Invalid Location)
```json
{
  "location": "InvalidCityXYZ123"
}
```

### Response
```json
{
  "tool_name": "get_current_weather",
  "status": "error",
  "execution_time_ms": 156.78,
  "message": "get_current_weather failed: Location not found: InvalidCityXYZ123",
  "error_details": {
    "error_type": "ValueError",
    "error_message": "Location not found: InvalidCityXYZ123"
  }
}
```

---

## Usage Tips

### Location Formats
All tools accept flexible location formats:
- City name: `"San Francisco"`, `"Tokyo"`, `"Paris"`
- City with country: `"London, UK"`, `"Sydney, Australia"`
- Specific regions: `"Brooklyn, New York"`, `"Cambridge, Massachusetts"`

### Date Formats
For `predict_umbrella_needed()` and `get_travel_recommendation()`:
- Format: `YYYY-MM-DD` (ISO 8601)
- Examples: `"2026-08-15"`, `"2026-12-25"`
- Omit date to use today
- Maximum 16 days in the future

### Response Structure
All tools return the same standardized wrapper:
```json
{
  "tool_name": "<function_name>",
  "status": "success" | "error",
  "execution_time_ms": <float>,
  "message": "<description>",
  "result": { ... } | "error_details": { ... }
}
```

This makes it easy to parse responses consistently across all tools.
