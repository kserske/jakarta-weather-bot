import os
import requests
import asyncio
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes
import json
from datetime import datetime

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
AQICN_API_KEY = os.getenv('AQICN_API_KEY')

# AQICN API endpoints
JAKARTA_AQI_URL = f"https://api.waqi.info/feed/jakarta/?token={AQICN_API_KEY}"
SINGAPORE_AQI_URL = f"https://api.waqi.info/feed/singapore/?token={AQICN_API_KEY}"

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

async def set_bot_commands(application):
    """Set the bot commands menu that appears when users type /"""
    commands = [
        BotCommand("start", "Welcome message and bot introduction"),
        BotCommand("weather", "Get Jakarta weather and Singapore PSI"),
        BotCommand("help", "Show help and usage instructions"),
        BotCommand("about", "About this bot and data sources"),
    ]
    
    await application.bot.set_my_commands(commands)
    print("Bot commands menu set successfully!")
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
🌬️ PSI: {singapore_aqi} - {singapore_level}

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
🌤️ **Welcome to Jakarta Weather Bot!**

I can provide you with:
• Jakarta's current weather conditions
• Jakarta's air quality index (AQI)
• Singapore's PSI index for comparison

**Quick Commands:**
• `/weather` - Get current weather & air quality
• `/help` - Detailed help information
• `/about` - About this bot

💡 **Tip:** Type `/` to see all available commands!

Ready to check the weather? Try `/weather` now!
"""
    await update.message.reply_text(welcome_message, parse_mode='Markdown')

async def weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send weather information when /weather command is used."""
    await update.message.reply_text("🔄 Fetching weather data...")
    
    data = fetch_weather_data()
    message = format_weather_message(data)
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message when /help command is used."""
    help_text = """
🌤️ **Jakarta Weather Bot Help**

**Available Commands:**
• `/start` - Welcome message and introduction
• `/weather` - Get current Jakarta weather & Singapore PSI
• `/help` - Show this detailed help message
• `/about` - Information about this bot

**How to Use:**
1. Type `/` to see all available commands
2. Click on any command or type it manually
3. The bot will respond with the requested information

**Weather Information Includes:**
• 🌡️ Temperature
• 💧 Humidity
• 🌊 Atmospheric pressure
• 💨 Wind speed
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
    about_text = """
🤖 **About Jakarta Weather Bot**

**Version:** 1.0
**Created:** 2025

**Features:**
• Real-time Jakarta weather data
• Jakarta air quality index (AQI)
• Singapore PSI index comparison
• Easy-to-understand air quality levels

**Data Sources:**
• AQICN (World Air Quality Index Project)
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
    
    print("Starting Jakarta Weather Bot...")
    
    # Create the Application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()
    
    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("weather", weather))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("about", about_command))
    
    # Start the bot
    print("Bot is running with command menu enabled...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
