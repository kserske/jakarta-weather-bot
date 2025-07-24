import os
import requests
import asyncio
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes
import json
from datetime import datetime
import concurrent.futures
from typing import Dict, List, Optional

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
AQICN_API_KEY = os.getenv('AQICN_API_KEY')
OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')

# API endpoints
JAKARTA_AQI_URL = f"https://api.waqi.info/feed/jakarta/?token={AQICN_API_KEY}"
JAKARTA_WEATHER_URL = f"https://api.openweathermap.org/data/2.5/weather?q=Jakarta,ID&appid={OPENWEATHER_API_KEY}&units=metric"

# Jakarta area coordinates and monitoring stations
JAKARTA_AREAS = {
    'central': {
        'name': 'Central Jakarta',
        'emoji': '🏢',
        'stations': ['jakarta', 'jakarta-central', 'monas'],
        'coordinates': (-6.2088, 106.8456)  # Central Jakarta coordinates
    },
    'north': {
        'name': 'North Jakarta',
        'emoji': '🏭',
        'stations': ['jakarta-north', 'kelapa-gading', 'ancol'],
        'coordinates': (-6.1381, 106.8635)  # North Jakarta coordinates
    },
    'south': {
        'name': 'South Jakarta',
        'emoji': '🏘️',
        'stations': ['jakarta-south', 'kebayoran', 'pondok-indah'],
        'coordinates': (-6.2615, 106.8106)  # South Jakarta coordinates
    },
    'east': {
        'name': 'East Jakarta',
        'emoji': '🏗️',
        'stations': ['jakarta-east', 'cakung', 'jatinegara'],
        'coordinates': (-6.2250, 106.9004)  # East Jakarta coordinates
    },
    'west': {
        'name': 'West Jakarta',
        'emoji': '🏪',
        'stations': ['jakarta-west', 'grogol', 'kebon-jeruk'],
        'coordinates': (-6.1683, 106.7593)  # West Jakarta coordinates
    }
}

async def set_bot_commands(application):
    """Set the bot commands menu that appears when users type /"""
    commands = [
        BotCommand("start", "Welcome message and bot introduction"),
        BotCommand("weather", "Get Jakarta weather and air quality"),
        BotCommand("rain", "Get Jakarta rain forecast"),
        BotCommand("aqimap", "Get air quality map for all Jakarta areas"),
        BotCommand("help", "Show help and usage instructions"),
        BotCommand("about", "About this bot and data sources"),
    ]
    
    try:
        await application.bot.set_my_commands(commands)
        print("Bot commands menu set successfully!")
    except Exception as e:
        print(f"Error setting bot commands: {e}")

def get_aqi_level(aqi_value):
    """Convert AQI number to descriptive level with emoji"""
    try:
        aqi = int(aqi_value)
        if aqi <= 50:
            return "Good 🟢", "🟢"
        elif aqi <= 100:
            return "Moderate 🟡", "🟡"
        elif aqi <= 150:
            return "Unhealthy for Sensitive Groups 🟠", "🟠"
        elif aqi <= 200:
            return "Unhealthy 🔴", "🔴"
        elif aqi <= 300:
            return "Very Unhealthy 🟣", "🟣"
        else:
            return "Hazardous ⚫", "⚫"
    except (ValueError, TypeError):
        return "N/A ⚪", "⚪"

def get_weather_condition_emoji(condition):
    """Get emoji for weather condition"""
    condition_lower = condition.lower()
    if 'clear' in condition_lower:
        return '☀️'
    elif 'cloud' in condition_lower:
        return '☁️'
    elif 'rain' in condition_lower or 'drizzle' in condition_lower:
        return '🌧️'
    elif 'thunder' in condition_lower or 'storm' in condition_lower:
        return '⛈️'
    elif 'snow' in condition_lower:
        return '❄️'
    elif 'mist' in condition_lower or 'fog' in condition_lower:
        return '🌫️'
    else:
        return '🌤️'

def fetch_aqi_for_station(station: str) -> Optional[Dict]:
    """Fetch AQI data for a specific station"""
    try:
        url = f"https://api.waqi.info/feed/{station}/?token={AQICN_API_KEY}"
        response = requests.get(url, timeout=5)
        data = response.json()
        
        if data.get('status') == 'ok' and 'data' in data:
            return {
                'station': station,
                'aqi': data['data'].get('aqi', 'N/A'),
                'time': data['data'].get('time', {}).get('s', 'N/A')
            }
    except Exception as e:
        print(f"Error fetching AQI for {station}: {e}")
    
    return None

def fetch_aqi_by_coordinates(lat: float, lon: float) -> Optional[Dict]:
    """Fetch AQI data using coordinates as fallback"""
    try:
        url = f"https://api.waqi.info/feed/geo:{lat};{lon}/?token={AQICN_API_KEY}"
        response = requests.get(url, timeout=5)
        data = response.json()
        
        if data.get('status') == 'ok' and 'data' in data:
            return {
                'station': f"geo:{lat},{lon}",
                'aqi': data['data'].get('aqi', 'N/A'),
                'time': data['data'].get('time', {}).get('s', 'N/A')
            }
    except Exception as e:
        print(f"Error fetching AQI for coordinates {lat},{lon}: {e}")
    
    return None

def get_best_aqi_for_area(area_key: str, area_data: Dict) -> Dict:
    """Get the best available AQI data for an area"""
    area_info = {
        'name': area_data['name'],
        'emoji': area_data['emoji'],
        'aqi': 'N/A',
        'level': 'N/A ⚪',
        'color': '⚪',
        'source': 'No data available'
    }
    
    # Try to get data from predefined stations
    for station in area_data['stations']:
        aqi_data = fetch_aqi_for_station(station)
        if aqi_data and aqi_data['aqi'] != 'N/A':
            level, color = get_aqi_level(aqi_data['aqi'])
            area_info.update({
                'aqi': aqi_data['aqi'],
                'level': level,
                'color': color,
                'source': f"Station: {station}"
            })
            break
    
    # If no station data available, try coordinates
    if area_info['aqi'] == 'N/A':
        lat, lon = area_data['coordinates']
        coord_data = fetch_aqi_by_coordinates(lat, lon)
        if coord_data and coord_data['aqi'] != 'N/A':
            level, color = get_aqi_level(coord_data['aqi'])
            area_info.update({
                'aqi': coord_data['aqi'],
                'level': level,
                'color': color,
                'source': f"Coordinates: {lat}, {lon}"
            })
    
    return area_info

def fetch_jakarta_aqi_map() -> Dict:
    """Fetch AQI data for all Jakarta areas"""
    jakarta_map = {}
    
    # Use ThreadPoolExecutor for concurrent requests
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_area = {
            executor.submit(get_best_aqi_for_area, area_key, area_data): area_key
            for area_key, area_data in JAKARTA_AREAS.items()
        }
        
        for future in concurrent.futures.as_completed(future_to_area):
            area_key = future_to_area[future]
            try:
                result = future.result()
                jakarta_map[area_key] = result
            except Exception as e:
                print(f"Error processing {area_key}: {e}")
                # Provide fallback data
                jakarta_map[area_key] = {
                    'name': JAKARTA_AREAS[area_key]['name'],
                    'emoji': JAKARTA_AREAS[area_key]['emoji'],
                    'aqi': 'N/A',
                    'level': 'N/A ⚪',
                    'color': '⚪',
                    'source': 'Error fetching data'
                }
    
    return jakarta_map

def format_aqi_map_message(aqi_map: Dict) -> str:
    """Format the AQI map data into a readable message"""
    if not aqi_map:
        return "❌ Sorry, I couldn't fetch the air quality map right now. Please try again later."
    
    message = f"""
🗺️ **Jakarta Air Quality Map**
📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}

"""
    
    # Visual map representation
    message += "📍 **Air Quality by Area:**\n\n"
    
    # Create a visual map layout
    north = aqi_map.get('north', {})
    central = aqi_map.get('central', {})
    west = aqi_map.get('west', {})
    east = aqi_map.get('east', {})
    south = aqi_map.get('south', {})
    
    # Visual map layout
    message += f"""
```
      {north.get('color', '⚪')} North
         |
{west.get('color', '⚪')} West - {central.get('color', '⚪')} Central - {east.get('color', '⚪')} East
         |
      {south.get('color', '⚪')} South
```

"""
    
    # Detailed information for each area
    message += "📊 **Detailed Information:**\n\n"
    
    # Sort areas by AQI value (lowest first, N/A last)
    sorted_areas = []
    for area_key, area_data in aqi_map.items():
        aqi_value = area_data.get('aqi', 'N/A')
        sort_key = float('inf') if aqi_value == 'N/A' else int(aqi_value)
        sorted_areas.append((sort_key, area_key, area_data))
    
    sorted_areas.sort(key=lambda x: x[0])
    
    for _, area_key, area_data in sorted_areas:
        message += f"{area_data.get('emoji', '📍')} **{area_data.get('name', 'Unknown')}**\n"
        message += f"   AQI: {area_data.get('aqi', 'N/A')} - {area_data.get('level', 'N/A')}\n"
        message += f"   Source: {area_data.get('source', 'Unknown')}\n\n"
    
    # Add legend and recommendations
    message += """
📊 **AQI Scale:**
🟢 0-50: Good
🟡 51-100: Moderate
🟠 101-150: Unhealthy for Sensitive Groups
🔴 151-200: Unhealthy
🟣 201-300: Very Unhealthy
⚫ 301+: Hazardous
⚪ N/A: No data available

💡 **Tips:**
• Choose areas with lower AQI for outdoor activities
• Use masks in areas with AQI > 100
• Data refreshed on each request

📡 Data from AQICN (World Air Quality Index Project)
"""
    
    return message

def fetch_weather_data():
    """Fetch weather and air quality data"""
    try:
        # Get Jakarta AQI data
        jakarta_aqi_response = requests.get(JAKARTA_AQI_URL, timeout=10)
        jakarta_aqi_data = jakarta_aqi_response.json()
        
        # Get Jakarta weather data from OpenWeather
        jakarta_weather_response = requests.get(JAKARTA_WEATHER_URL, timeout=10)
        jakarta_weather_data = jakarta_weather_response.json()
        
        if jakarta_aqi_data['status'] != 'ok':
            return None
            
        return {
            'aqi': jakarta_aqi_data['data'],
            'weather': jakarta_weather_data
        }
        
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

def fetch_rain_forecast():
    """Fetch rain forecast data for Jakarta"""
    try:
        # Use OpenWeather 5-day forecast API
        forecast_url = f"https://api.openweathermap.org/data/2.5/forecast?q=Jakarta,ID&appid={OPENWEATHER_API_KEY}&units=metric"
        response = requests.get(forecast_url, timeout=10)
        forecast_data = response.json()
        
        if response.status_code == 200:
            return forecast_data
        else:
            return None
            
    except Exception as e:
        print(f"Error fetching rain forecast: {e}")
        return None

def format_weather_message(data):
    """Format the weather data into a readable message"""
    if not data:
        return "❌ Sorry, I couldn't fetch the weather data right now. Please try again later."
    
    aqi_data = data['aqi']
    weather_data = data['weather']
    
    # AQI information
    jakarta_aqi = aqi_data.get('aqi', 'N/A')
    jakarta_level = get_aqi_level(jakarta_aqi)[0] if jakarta_aqi != 'N/A' else 'N/A'
    
    # Weather information from OpenWeather
    temp = weather_data['main']['temp']
    feels_like = weather_data['main']['feels_like']
    humidity = weather_data['main']['humidity']
    pressure = weather_data['main']['pressure']
    weather_desc = weather_data['weather'][0]['description'].title()
    weather_emoji = get_weather_condition_emoji(weather_desc)
    wind_speed = weather_data['wind']['speed']
    
    # Rain information
    rain_info = ""
    if 'rain' in weather_data:
        if '1h' in weather_data['rain']:
            rain_info = f"🌧️ Rain (1h): {weather_data['rain']['1h']} mm\n"
        elif '3h' in weather_data['rain']:
            rain_info = f"🌧️ Rain (3h): {weather_data['rain']['3h']} mm\n"
    
    # Format the message
    message = f"""
🌤️ **Jakarta Weather Report**
📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}

{weather_emoji} **Current Weather**
🌡️ Temperature: {temp}°C (feels like {feels_like}°C)
💧 Humidity: {humidity}%
🌊 Pressure: {pressure} hPa
💨 Wind Speed: {wind_speed} m/s
☁️ Conditions: {weather_desc}
{rain_info}

🌬️ **Air Quality (General Jakarta)**
AQI: {jakarta_aqi} - {jakarta_level}

💡 **Tip:** Use `/aqimap` to see air quality in different Jakarta areas!

📊 **AQI Scale:**
• 0-50: Good 🟢 • 51-100: Moderate 🟡 • 101-150: Unhealthy for Sensitive Groups 🟠
• 151-200: Unhealthy 🔴 • 201-300: Very Unhealthy 🟣 • 301+: Hazardous ⚫

💡 Data from OpenWeather & AQICN
"""
    return message

def format_rain_forecast_message(forecast_data):
    """Format rain forecast data into a readable message"""
    if not forecast_data:
        return "❌ Sorry, I couldn't fetch the rain forecast right now. Please try again later."
    
    message = f"""
🌧️ **Jakarta Rain Forecast**
📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}

"""
    
    rain_periods = []
    for item in forecast_data['list'][:8]:  # Next 24 hours (8 x 3-hour periods)
        dt = datetime.fromtimestamp(item['dt'])
        weather_desc = item['weather'][0]['description']
        
        rain_amount = 0
        if 'rain' in item:
            rain_amount = item['rain'].get('3h', 0)
        
        if 'rain' in weather_desc.lower() or rain_amount > 0:
            rain_periods.append({
                'time': dt.strftime('%H:%M'),
                'date': dt.strftime('%m-%d'),
                'description': weather_desc.title(),
                'amount': rain_amount
            })
    
    if rain_periods:
        message += "🌧️ **Expected Rain Periods:**\n"
        for period in rain_periods:
            message += f"• {period['date']} {period['time']}: {period['description']}"
            if period['amount'] > 0:
                message += f" ({period['amount']} mm)"
            message += "\n"
    else:
        message += "☀️ **Good News!** No rain expected in the next 24 hours.\n"
    
    message += "\n💡 Data from OpenWeather"
    
    return message

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    welcome_message = """
🌤️ **Welcome to Jakarta Weather Bot!**

I can provide you with:
• Jakarta's current weather conditions
• Jakarta's air quality index (AQI)
• Real-time rain forecast for Jakarta
• **NEW:** Air quality map for all Jakarta areas!

**Quick Commands:**
• `/weather` - Get current weather & air quality
• `/rain` - Get rain forecast for next 24 hours
• `/aqimap` - Get air quality map for all Jakarta areas
• `/help` - Detailed help information
• `/about` - About this bot

💡 **Tip:** Type `/` to see all available commands!

🗺️ **New Feature:** Check air quality in North, South, East, West, and Central Jakarta with `/aqimap`!

Ready to check the weather? Try `/weather` or `/aqimap` now!
Created by Gilson Chin
"""
    await update.message.reply_text(welcome_message, parse_mode='Markdown')

async def weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send weather information when /weather command is used."""
    await update.message.reply_text("🔄 Fetching weather data...")
    
    data = fetch_weather_data()
    message = format_weather_message(data)
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def rain_forecast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send rain forecast when /rain command is used."""
    await update.message.reply_text("🔄 Fetching rain forecast...")
    
    forecast_data = fetch_rain_forecast()
    message = format_rain_forecast_message(forecast_data)
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def aqi_map(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send air quality map when /aqimap command is used."""
    await update.message.reply_text("🔄 Fetching air quality data for all Jakarta areas...")
    
    aqi_map_data = fetch_jakarta_aqi_map()
    message = format_aqi_map_message(aqi_map_data)
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message when /help command is used."""
    help_text = """
🌤️ **Jakarta Weather Bot Help**

**Available Commands:**
• `/start` - Welcome message and introduction
• `/weather` - Get current Jakarta weather & air quality
• `/rain` - Get Jakarta rain forecast (next 24 hours)
• `/aqimap` - Get air quality map for all Jakarta areas
• `/help` - Show this detailed help message
• `/about` - Information about this bot

**How to Use:**
1. Type `/` to see all available commands
2. Click on any command or type it manually
3. The bot will respond with the requested information

**Weather Information Includes:**
• 🌡️ Temperature & feels-like temperature
• 💧 Humidity
• 🌊 Atmospheric pressure
• 💨 Wind speed
• ☁️ Weather conditions
• 🌧️ Current rain data
• 🌬️ Air Quality Index (AQI)

**Air Quality Map Features:**
• 🗺️ Visual map of Jakarta areas
• 📊 AQI data for North, South, East, West, Central Jakarta
• 🔄 Multiple data sources for reliability
• 📍 Coordinate-based fallback data
• 🏆 Areas ranked by air quality

**Rain Forecast:**
• Next 24 hours rain prediction
• Rain intensity and timing
• Weather conditions during rain periods

**Air Quality Scale:**
• 0-50: Good 🟢
• 51-100: Moderate 🟡
• 101-150: Unhealthy for Sensitive Groups 🟠
• 151-200: Unhealthy 🔴
• 201-300: Very Unhealthy 🟣
• 301+: Hazardous ⚫

**Data Updates:** Real-time data fetched on each request

Need more help? Just ask! 😊
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send information about the bot."""
    about_text = """
🤖 **About Jakarta Weather Bot**

**Version:** 3.0
**Created:** 2025 by Gilson Chin

**Features:**
• Real-time Jakarta weather data
• Jakarta air quality index (AQI)
• Rain forecast for next 24 hours
• **NEW:** Air quality map for all Jakarta areas

**Air Quality Map:**
• Coverage: North, South, East, West, Central Jakarta
• Multiple monitoring stations per area
• Coordinate-based fallback data
• Visual map representation
• Error-resistant data fetching

**Data Sources:**
• OpenWeather API (Weather & Rain data)
• AQICN (World Air Quality Index Project)
• Multiple AQI monitoring stations
• Updates every request with fresh data

**Technical Features:**
• Concurrent API requests for faster response
• Robust error handling and fallback mechanisms
• Multiple data sources per Jakarta area
• Visual map representation with emojis

**Developer:** Built with Python & python-telegram-bot
**Hosting:** Railway Cloud Platform

**Privacy:** This bot doesn't store any personal data
"""
    await update.message.reply_text(about_text, parse_mode='Markdown')

async def post_init(application):
    """Initialize bot commands after the application starts."""
    await set_bot_commands(application)

def main():
    """Start the bot."""
    if not TELEGRAM_BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN environment variable not set")
        return
    
    if not AQICN_API_KEY:
        print("Error: AQICN_API_KEY environment variable not set")
        return
    
    if not OPENWEATHER_API_KEY:
        print("Error: OPENWEATHER_API_KEY environment variable not set")
        print("Please get a free API key from https://openweathermap.org/api")
        return
    
    print("Starting Jakarta Weather Bot with Air Quality Map...")
    
    # Create the Application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()
    
    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("weather", weather))
    application.add_handler(CommandHandler("rain", rain_forecast))
    application.add_handler(CommandHandler("aqimap", aqi_map))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("about", about_command))
    
    # Start the bot
    print("Bot is running with Air Quality Map feature enabled...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
