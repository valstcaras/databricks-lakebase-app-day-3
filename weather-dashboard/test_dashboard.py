"""
Test script to generate sample weather queries for the dashboard.

Run this to populate the dashboard with sample data for testing.
"""

import requests
import time
import random
from datetime import datetime, timedelta

DASHBOARD_URL = "http://localhost:8002/api/log"

# Sample data
locations = [
    "San Francisco", "London", "Tokyo", "Paris", "New York",
    "Seattle", "Los Angeles", "Barcelona", "Sydney", "Berlin"
]

conditions_list = [
    "Sunny", "Partly cloudy", "Cloudy", "Overcast", "Foggy",
    "Light rain", "Moderate rain", "Heavy rain", "Clear sky"
]


def generate_current_weather(location):
    """Generate a sample current weather query."""
    return {
        "tool_name": "get_current_weather",
        "location": location,
        "parameters": {"location": location},
        "result": {
            "location": {
                "name": location,
                "country": "Unknown",
                "latitude": round(random.uniform(-90, 90), 4),
                "longitude": round(random.uniform(-180, 180), 4),
                "timezone": "UTC"
            },
            "temperature": round(random.uniform(-5, 35), 1),
            "temperature_f": round(random.uniform(23, 95), 1),
            "feels_like": round(random.uniform(-5, 35), 1),
            "conditions": random.choice(conditions_list),
            "humidity": random.randint(30, 100),
            "wind_speed": round(random.uniform(0, 40), 1),
            "wind_speed_mph": round(random.uniform(0, 25), 1),
            "wind_direction": random.randint(0, 360),
            "precipitation": round(random.uniform(0, 5), 1),
            "pressure": round(random.uniform(990, 1030), 1),
            "as_of": datetime.utcnow().isoformat()
        },
        "timestamp": datetime.utcnow().isoformat(),
        "execution_time_ms": round(random.uniform(100, 500), 2)
    }


def generate_forecast(location):
    """Generate a sample forecast query."""
    days = random.randint(1, 7)
    forecast_days = []
    
    for i in range(days):
        forecast_days.append({
            "date": (datetime.utcnow() + timedelta(days=i)).strftime("%Y-%m-%d"),
            "temp_max": round(random.uniform(15, 35), 1),
            "temp_max_f": round(random.uniform(59, 95), 1),
            "temp_min": round(random.uniform(5, 20), 1),
            "temp_min_f": round(random.uniform(41, 68), 1),
            "precipitation_probability": random.randint(0, 100),
            "precipitation_sum": round(random.uniform(0, 10), 1),
            "conditions": random.choice(conditions_list),
            "wind_speed_max": round(random.uniform(5, 30), 1),
            "wind_speed_max_mph": round(random.uniform(3, 19), 1),
            "wind_direction": random.randint(0, 360)
        })
    
    return {
        "tool_name": "get_forecast",
        "location": location,
        "parameters": {"location": location, "days": days},
        "result": {
            "location": {"name": location},
            "forecast_days": forecast_days,
            "generated_at": datetime.utcnow().isoformat()
        },
        "timestamp": datetime.utcnow().isoformat(),
        "execution_time_ms": round(random.uniform(200, 600), 2)
    }


def generate_umbrella_prediction(location):
    """Generate a sample umbrella prediction query."""
    precipitation_prob = random.randint(0, 100)
    umbrella_needed = precipitation_prob > 30
    
    return {
        "tool_name": "predict_umbrella_needed",
        "location": location,
        "parameters": {
            "location": location,
            "date": (datetime.utcnow() + timedelta(days=random.randint(0, 3))).strftime("%Y-%m-%d")
        },
        "result": {
            "location": {"name": location},
            "umbrella_needed": umbrella_needed,
            "recommendation": f"{'☂️ Yes, bring an umbrella!' if umbrella_needed else '☀️ No umbrella needed.'}",
            "reasoning": f"{'High' if umbrella_needed else 'Low'} precipitation risk",
            "weather_details": {
                "precipitation_probability": precipitation_prob,
                "precipitation_sum": round(random.uniform(0, 10), 1),
                "conditions": random.choice(conditions_list),
                "temp_max": round(random.uniform(15, 30), 1),
                "temp_min": round(random.uniform(5, 20), 1)
            }
        },
        "timestamp": datetime.utcnow().isoformat(),
        "execution_time_ms": round(random.uniform(150, 450), 2)
    }


def generate_travel_recommendation(location):
    """Generate a sample travel recommendation query."""
    travel_score = round(random.uniform(2, 10), 1)
    
    if travel_score >= 7:
        recommendation = "🌟 Excellent conditions for travel"
    elif travel_score >= 5:
        recommendation = "👍 Good conditions for travel"
    else:
        recommendation = "⚠️ Fair conditions - some weather challenges"
    
    return {
        "tool_name": "get_travel_recommendation",
        "location": location,
        "parameters": {
            "location": location,
            "date": (datetime.utcnow() + timedelta(days=random.randint(1, 10))).strftime("%Y-%m-%d")
        },
        "result": {
            "location": {"name": location},
            "travel_score": travel_score,
            "overall_recommendation": recommendation,
            "packing_suggestions": ["Sunscreen", "Hat", "Light clothing"],
            "activity_recommendations": ["Outdoor sightseeing", "Walking tours"],
            "weather_summary": {
                "conditions": random.choice(conditions_list),
                "temperature_range": "20-28°C",
                "precipitation_probability": f"{random.randint(0, 50)}%"
            }
        },
        "timestamp": datetime.utcnow().isoformat(),
        "execution_time_ms": round(random.uniform(250, 700), 2)
    }


def send_query(query_data):
    """Send a query to the dashboard."""
    try:
        response = requests.post(DASHBOARD_URL, json=query_data, timeout=2)
        if response.status_code == 200:
            print(f"✓ Logged {query_data['tool_name']} for {query_data['location']}")
        else:
            print(f"✗ Failed to log query: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"✗ Error connecting to dashboard: {e}")


def main():
    """Generate and send sample queries."""
    print("Weather Dashboard Test Script")
    print("==============================")
    print(f"Sending queries to: {DASHBOARD_URL}\n")
    
    generators = [
        generate_current_weather,
        generate_forecast,
        generate_umbrella_prediction,
        generate_travel_recommendation
    ]
    
    # Generate 20 sample queries
    for i in range(20):
        location = random.choice(locations)
        generator = random.choice(generators)
        query_data = generator(location)
        send_query(query_data)
        time.sleep(0.5)  # Small delay between queries
    
    print("\n✅ Done! Check your dashboard at http://localhost:8002")


if __name__ == "__main__":
    main()
