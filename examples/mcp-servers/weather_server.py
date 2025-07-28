#!/usr/bin/env python3
"""
Weather MCP Server

A simple MCP server that provides weather information.
This server uses mock data for demonstration purposes.

Usage:
    python weather_server.py [--transport stdio|sse] [--port PORT]
"""

import json
import asyncio
import argparse
import os
from datetime import datetime, timedelta
import random

from mcp.server.fastmcp import FastMCP


# Initialize FastMCP server
mcp = FastMCP("weather-server")

# Mock weather data
WEATHER_CONDITIONS = [
    "Sunny", "Partly Cloudy", "Cloudy", "Rainy", 
    "Thunderstorms", "Snowy", "Foggy", "Windy"
]


@mcp.tool()
async def get_weather(location: str, units: str = "celsius") -> dict:
    """
    Get current weather for a location.
    
    Args:
        location: City name or location
        units: Temperature units - 'celsius' or 'fahrenheit'
    
    Returns:
        Current weather data
    """
    if units not in ["celsius", "fahrenheit"]:
        raise ValueError("Units must be 'celsius' or 'fahrenheit'")
    
    # Generate mock weather data
    temp_c = random.randint(-10, 35)
    temp_f = int(temp_c * 9/5 + 32)
    temp = temp_f if units == "fahrenheit" else temp_c
    unit_symbol = "°F" if units == "fahrenheit" else "°C"
    
    return {
        "location": location,
        "timestamp": datetime.now().isoformat(),
        "condition": random.choice(WEATHER_CONDITIONS),
        "temperature": f"{temp}{unit_symbol}",
        "feels_like": f"{temp + random.randint(-3, 3)}{unit_symbol}",
        "humidity": f"{random.randint(30, 90)}%",
        "wind_speed": f"{random.randint(0, 30)} km/h",
        "pressure": f"{random.randint(980, 1040)} hPa",
        "visibility": f"{random.randint(5, 20)} km"
    }


@mcp.tool()
async def get_forecast(location: str, days: int = 3, units: str = "celsius") -> dict:
    """
    Get weather forecast for a location.
    
    Args:
        location: City name or location
        days: Number of days to forecast (1-7)
        units: Temperature units - 'celsius' or 'fahrenheit'
    
    Returns:
        Weather forecast data
    """
    if units not in ["celsius", "fahrenheit"]:
        raise ValueError("Units must be 'celsius' or 'fahrenheit'")
    
    days = min(max(days, 1), 7)
    unit_symbol = "°F" if units == "fahrenheit" else "°C"
    forecast_data = []
    
    for i in range(days):
        date = (datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d")
        
        # Generate temperatures
        high_c = random.randint(10, 35)
        low_c = high_c - random.randint(5, 15)
        
        if units == "fahrenheit":
            high = int(high_c * 9/5 + 32)
            low = int(low_c * 9/5 + 32)
        else:
            high = high_c
            low = low_c
        
        forecast_data.append({
            "date": date,
            "condition": random.choice(WEATHER_CONDITIONS),
            "high": f"{high}{unit_symbol}",
            "low": f"{low}{unit_symbol}",
            "precipitation_chance": f"{random.randint(0, 100)}%",
            "wind_speed": f"{random.randint(0, 30)} km/h"
        })
    
    return {
        "location": location,
        "forecast_days": days,
        "units": units,
        "forecast": forecast_data
    }


@mcp.tool()
async def get_alerts(location: str) -> dict:
    """
    Get weather alerts for a location.
    
    Args:
        location: City name or location
    
    Returns:
        Weather alerts if any
    """
    # Randomly generate alerts (or none)
    alerts = []
    if random.random() > 0.7:  # 30% chance of alerts
        alert_types = [
            ("Heavy Rain Warning", "Heavy rainfall expected in the next 24 hours"),
            ("High Wind Advisory", "Strong winds up to 60 km/h expected"),
            ("Heat Wave Alert", "Temperatures exceeding 35°C expected"),
            ("Fog Advisory", "Dense fog may reduce visibility"),
            ("Thunderstorm Watch", "Severe thunderstorms possible this evening")
        ]
        
        num_alerts = random.randint(1, 2)
        selected_alerts = random.sample(alert_types, num_alerts)
        
        for alert_type, description in selected_alerts:
            alerts.append({
                "type": alert_type,
                "severity": random.choice(["Low", "Moderate", "High"]),
                "description": description,
                "issued": datetime.now().isoformat(),
                "expires": (datetime.now() + timedelta(hours=random.randint(6, 24))).isoformat()
            })
    
    return {
        "location": location,
        "alerts": alerts,
        "alert_count": len(alerts)
    }


# Resources
@mcp.resource("weather://current/{city}")
def get_current_weather_resource(city: str) -> str:
    """Get current weather as a resource."""
    # For sync resource, we need to use the mock data directly
    location = city.replace("-", " ").title()
    
    # Generate mock weather data (same logic as get_weather but sync)
    condition = random.choice(WEATHER_CONDITIONS)
    temp_celsius = random.randint(-10, 35)
    
    weather_data = {
        "location": location,
        "timestamp": datetime.now().isoformat(),
        "condition": condition,
        "temperature": f"{temp_celsius}°C",
        "feels_like": f"{temp_celsius - 2}°C",
        "humidity": f"{random.randint(30, 90)}%",
        "wind_speed": f"{random.randint(0, 50)} km/h",
        "wind_direction": random.choice(["N", "NE", "E", "SE", "S", "SW", "W", "NW"]),
        "pressure": f"{random.randint(980, 1040)} hPa",
        "visibility": f"{random.randint(5, 20)} km",
        "uv_index": random.randint(0, 11)
    }
    
    return json.dumps(weather_data, indent=2)


# Prompts
@mcp.prompt()
async def weather_report(location: str, include_forecast: bool = True) -> str:
    """
    Generate a comprehensive weather report.
    
    Args:
        location: Location for the weather report
        include_forecast: Whether to include forecast in report
    
    Returns:
        Prompt text for weather report
    """
    prompt_text = f"""Please generate a comprehensive weather report for {location}.

Include the following:
1. Current weather conditions (temperature, humidity, wind, etc.)
2. Any active weather alerts
"""
    if include_forecast:
        prompt_text += "3. 3-day weather forecast with daily highs/lows and conditions\n"
    
    prompt_text += """
Format the report in a clear, easy-to-read format suitable for the general public.
Use the get_weather, get_alerts, and get_forecast tools to gather the necessary data."""
    
    return prompt_text


@mcp.prompt()
async def travel_weather(destination: str, travel_date: str, duration_days: int = 7) -> str:
    """
    Get weather information for travel planning.
    
    Args:
        destination: Travel destination
        travel_date: Date of travel (YYYY-MM-DD)
        duration_days: Duration of stay in days
    
    Returns:
        Prompt text for travel weather planning
    """
    return f"""Please provide weather information for travel planning to {destination}.

Travel details:
- Destination: {destination}
- Travel date: {travel_date}
- Duration: {duration_days} days

Please provide:
1. Current weather conditions at the destination
2. Weather forecast for the travel period
3. Any weather alerts or advisories
4. Packing recommendations based on expected weather
5. Best and worst weather days during the stay

Use the available weather tools to gather comprehensive information."""


@mcp.prompt()
async def weather_comparison(location1: str, location2: str) -> str:
    """
    Compare weather between two locations.
    
    Args:
        location1: First location
        location2: Second location
    
    Returns:
        Prompt text for weather comparison
    """
    return f"""Please compare the current weather between {location1} and {location2}.

Include:
1. Current conditions in both locations
2. Temperature difference
3. Which location has better weather and why
4. 3-day forecast comparison
5. Any significant weather alerts in either location

Use the weather tools to gather data for both locations and present a clear comparison."""


if __name__ == "__main__":
    import sys
    
    # For stdio transport, just run with default settings
    print(f"Starting Weather MCP Server", file=sys.stderr)
    
    # FastMCP handles stdio transport automatically when run without arguments
    mcp.run()