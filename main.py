import os
import requests
import asyncio
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes
import json
from datetime import datetime

# Debug: Print all environment variables
print("=== DEBUGGING ENVIRONMENT VARIABLES ===")
print(f"TELEGRAM_BOT_TOKEN exists: {bool(os.getenv('TELEGRAM_BOT_TOKEN'))}")
print(f"AQICN_API_KEY exists: {bool(os.getenv('AQICN_API_KEY'))}")
print(f"OPENWEATHER_API_KEY exists: {bool(os.getenv('OPENWEATHER_API_KEY'))}")
print(f"OPENWEATHER_API_KEY value: {os.getenv('OPENWEATHER_API_KEY', 'NOT_SET')}")

# List all environment variables that contain 'WEATHER' or 'OPEN'
print("\n=== ALL ENV VARS CONTAINING 'WEATHER' OR 'OPEN' ===")
for key, value in os.environ.items():
    if 'WEATHER' in key.upper() or 'OPEN' in key.upper():
        print(f"{key}: {value[:20]}..." if len(value) > 20 else f"{key}: {value}")

print("=== END DEBUG INFO ===\n")

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
AQICN_API_KEY = os.getenv('AQICN_API_KEY')
OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')

# API endpoints
JAKARTA_AQI_URL = f"https://api.waqi.info/feed/jakarta/?token={AQICN_API_KEY}"
JAKARTA_WEATHER_URL = f"https://api.openweathermap.org/data/2.5/weather?q=Jakarta,ID&appid={OPENWEATHER_API_KEY}&units=metric" if OPENWEATHER_API_KEY else None

async def set_bot_commands(application):
    """Set the bot commands menu that appears when users type /"""
    commands = [
        BotCommand("start", "Welcome message and bot introduction"),
        BotCommand("weather", "Get Jakarta weather and air quality"),
        BotCommand("help", "Show help and usage instructions"),
        BotCommand("about", "About this bot and data sources"),
    ]
    
    # Only add rain command if OpenWeather is available
    if OPENWEATHER_API_KEY:
        commands.insert(2, BotCommand("rain", "Get Jakarta rain forecast"))
    
    try:
        await application.bot.set_my_commands(commands)
        print("Bot commands menu set successfully!")
    except Exception as e:
        print(f"Error setting bot commands: {e}")

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

def fetch_weather_data():
    """Fetch weather and air quality data"""
    try:
        # Get Jakarta AQI data
        jakarta_aqi_response = requests.get(JAKARTA_AQI_URL, timeout=10)
        jakarta_aqi_data = jakarta_aqi_response.json()
        
        result = {
            'aqi': jakarta_aqi_data['data'] if jakarta_aqi_data['status'] == 'ok' else None,
            'weather': None
        }
        
        # Get Jakarta weather data from OpenWeather (if available)
        if OPENWEATHER_API_KEY and JAKARTA_WEATHER_URL:
            jakarta_weather_response = requests.get(JAKARTA_WEATHER_URL, timeout=10)
            if jakarta_weather_response.status_code == 200:
                result['weather'] = jakarta_weather_response.json()
        
        return result
        
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

def fetch_rain_forecast():
    """Fetch rain forecast data for Jakarta"""
    if not OPENWEATHER_API_KEY:
        return None
        
    try:
        # Use OpenWeather 5-day forecast API
        forecast_url = f"https://api.openweathermap.org/data/2.5/forecast?q=Jakarta,ID&appid={OPENWEATHER_API_KEY}&units=metric"
        response = requests.get(forecast_url, timeout=10)
        
        if response.status_code == 200:
            return response.json()
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
    jakarta_aqi = aqi_data.get('aqi', 'N/A') if aqi_data else 'N/A'
    jakarta_level = get_aqi_level(jakarta_aqi) if jakarta_aqi != 'N/A' else 'N/A'
    
    # Weather information from OpenWeather (if available)
    weather_section = ""
    if weather_data:
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
        
        weather_section = f"""
{weather_emoji} **Current Weather**
🌡️ Temperature: {temp}°C (feels like {feels_like}°C)
💧 Humidity: {humidity}%
🌊 Pressure: {pressure} hPa
💨 Wind Speed: {wind_speed} m/s
☁️ Conditions: {weather_desc}
{rain_info}
"""
    else:
        weather_section = """
⚠️ **Weather Data Unavailable**
OpenWeather API not configured or temporarily unavailable.
"""
    
    # Additional weather details from AQICN if available
    additional_info = ""
    if aqi_data and 'iaqi' in aqi_data:
        iaqi = aqi_data['iaqi']
        if 't' in iaqi:  # Temperature
            additional_info += f"🌡️ Temperature (AQICN): {iaqi['t']['v']}°C\n"
        if 'h' in iaqi:  # Humidity
            additional_info += f"💧 Humidity (AQICN): {iaqi['h']['v']}%\n"
        if 'p' in iaqi:  # Pressure
            additional_info += f"🌊 Pressure (AQICN): {iaqi['p']['v']} hPa\n"
        if 'w' in iaqi:  # Wind
            additional_info += f"💨 Wind (AQICN): {iaqi['w']['v']} m/s\n"
    
    # Format the message
    message = f"""
🌤️ **Jakarta Weather Report**
📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}
{weather_section}
{additional_info}
🌬️ **Air Quality**
AQI: {jakarta_aqi} - {jakarta_level}

📊 **AQI Scale:**
• 0-50: Good 🟢
• 51-100: Moderate 🟡
• 101-150: Unhealthy for Sensitive Groups 🟠
• 151-200: Unhealthy 🔴
• 201-300: Very Unhealthy 🟣
• 301+: Hazardous 🔴

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
    openweather_status = "✅ Available" if OPENWEATHER_API_KEY else "❌ Not configured"
    
    welcome_message = f"""
🌤️ **Welcome to Jakarta Weather Bot!**

I can provide you with:
• Jakarta's current weather conditions
• Jakarta's air quality index (AQI)
• Real-time rain forecast for Jakarta {openweather_status}

**Quick Commands:**
• `/weather` - Get current weather & air quality
• `/help` - Detailed help information
• `/about` - About this bot

💡 **Tip:** Type `/` to see all available commands!

Ready to check the weather? Try `/weather` now!
Created by Gilson Chin
"""
    
    if OPENWEATHER_API_KEY:
        welcome_message = welcome_message.replace("💡 **Tip:**", "• `/rain` - Get rain forecast for next 24 hours\n\n💡 **Tip:**")
    
    await update.message.reply_text(welcome_message, parse_mode='Markdown')

async def weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send weather information when /weather command is used."""
    await update.message.reply_text("🔄 Fetching weather data...")
    
    data = fetch_weather_data()
    message = format_weather_message(data)
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def rain_forecast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send rain forecast when /rain command is used."""
    if not OPENWEATHER_API_KEY:
        await update.message.reply_text("❌ Rain forecast is not available. OpenWeather API key is not configured.")
        return
        
    await update.message.reply_text("🔄 Fetching rain forecast...")
    
    forecast_data = fetch_rain_forecast()
    message = format_rain_forecast_message(forecast_data)
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message when /help command is used."""
    rain_help = ""
    if OPENWEATHER_API_KEY:
        rain_help = """• `/rain` - Get Jakarta rain forecast (next 24 hours)
"""
    
    help_text = f"""
🌤️ **Jakarta Weather Bot Help**

**Available Commands:**
• `/start` - Welcome message and introduction
• `/weather` - Get current Jakarta weather & air quality
{rain_help}• `/help` - Show this detailed help message
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
• 🌧️ Current rain data (if available)
• 🌬️ Air Quality Index (AQI)

**Air Quality Scale:**
• 0-50: Good 🟢
• 51-100: Moderate 🟡
• 101-150: Unhealthy for Sensitive Groups 🟠
• 151-200: Unhealthy 🔴
• 201-300: Very Unhealthy 🟣
• 301+: Hazardous 🔴

**Data Updates:** Real-time data fetched on each request

Need more help? Just ask! 😊
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send information about the bot."""
    openweather_status = "✅ Active" if OPENWEATHER_API_KEY else "❌ Not configured"
    
    about_text = f"""
🤖 **About Jakarta Weather Bot**

**Version:** 2.0
**Created:** 2025 by Gilson Chin

**Features:**
• Real-time Jakarta weather data
• Jakarta air quality index (AQI)
• Rain forecast for next 24 hours {openweather_status}
• Easy-to-understand weather conditions

**Data Sources:**
• OpenWeather API {openweather_status}
• AQICN (World Air Quality Index Project) ✅
• Updates every request with fresh data

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
    
    # Make OpenWeather optional - bot will still work without it
    if not OPENWEATHER_API_KEY:
        print("Warning: OPENWEATHER_API_KEY environment variable not set")
        print("Bot will run with limited functionality (AQI only)")
    else:
        print("OpenWeather API key found - full functionality enabled")
    
    print("Starting Jakarta Weather Bot...")
    
    # Create the Application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()
    
    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("weather", weather))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("about", about_command))
    
    # Only add rain command if OpenWeather is available
    if OPENWEATHER_API_KEY:
        application.add_handler(CommandHandler("rain", rain_forecast))
    
    # Start the bot
    print("Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
