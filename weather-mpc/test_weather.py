"""
Test script for the Weather MCP Server.

Run this to verify that the weather broker functions work correctly
before deploying as a Databricks App.

Usage:
    python test_weather.py
"""

import weather_broker


def test_current_weather():
    """Test get_current_weather function."""
    print("\n" + "="*60)
    print("TEST 1: Get Current Weather for San Francisco")
    print("="*60)
    
    try:
        result = weather_broker.get_current_weather("San Francisco")
        print(f"✅ Success!")
        print(f"Location: {result['location']['name']}, {result['location']['country']}")
        print(f"Temperature: {result['temperature']}°C ({result['temperature_f']}°F)")
        print(f"Feels like: {result['feels_like']}°C")
        print(f"Conditions: {result['conditions']}")
        print(f"Humidity: {result['humidity']}%")
        print(f"Wind Speed: {result['wind_speed']} km/h ({result['wind_speed_mph']} mph)")
        print(f"Precipitation: {result['precipitation']} mm")
        print(f"As of: {result['as_of']}")
    except Exception as e:
        print(f"❌ Failed: {e}")


def test_forecast():
    """Test get_forecast function."""
    print("\n" + "="*60)
    print("TEST 2: Get 5-Day Forecast for London")
    print("="*60)
    
    try:
        result = weather_broker.get_forecast("London", days=5)
        print(f"✅ Success!")
        print(f"Location: {result['location']['name']}, {result['location']['country']}")
        print(f"\nForecast:")
        
        for day in result['forecast_days']:
            print(f"\n  📅 {day['date']}")
            print(f"     Temp: {day['temp_min']}°C to {day['temp_max']}°C")
            print(f"     Conditions: {day['conditions']}")
            print(f"     Precipitation: {day['precipitation_probability']}% chance, {day['precipitation_sum']}mm")
            print(f"     Wind: {day['wind_speed_max']} km/h")
    except Exception as e:
        print(f"❌ Failed: {e}")


def test_geocoding():
    """Test geocoding for various locations."""
    print("\n" + "="*60)
    print("TEST 3: Geocoding Multiple Locations")
    print("="*60)
    
    locations = ["Tokyo", "New York", "Sydney", "Paris", "Dubai"]
    
    for location in locations:
        try:
            result = weather_broker.get_geocode(location)
            print(f"✅ {result['name']}, {result['country']}")
            print(f"   Coordinates: {result['latitude']}, {result['longitude']}")
            print(f"   Timezone: {result['timezone']}")
        except Exception as e:
            print(f"❌ {location}: Failed - {e}")


def test_edge_cases():
    """Test edge cases and error handling."""
    print("\n" + "="*60)
    print("TEST 4: Edge Cases and Error Handling")
    print("="*60)
    
    # Test invalid location
    print("\n1. Invalid location:")
    try:
        result = weather_broker.get_current_weather("XYZABC123InvalidCity")
        print(f"❌ Should have failed but didn't")
    except ValueError as e:
        print(f"✅ Correctly caught error: {e}")
    except Exception as e:
        print(f"⚠️ Unexpected error type: {e}")
    
    # Test maximum forecast days
    print("\n2. Maximum forecast days (16):")
    try:
        result = weather_broker.get_forecast("Seattle", days=16)
        print(f"✅ Success! Got {len(result['forecast_days'])} days")
    except Exception as e:
        print(f"❌ Failed: {e}")
    
    # Test with coordinates-like location
    print("\n3. Location with special characters:")
    try:
        result = weather_broker.get_current_weather("São Paulo")
        print(f"✅ Success! {result['location']['name']}")
    except Exception as e:
        print(f"❌ Failed: {e}")


def main():
    """Run all tests."""
    print("\n" + "#"*60)
    print("# Weather MCP Server - Test Suite")
    print("#"*60)
    
    test_current_weather()
    test_forecast()
    test_geocoding()
    test_edge_cases()
    
    print("\n" + "="*60)
    print("All tests completed!")
    print("="*60)


if __name__ == "__main__":
    main()
