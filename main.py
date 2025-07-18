import os
import requests
import asyncio
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes
import json
from datetime import datetime
import pytz

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
AQICN_API_KEY = os.getenv('AQICN_API_KEY')
OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')  # Add this for weather data

# Jakarta timezone
JAKARTA_TZ = pytz.timezone('Asia/Jakarta')

# API endpoints
JAKARTA_AQI_URL = f"https://api.waqi.info/feed/jakarta/?token={AQICN_API_KEY}"
JAKARTA_WEATHER_URL = f"https://api.openweathermap.org/data/2.5/weather?q=Jakarta,ID&appid={OPENWEATHER_API_KEY}&units=metric"

async def set_bot_commands(application):
    """Set the bot commands menu that appears when users type /"""
    commands = [
        BotCommand("start", "Welcome message and bot introduction"),
        BotCommand("weather", "Get Jakarta weather and air quality"),
        BotCommand("currentrain", "Get current real-time rainfall"),
        BotCommand("rain", "Get Jakarta rain forecast"),
        BotCommand("help", "Show help and usage instructions"),
        BotCommand("about", "About this bot and data sources"),
    ]
    
    try:
        await application.bot.set_my_commands(commands)
        print("Bot commands menu set successfully!")
    except Exception as e:
        print(f"Error setting bot commands: {e}")

def get_jakarta_time():
    """Get current time in Jakarta timezone"""
    utc_now = datetime.now(pytz.UTC)
    jakarta_time = utc_now.astimezone(JAKARTA_TZ)
    return jakarta_time

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
    
    # Get Jakarta time
    jakarta_time = get_jakarta_time()
    
    # AQI information
    jakarta_aqi = aqi_data.get('aqi', 'N/A')
    jakarta_level = get_aqi_level(jakarta_aqi) if jakarta_aqi != 'N/A' else 'N/A'
    
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
    
    # Additional weather details from AQICN if available
    additional_info = ""
    if 'iaqi' in aqi_data:
        iaqi = aqi_data['iaqi']
        if 'w' in iaqi:  # Wind from AQICN
            additional_info += f"💨 Wind (AQICN): {iaqi['w']['v']} m/s\n"
    
    # Format the message
    message = f"""
🌤️ **Jakarta Weather Report**
📅 {jakarta_time.strftime('%Y-%m-%d %H:%M')} WIB

{weather_emoji} **Current Weather**
🌡️ Temperature: {temp}°C (feels like {feels_like}°C)
💧 Humidity: {humidity}%
☁️ Conditions: {weather_desc}
{rain_info}

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

def format_current_rain_message(data):
    """Format current rainfall data into a detailed message"""
    if not data:
        return "❌ Sorry, I couldn't fetch the current rainfall data right now. Please try again later."
    
    weather_data = data['weather']
    jakarta_time = get_jakarta_time()
    
    # Current rain information
    current_rain = "No rain detected"
    rain_emoji = "☀️"
    rain_details = ""
    
    if 'rain' in weather_data:
        rain_emoji = "🌧️"
        current_rain = "Rain detected!"
        
        if '1h' in weather_data['rain']:
            rain_1h = weather_data['rain']['1h']
            rain_details += f"💧 Last 1 hour: {rain_1h} mm\n"
        
        if '3h' in weather_data['rain']:
            rain_3h = weather_data['rain']['3h']
            rain_details += f"💧 Last 3 hours: {rain_3h} mm\n"
    
    # Weather conditions
    weather_desc = weather_data['weather'][0]['description'].title()
    weather_main = weather_data['weather'][0]['main']
    
    # Rain intensity classification
    rain_intensity = ""
    if 'rain' in weather_data:
        rain_1h = weather_data['rain'].get('1h', 0)
        if rain_1h > 0:
            if rain_1h < 2.5:
                rain_intensity = "Light rain 🌦️"
            elif rain_1h < 10:
                rain_intensity = "Moderate rain 🌧️"
            elif rain_1h < 50:
                rain_intensity = "Heavy rain ⛈️"
            else:
                rain_intensity = "Violent rain 🌊"
    
    # Cloud coverage
    clouds = weather_data.get('clouds', {}).get('all', 0)
    
    # Visibility
    visibility = weather_data.get('visibility', 0) / 1000 if 'visibility' in weather_data else 'N/A'
    
    message = f"""
🌧️ **Jakarta Real-time Rainfall**
📅 {jakarta_time.strftime('%Y-%m-%d %H:%M')} WIB

{rain_emoji} **Current Status: {current_rain}**
☁️ Weather: {weather_desc}
{rain_details}
{f"⚡ Intensity: {rain_intensity}" if rain_intensity else ""}

📊 **Atmospheric Conditions:**
☁️ Cloud Cover: {clouds}%
👁️ Visibility: {visibility} km
🌡️ Temperature: {weather_data['main']['temp']}°C
💧 Humidity: {weather_data['main']['humidity']}%

💡 **Rain Scale:**
• 0-2.5 mm/h: Light rain 🌦️
• 2.5-10 mm/h: Moderate rain 🌧️
• 10-50 mm/h: Heavy rain ⛈️
• 50+ mm/h: Violent rain 🌊

🔄 Data updates every request
💡 Source: OpenWeather API
"""
    
    return message
    """Format rain forecast data into a readable message"""
    if not forecast_data:
        return "❌ Sorry, I couldn't fetch the rain forecast right now. Please try again later."
    
    # Get Jakarta time
    jakarta_time = get_jakarta_time()
    
    message = f"""
🌧️ **Jakarta Rain Forecast**
📅 {jakarta_time.strftime('%Y-%m-%d %H:%M')} WIB

"""
    
    rain_periods = []
    for item in forecast_data['list'][:8]:  # Next 24 hours (8 x 3-hour periods)
        # Convert UTC timestamp to Jakarta time
        dt_utc = datetime.fromtimestamp(item['dt'], tz=pytz.UTC)
        dt_jakarta = dt_utc.astimezone(JAKARTA_TZ)
        
        weather_desc = item['weather'][0]['description']
        
        rain_amount = 0
        if 'rain' in item:
            rain_amount = item['rain'].get('3h', 0)
        
        if 'rain' in weather_desc.lower() or rain_amount > 0:
            rain_periods.append({
                'time': dt_jakarta.strftime('%H:%M'),
                'date': dt_jakarta.strftime('%m-%d'),
                'description': weather_desc.title(),
                'amount': rain_amount
            })
    
    if rain_periods:
        message += "🌧️ **Expected Rain Periods:**\n"
        for period in rain_periods:
            message += f"• {period['date']} {period['time']} WIB: {period['description']}"
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
• Real-time rainfall detection
• Rain forecast for next 24 hours

**Quick Commands:**
• `/weather` - Get current weather & air quality
• `/currentrain` - Get real-time rainfall status
• `/rain` - Get rain forecast for next 24 hours
• `/help` - Detailed help information
• `/about` - About this bot

💡 **Tip:** Type `/` to see all available commands!

Ready to check the weather? Try `/weather` now!
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

async def current_rain(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send current rainfall information when /currentrain command is used."""
    await update.message.reply_text("🔄 Fetching current rainfall data...")
    
    data = fetch_weather_data()
    message = format_current_rain_message(data)
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message when /help command is used."""
    help_text = """
🌤️ **Jakarta Weather Bot Help**

**Available Commands:**
• `/start` - Welcome message and introduction
• `/weather` - Get current Jakarta weather & air quality
• `/currentrain` - Get real-time rainfall status & intensity
• `/rain` - Get Jakarta rain forecast (next 24 hours)
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
• 301+: Hazardous 🔴

**Data Updates:** Real-time data fetched on each request
**Timezone:** All times shown in WIB (Western Indonesian Time)

Need more help? Just ask! 😊
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send information about the bot."""
    about_text = """
🤖 **About Jakarta Weather Bot**

**Version:** 2.1
**Created:** 2025 by Gilson Chin

**Features:**
• Real-time Jakarta weather data
• Jakarta air quality index (AQI)
• Real-time rainfall detection & intensity
• Rain forecast for next 24 hours
• Easy-to-understand weather conditions
• Local Jakarta timezone (WIB)

**Data Sources:**
• OpenWeather API (Weather & Rain data)
• AQICN (World Air Quality Index Project)
• Updates every request with fresh data

**New Features:**
• Rain forecast with timing
• More detailed weather information
• Real-time rain detection
• Jakarta local time display (WIB)

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
    
    print("Starting Jakarta Weather Bot...")
    
    # Create the Application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()
    
    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("weather", weather))
    application.add_handler(CommandHandler("currentrain", current_rain))
    application.add_handler(CommandHandler("rain", rain_forecast))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("about", about_command))
    
    # Start the bot
    print("Bot is running with command menu enabled...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
