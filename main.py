import os
import requests
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import json
from datetime import datetime

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
AQICN_API_KEY = os.getenv('AQICN_API_KEY')

# AQICN API endpoints
JAKARTA_AQI_URL = f"https://api.waqi.info/feed/jakarta/?token={AQICN_API_KEY}"
SINGAPORE_AQI_URL = f"https://api.waqi.info/feed/singapore/?token={AQICN_API_KEY}"

# Jakarta area monitoring stations
JAKARTA_STATIONS = {
    'Central Jakarta': [
        f"https://api.waqi.info/feed/jakarta-central/?token={AQICN_API_KEY}",
        f"https://api.waqi.info/feed/jakarta-gambir/?token={AQICN_API_KEY}",
        f"https://api.waqi.info/feed/jakarta-menteng/?token={AQICN_API_KEY}"
    ],
    'North Jakarta': [
        f"https://api.waqi.info/feed/jakarta-north/?token={AQICN_API_KEY}",
        f"https://api.waqi.info/feed/jakarta-kelapa-gading/?token={AQICN_API_KEY}",
        f"https://api.waqi.info/feed/jakarta-ancol/?token={AQICN_API_KEY}"
    ],
    'South Jakarta': [
        f"https://api.waqi.info/feed/jakarta-south/?token={AQICN_API_KEY}",
        f"https://api.waqi.info/feed/jakarta-kebayoran/?token={AQICN_API_KEY}",
        f"https://api.waqi.info/feed/jakarta-senayan/?token={AQICN_API_KEY}"
    ],
    'East Jakarta': [
        f"https://api.waqi.info/feed/jakarta-east/?token={AQICN_API_KEY}",
        f"https://api.waqi.info/feed/jakarta-cakung/?token={AQICN_API_KEY}",
        f"https://api.waqi.info/feed/jakarta-duren-sawit/?token={AQICN_API_KEY}"
    ],
    'West Jakarta': [
        f"https://api.waqi.info/feed/jakarta-west/?token={AQICN_API_KEY}",
        f"https://api.waqi.info/feed/jakarta-grogol/?token={AQICN_API_KEY}",
        f"https://api.waqi.info/feed/jakarta-kebon-jeruk/?token={AQICN_API_KEY}"
    ]
}

def get_aqi_level(aqi_value):
    """Convert AQI number to descriptive level"""
    if aqi_value <= 50:
        return "Good 🟢"
    elif aqi_value <= 100:
        return "Moderate 🟡"
    elif aqi_value <= 150:
        return "Unhealthy for Sensitive Groups 🟠"
    elif aqi_value <= 200:
        return "Unhealthy 🔴"
    elif aqi_value <= 300:
        return "Very Unhealthy 🟣"
    else:
        return "Hazardous 🔴"

def get_aqi_emoji(aqi_value):
    """Get emoji for AQI value"""
    if aqi_value <= 50:
        return "🟢"
    elif aqi_value <= 100:
        return "🟡"
    elif aqi_value <= 150:
        return "🟠"
    elif aqi_value <= 200:
        return "🔴"
    elif aqi_value <= 300:
        return "🟣"
    else:
        return "⚫"

def fetch_station_data(url):
    """Fetch data from a single station"""
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        if data['status'] == 'ok':
            return data['data'].get('aqi', None)
    except:
        pass
    return None

def fetch_jakarta_area_data():
    """Fetch AQI data from all Jakarta areas"""
    area_data = {}
    
    for area, stations in JAKARTA_STATIONS.items():
        aqi_values = []
        for station_url in stations:
            aqi = fetch_station_data(station_url)
            if aqi and isinstance(aqi, (int, float)):
                aqi_values.append(aqi)
        
        if aqi_values:
            # Calculate average AQI for the area
            avg_aqi = sum(aqi_values) / len(aqi_values)
            area_data[area] = {
                'avg_aqi': round(avg_aqi),
                'stations_count': len(aqi_values),
                'values': aqi_values
            }
        else:
            area_data[area] = {
                'avg_aqi': None,
                'stations_count': 0,
                'values': []
            }
    
    return area_data

def fetch_weather_data():
    """Fetch weather and air quality data from AQICN"""
    try:
        # Get Jakarta data
        jakarta_response = requests.get(JAKARTA_AQI_URL, timeout=10)
        jakarta_data = jakarta_response.json()
        
        # Get Singapore data
        singapore_response = requests.get(SINGAPORE_AQI_URL, timeout=10)
        singapore_data = singapore_response.json()
        
        if jakarta_data['status'] != 'ok' or singapore_data['status'] != 'ok':
            return None
            
        return {
            'jakarta': jakarta_data['data'],
            'singapore': singapore_data['data']
        }
        
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

def format_jakarta_aqi_map(area_data):
    """Create a visual map of Jakarta AQI by area"""
    if not area_data:
        return "❌ Unable to fetch Jakarta area AQI data"
    
    # Get AQI values for positioning
    north_aqi = area_data.get('North Jakarta', {}).get('avg_aqi')
    central_aqi = area_data.get('Central Jakarta', {}).get('avg_aqi')
    south_aqi = area_data.get('South Jakarta', {}).get('avg_aqi')
    east_aqi = area_data.get('East Jakarta', {}).get('avg_aqi')
    west_aqi = area_data.get('West Jakarta', {}).get('avg_aqi')
    
    # Create visual map
    map_visual = f"""
🗺️ **Jakarta AQI Map**

```
        {get_aqi_emoji(north_aqi) if north_aqi else '⚪'} North Jakarta
        AQI: {north_aqi if north_aqi else 'N/A'}

{get_aqi_emoji(west_aqi) if west_aqi else '⚪'} West    🏛️ Central    {get_aqi_emoji(east_aqi) if east_aqi else '⚪'} East
AQI: {west_aqi if west_aqi else 'N/A'}   AQI: {central_aqi if central_aqi else 'N/A'}   AQI: {east_aqi if east_aqi else 'N/A'}

        {get_aqi_emoji(south_aqi) if south_aqi else '⚪'} South Jakarta
        AQI: {south_aqi if south_aqi else 'N/A'}
```

📊 **Detailed Area Breakdown:**
"""
    
    for area, data in area_data.items():
        if data['avg_aqi']:
            level = get_aqi_level(data['avg_aqi'])
            map_visual += f"• **{area}**: {data['avg_aqi']} - {level}\n"
            map_visual += f"  └ Based on {data['stations_count']} station(s)\n"
        else:
            map_visual += f"• **{area}**: No data available\n"
    
    return map_visual

def format_weather_message(data):
    """Format the weather data into a readable message"""
    if not data:
        return "❌ Sorry, I couldn't fetch the weather data right now. Please try again later."
    
    jakarta_data = data['jakarta']
    singapore_data = data['singapore']
    
    # Jakarta information
    jakarta_aqi = jakarta_data.get('aqi', 'N/A')
    jakarta_level = get_aqi_level(jakarta_aqi) if jakarta_aqi != 'N/A' else 'N/A'
    
    # Singapore information
    singapore_aqi = singapore_data.get('aqi', 'N/A')
    singapore_level = get_aqi_level(singapore_aqi) if singapore_aqi != 'N/A' else 'N/A'
    
    # Weather details for Jakarta
    weather_info = ""
    if 'iaqi' in jakarta_data:
        iaqi = jakarta_data['iaqi']
        if 't' in iaqi:  # Temperature
            weather_info += f"🌡️ Temperature: {iaqi['t']['v']}°C\n"
        if 'h' in iaqi:  # Humidity
            weather_info += f"💧 Humidity: {iaqi['h']['v']}%\n"
        if 'p' in iaqi:  # Pressure
            weather_info += f"🌊 Pressure: {iaqi['p']['v']} hPa\n"
        if 'w' in iaqi:  # Wind
            weather_info += f"💨 Wind: {iaqi['w']['v']} m/s\n"
    
    # Format the message
    message = f"""
🌤️ **Weather Report**
📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}

🏙️ **Jakarta Weather & Air Quality**
🌬️ AQI: {jakarta_aqi} - {jakarta_level}
{weather_info}

🇸🇬 **Singapore Air Quality (PSI)**
🌬️ AQI: {singapore_aqi} - {singapore_level}

📊 **AQI Scale:**
• 0-50: Good 🟢
• 51-100: Moderate 🟡
• 101-150: Unhealthy for Sensitive Groups 🟠
• 151-200: Unhealthy 🔴
• 201-300: Very Unhealthy 🟣
• 301+: Hazardous 🔴

💡 Data provided by AQICN
"""
    return message

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    welcome_message = """
🌤️ Welcome to Jakarta Weather Bot!

I can provide you with:
• Jakarta's current weather conditions
• Jakarta's air quality index (AQI)
• Jakarta AQI map by areas (North, South, East, West, Central)
• Singapore's PSI index for comparison

Commands:
/weather - Get current weather and air quality
/aqimap - Get Jakarta AQI map by areas
/help - Show this help message

Just type /weather or /aqimap to get started!
"""
    await update.message.reply_text(welcome_message)

async def weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send weather information when /weather command is used."""
    await update.message.reply_text("🔄 Fetching weather data...")
    
    data = fetch_weather_data()
    message = format_weather_message(data)
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def aqi_map(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send Jakarta AQI map when /aqimap command is used."""
    await update.message.reply_text("🔄 Fetching AQI data from all Jakarta areas...")
    
    area_data = fetch_jakarta_area_data()
    message = format_jakarta_aqi_map(area_data)
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message when /help command is used."""
    help_text = """
🌤️ **Jakarta Weather Bot Help**

**Commands:**
• `/start` - Welcome message
• `/weather` - Get current Jakarta weather & Singapore PSI
• `/aqimap` - Get Jakarta AQI map by areas
• `/help` - Show this help message

**About:**
This bot fetches real-time weather data for Jakarta and air quality information for both Jakarta and Singapore using the AQICN API. The AQI map shows air quality across different areas of Jakarta.

**Data Sources:**
• Weather data: AQICN (World Air Quality Index)
• Updates: Real-time data from multiple monitoring stations
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

def main():
    """Start the bot."""
    if not TELEGRAM_BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN environment variable not set")
        return
    
    if not AQICN_API_KEY:
        print("Error: AQICN_API_KEY environment variable not set")
        return
    
    print("Starting Jakarta Weather Bot...")
    
    # Create the Application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("weather", weather))
    application.add_handler(CommandHandler("aqimap", aqi_map))
    application.add_handler(CommandHandler("help", help_command))
    
    # Start the bot
    print("Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
