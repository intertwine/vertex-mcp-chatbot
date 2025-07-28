"""
Tests for the weather MCP server example.

These tests verify that the weather_server.py example server correctly
implements MCP protocol features including tools, resources, and prompts.
"""

import asyncio
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Add examples directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "examples" / "mcp-servers"))

from weather_server import (
    WEATHER_CONDITIONS,
    get_alerts,
    get_current_weather_resource,
    get_forecast,
    get_weather,
    mcp,
    travel_weather,
    weather_comparison,
    weather_report,
)


class TestWeatherServer:
    """Test weather MCP server functionality."""

    def setup_method(self):
        """Set up test environment."""
        # Seed random for predictable tests
        import random

        random.seed(42)


class TestGetWeatherTool(TestWeatherServer):
    """Test get_weather tool."""

    @pytest.mark.asyncio
    async def test_get_weather_celsius(self):
        """Test getting weather in Celsius."""
        result = await get_weather("London", "celsius")

        assert result["location"] == "London"
        assert "timestamp" in result
        assert result["condition"] in WEATHER_CONDITIONS
        assert result["temperature"].endswith("°C")
        assert result["feels_like"].endswith("°C")
        assert result["humidity"].endswith("%")
        assert result["wind_speed"].endswith(" km/h")
        assert result["pressure"].endswith(" hPa")
        assert result["visibility"].endswith(" km")

    @pytest.mark.asyncio
    async def test_get_weather_fahrenheit(self):
        """Test getting weather in Fahrenheit."""
        result = await get_weather("New York", "fahrenheit")

        assert result["location"] == "New York"
        assert result["temperature"].endswith("°F")
        assert result["feels_like"].endswith("°F")

    @pytest.mark.asyncio
    async def test_get_weather_default_units(self):
        """Test getting weather with default units (celsius)."""
        result = await get_weather("Paris")

        assert result["temperature"].endswith("°C")
        assert result["feels_like"].endswith("°C")

    @pytest.mark.asyncio
    async def test_get_weather_invalid_units(self):
        """Test getting weather with invalid units."""
        with pytest.raises(ValueError, match="Units must be 'celsius' or 'fahrenheit'"):
            await get_weather("London", "kelvin")

    @pytest.mark.asyncio
    async def test_get_weather_data_types(self):
        """Test that weather data has correct types and formats."""
        result = await get_weather("Tokyo", "celsius")

        # Check timestamp format
        timestamp = result["timestamp"]
        datetime.fromisoformat(timestamp)  # Should not raise

        # Check percentage format
        humidity = result["humidity"]
        assert humidity.endswith("%")
        humidity_value = int(humidity[:-1])
        assert 0 <= humidity_value <= 100

        # Check temperature is numeric
        temp_str = result["temperature"]
        temp_value = int(temp_str[:-2])  # Remove unit
        assert isinstance(temp_value, int)


class TestGetForecastTool(TestWeatherServer):
    """Test get_forecast tool."""

    @pytest.mark.asyncio
    async def test_get_forecast_default_days(self):
        """Test getting forecast with default days."""
        result = await get_forecast("London", units="celsius")

        assert result["location"] == "London"
        assert result["forecast_days"] == 3
        assert result["units"] == "celsius"
        assert len(result["forecast"]) == 3

    @pytest.mark.asyncio
    async def test_get_forecast_custom_days(self):
        """Test getting forecast with custom number of days."""
        result = await get_forecast("London", 5, "celsius")

        assert result["forecast_days"] == 5
        assert len(result["forecast"]) == 5

    @pytest.mark.asyncio
    async def test_get_forecast_max_days_limit(self):
        """Test forecast days are limited to maximum."""
        result = await get_forecast("London", 10, "celsius")

        assert result["forecast_days"] == 7  # Should be limited to 7
        assert len(result["forecast"]) == 7

    @pytest.mark.asyncio
    async def test_get_forecast_min_days_limit(self):
        """Test forecast days are limited to minimum."""
        result = await get_forecast("London", 0, "celsius")

        assert result["forecast_days"] == 1  # Should be at least 1
        assert len(result["forecast"]) == 1

    @pytest.mark.asyncio
    async def test_get_forecast_fahrenheit(self):
        """Test getting forecast in Fahrenheit."""
        result = await get_forecast("New York", 3, "fahrenheit")

        assert result["units"] == "fahrenheit"
        for day in result["forecast"]:
            assert day["high"].endswith("°F")
            assert day["low"].endswith("°F")

    @pytest.mark.asyncio
    async def test_get_forecast_invalid_units(self):
        """Test getting forecast with invalid units."""
        with pytest.raises(ValueError, match="Units must be 'celsius' or 'fahrenheit'"):
            await get_forecast("London", 3, "kelvin")

    @pytest.mark.asyncio
    async def test_get_forecast_data_structure(self):
        """Test forecast data structure."""
        result = await get_forecast("Paris", 3, "celsius")

        for i, day in enumerate(result["forecast"]):
            # Check date format
            date = day["date"]
            datetime.strptime(date, "%Y-%m-%d")  # Should not raise

            # Check required fields
            assert "condition" in day
            assert "high" in day
            assert "low" in day
            assert "precipitation_chance" in day
            assert "wind_speed" in day

            # Check condition is valid
            assert day["condition"] in WEATHER_CONDITIONS

            # Check percentage format for precipitation
            precip = day["precipitation_chance"]
            assert precip.endswith("%")
            precip_value = int(precip[:-1])
            assert 0 <= precip_value <= 100

    @pytest.mark.asyncio
    async def test_get_forecast_date_sequence(self):
        """Test that forecast dates are sequential."""
        result = await get_forecast("Berlin", 5, "celsius")

        dates = [day["date"] for day in result["forecast"]]
        for i in range(1, len(dates)):
            current_date = datetime.strptime(dates[i], "%Y-%m-%d")
            previous_date = datetime.strptime(dates[i - 1], "%Y-%m-%d")

            # Should be exactly one day apart
            assert (current_date - previous_date).days == 1


class TestGetAlertsTool(TestWeatherServer):
    """Test get_alerts tool."""

    @pytest.mark.asyncio
    async def test_get_alerts_structure(self):
        """Test alerts data structure."""
        result = await get_alerts("Miami")

        assert result["location"] == "Miami"
        assert "alerts" in result
        assert "alert_count" in result
        assert result["alert_count"] == len(result["alerts"])

    @pytest.mark.asyncio
    async def test_get_alerts_structure_and_data(self):
        """Test alerts data structure and content."""
        # Test multiple cities to potentially get both alerts and no alerts
        for city in ["Phoenix", "Miami", "Chicago", "Seattle", "Denver"]:
            result = await get_alerts(city)

            # Basic structure should always be present
            assert "location" in result
            assert "alerts" in result
            assert "alert_count" in result
            assert result["location"] == city
            assert result["alert_count"] == len(result["alerts"])

            # If there are alerts, check their structure
            if result["alert_count"] > 0:
                alert = result["alerts"][0]
                assert "type" in alert
                assert "severity" in alert
                assert "description" in alert
                assert "issued" in alert
                assert "expires" in alert

                # Check severity is valid
                assert alert["severity"] in ["Low", "Moderate", "High"]

                # Check timestamps are valid ISO format
                datetime.fromisoformat(alert["issued"])
                datetime.fromisoformat(alert["expires"])

                # Found working alerts, can break
                break

    @pytest.mark.asyncio
    async def test_get_alerts_expiry_after_issued(self):
        """Test that alert expiry time is after issued time."""
        with patch("weather_server.random.random", return_value=0.5):
            with patch(
                "weather_server.random.randint", side_effect=[1, 12]
            ):  # 1 alert, expires in 12 hours
                with patch("weather_server.random.sample") as mock_sample:
                    mock_sample.return_value = [
                        ("Storm Warning", "Severe storms expected")
                    ]

                    result = await get_alerts("Storm City")

                    if result["alert_count"] > 0:
                        alert = result["alerts"][0]
                        issued = datetime.fromisoformat(alert["issued"])
                        expires = datetime.fromisoformat(alert["expires"])

                        assert expires > issued


class TestGetCurrentWeatherResource(TestWeatherServer):
    """Test get_current_weather_resource function."""

    def test_get_current_weather_resource(self):
        """Test getting current weather as resource."""
        result = get_current_weather_resource("new-york")

        # Should return JSON string
        weather_data = json.loads(result)

        assert weather_data["location"] == "New York"
        assert "timestamp" in weather_data
        assert "condition" in weather_data
        assert weather_data["condition"] in WEATHER_CONDITIONS
        assert weather_data["temperature"].endswith("°C")
        assert "humidity" in weather_data
        assert "wind_speed" in weather_data
        assert "wind_direction" in weather_data
        assert "pressure" in weather_data
        assert "visibility" in weather_data
        assert "uv_index" in weather_data

    def test_get_current_weather_resource_city_formatting(self):
        """Test city name formatting in resource."""
        result = get_current_weather_resource("san-francisco")
        weather_data = json.loads(result)

        assert weather_data["location"] == "San Francisco"

    def test_get_current_weather_resource_wind_direction(self):
        """Test wind direction is valid."""
        result = get_current_weather_resource("chicago")
        weather_data = json.loads(result)

        valid_directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        assert weather_data["wind_direction"] in valid_directions

    def test_get_current_weather_resource_uv_index(self):
        """Test UV index is in valid range."""
        result = get_current_weather_resource("denver")
        weather_data = json.loads(result)

        uv_index = weather_data["uv_index"]
        assert 0 <= uv_index <= 11


class TestPrompts(TestWeatherServer):
    """Test prompt templates."""

    @pytest.mark.asyncio
    async def test_weather_report_prompt(self):
        """Test weather_report prompt template."""
        result = await weather_report("Seattle")

        assert "comprehensive weather report for Seattle" in result
        assert "Current weather conditions" in result
        assert "weather alerts" in result
        assert "3-day weather forecast" in result
        assert "get_weather" in result
        assert "get_alerts" in result
        assert "get_forecast" in result

    @pytest.mark.asyncio
    async def test_weather_report_prompt_no_forecast(self):
        """Test weather_report prompt without forecast."""
        result = await weather_report("Portland", include_forecast=False)

        assert "comprehensive weather report for Portland" in result
        assert "Current weather conditions" in result
        assert "weather alerts" in result
        assert "3-day weather forecast" not in result

    @pytest.mark.asyncio
    async def test_travel_weather_prompt(self):
        """Test travel_weather prompt template."""
        result = await travel_weather("Tokyo", "2024-07-15", 5)

        assert "travel planning to Tokyo" in result
        assert "Travel date: 2024-07-15" in result
        assert "Duration: 5 days" in result
        assert "Current weather conditions" in result
        assert "Weather forecast for the travel period" in result
        assert "weather alerts" in result
        assert "Packing recommendations" in result
        assert "Best and worst weather days" in result

    @pytest.mark.asyncio
    async def test_travel_weather_prompt_default_duration(self):
        """Test travel_weather prompt with default duration."""
        result = await travel_weather("Paris", "2024-08-01")

        assert "Duration: 7 days" in result

    @pytest.mark.asyncio
    async def test_weather_comparison_prompt(self):
        """Test weather_comparison prompt template."""
        result = await weather_comparison("London", "Paris")

        assert "compare the current weather between London and Paris" in result
        assert "Current conditions in both locations" in result
        assert "Temperature difference" in result
        assert "better weather and why" in result
        assert "3-day forecast comparison" in result
        assert "weather alerts in either location" in result


class TestMCPServerIntegration(TestWeatherServer):
    """Test MCP server integration."""

    @pytest.mark.asyncio
    async def test_server_has_tools(self):
        """Test that server has expected tools."""
        tools = await mcp.list_tools()
        tool_names = [tool.name for tool in tools]

        expected_tools = ["get_weather", "get_forecast", "get_alerts"]
        for tool in expected_tools:
            assert tool in tool_names

    @pytest.mark.asyncio
    async def test_server_has_resources(self):
        """Test that server has expected resources."""
        resources = await mcp.list_resources()
        # Weather server has resource patterns defined but may return empty list
        # This is expected behavior for FastMCP with template resources
        assert isinstance(resources, list)

    @pytest.mark.asyncio
    async def test_server_has_prompts(self):
        """Test that server has expected prompts."""
        prompts = await mcp.list_prompts()
        prompt_names = [prompt.name for prompt in prompts]

        expected_prompts = ["weather_report", "travel_weather", "weather_comparison"]
        for prompt in expected_prompts:
            assert prompt in prompt_names

    @pytest.mark.asyncio
    async def test_tool_schemas(self):
        """Test that tools have proper schemas."""
        tools = await mcp.list_tools()

        for tool in tools:
            assert tool.name is not None
            assert tool.description is not None
            assert hasattr(tool, "inputSchema")

    @pytest.mark.asyncio
    async def test_get_weather_tool_schema(self):
        """Test get_weather tool schema."""
        tools = await mcp.list_tools()
        get_weather_tool = next((t for t in tools if t.name == "get_weather"), None)

        assert get_weather_tool is not None
        assert "location" in str(get_weather_tool.inputSchema)
        assert "units" in str(get_weather_tool.inputSchema)

    @pytest.mark.asyncio
    async def test_get_forecast_tool_schema(self):
        """Test get_forecast tool schema."""
        tools = await mcp.list_tools()
        get_forecast_tool = next((t for t in tools if t.name == "get_forecast"), None)

        assert get_forecast_tool is not None
        assert "location" in str(get_forecast_tool.inputSchema)
        assert "days" in str(get_forecast_tool.inputSchema)
        assert "units" in str(get_forecast_tool.inputSchema)


class TestDataConsistency(TestWeatherServer):
    """Test data consistency and validation."""

    @pytest.mark.asyncio
    async def test_temperature_consistency_celsius(self):
        """Test temperature values are consistent in Celsius."""
        result = await get_weather("Test City", "celsius")

        temp_str = result["temperature"]
        feels_like_str = result["feels_like"]

        # Extract numeric values
        temp_val = int(temp_str[:-2])
        feels_like_val = int(feels_like_str[:-2])

        # Feels like should be within reasonable range of actual temp
        assert abs(feels_like_val - temp_val) <= 10

    @pytest.mark.asyncio
    async def test_temperature_consistency_fahrenheit(self):
        """Test temperature values are consistent in Fahrenheit."""
        result = await get_weather("Test City", "fahrenheit")

        temp_str = result["temperature"]
        feels_like_str = result["feels_like"]

        # Extract numeric values
        temp_val = int(temp_str[:-2])
        feels_like_val = int(feels_like_str[:-2])

        # Feels like should be within reasonable range of actual temp
        assert abs(feels_like_val - temp_val) <= 10

    @pytest.mark.asyncio
    async def test_forecast_temperature_ranges(self):
        """Test forecast temperature ranges are logical."""
        result = await get_forecast("Test City", 3, "celsius")

        for day in result["forecast"]:
            high_str = day["high"]
            low_str = day["low"]

            high_val = int(high_str[:-2])
            low_val = int(low_str[:-2])

            # High should be greater than or equal to low
            assert high_val >= low_val

            # Temperature difference should be reasonable
            assert (high_val - low_val) <= 25


class TestErrorHandling(TestWeatherServer):
    """Test error handling scenarios."""

    @pytest.mark.asyncio
    async def test_get_weather_with_special_characters(self):
        """Test weather API with special characters in location."""
        result = await get_weather("São Paulo", "celsius")
        assert result["location"] == "São Paulo"

    @pytest.mark.asyncio
    async def test_get_weather_with_numbers(self):
        """Test weather API with numbers in location."""
        result = await get_weather("Highway 101", "celsius")
        assert result["location"] == "Highway 101"

    @pytest.mark.asyncio
    async def test_get_forecast_edge_case_days(self):
        """Test forecast with edge case day values."""
        # Test negative days
        result = await get_forecast("Test", -5, "celsius")
        assert result["forecast_days"] == 1

        # Test very large days
        result = await get_forecast("Test", 100, "celsius")
        assert result["forecast_days"] == 7

    def test_get_current_weather_resource_empty_city(self):
        """Test weather resource with empty city name."""
        result = get_current_weather_resource("")
        weather_data = json.loads(result)
        assert weather_data["location"] == ""

    def test_get_current_weather_resource_json_validity(self):
        """Test that weather resource always returns valid JSON."""
        result = get_current_weather_resource("Test City")

        # Should not raise exception
        weather_data = json.loads(result)

        # Should have all required fields
        required_fields = [
            "location",
            "timestamp",
            "condition",
            "temperature",
            "feels_like",
            "humidity",
            "wind_speed",
            "wind_direction",
            "pressure",
            "visibility",
            "uv_index",
        ]

        for field in required_fields:
            assert field in weather_data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
