    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        if query.data == 'check_aqi':
            await query.edit_message_text("🔄 Fetching regional air quality data...")
            
            aqi_data = self.fetch_jakarta_aqi()
            sg_psi_data = self.fetch_singapore_psi()
            message = self.format_aqi_message(aqi_data, sg_psi_data)
            
            keyboard = [
                [InlineKeyboardButton("🔄 Refresh", callback_data='check_aqi')],
                [InlineKeyboardButton("📊 Detailed Jakarta", callback_data='detailed_aqi')],
                [InlineKeyboardButton("🇸🇬 Singapore Details", callback_data='sg_details')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        
        elif query.data == 'about_aqi':
            about_text = """
📊 **About Air Quality Indices**

**AQI vs PSI - What's the difference?**

Both indices measure air quality but use different scales:

🇮🇩 **AQI (Air Quality Index):**
Used by Jakarta and most countries worldwide
• More granular scale (6 categories)
• Includes "Unhealthy for Sensitive Groups"
• Range: 0-500+

🇸🇬 **PSI (Pollutant Standards Index):**
Used by Singapore and some Asian countries
• Simpler scale (5 categories)
• More conservative thresholds
• Range: 0-500+

**Health Impact Scale:**
🟢 **Good (0-50):** Minimal impact
🟡 **Moderate (51-100):** Acceptable
🟠 **Unhealthy (101-150/200):** Sensitive groups affected
🔴 **Very Unhealthy (151-200/201-300):** Everyone affected
⚫ **Hazardous (301+):** Emergency conditions

**Main Pollutants:**
• PM2.5: Fine particles (most dangerous)
• PM10: Coarse particles
• Ozone (O3): Ground-level ozone
• NO2: Traffic pollution
• SO2: Industrial pollution

Both systems update hourly from official monitoring stations.
            """
            
            keyboard = [
                [InlineKeyboardButton("🔙 Back to Menu", callback_data='back_to_menu')],
                [InlineKeyboardButton("🌍 Check Air Quality", callback_data='check_aqi')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(about_text, reply_markup=reply_markup, parse_mode='Markdown')
        
        elif query.data == 'sg_details':
            await query.edit_message_text("🔄 Fetching detailed Singapore PSI data...")
            
            sg_psi_data = self.fetch_singapore_psi()
            if sg_psi_data:
                detailed_message = "🇸🇬 **Detailed Singapore PSI Report**\n\n"
                
                readings = sg_psi_data.get('readings', {})
                timestamp = sg_psi_data.get('timestamp', 'N/A')
                
                detailed_message += f"⏰ **Last Updated:** {timestamp}\n\n"
                
                # 24-hour PSI readings
                psi_24h = readings.get('psi_twenty_four_hourly', {})
                if psi_24h:
                    detailed_message += "📊 **24-Hour PSI Readings:**\n"
                    detailed_message += f"🇸🇬 National: {psi_24h.get('national', 'N/A')}\n"
                    
                    regions = ['north', 'south', 'east', 'west', 'central']
                    for region in regions:
                        if region in psi_24h:
                            psi_val = psi_24h[region]
                            if psi_val != 'N/A':
                                level, _ = self.get_psi_level(int(psi_val))
                                detailed_message += f"📍 {region.title()}: {psi_val} ({level})\n"
                    
                    detailed_message += "\n"
                
                # PM2.5 readings
                pm25_24h = readings.get('pm25_twenty_four_hourly', {})
                if pm25_24h:
                    detailed_message += "🧪 **PM2.5 Concentrations (µg/m³):**\n"
                    detailed_message += f"🇸🇬 National: {pm25_24h.get('national', 'N/A')}\n"
                    
                    regions = ['north', 'south', 'east', 'west', 'central']
                    for region in regions:
                        if region in pm25_24h:
                            pm25_val = pm25_24h[region]
                            if pm25_val != 'N/A':
                                detailed_message += f"📍 {region.title()}: {pm25_val}\n"
                
                # Health advisory
                national_psi = psi_24h.get('national', 'N/A')
                if national_psi != 'N/A':
                    level, description = self.get_psi_level(int(national_psi))
                    detailed_message += f"\n🏥 **Health Advisory:**\n"
                    detailed_message += f"Status: {level}\n"
                    detailed_message += f"Recommendation: {description}\n"
                
            else:
                detailed_message = "❌ Unable to fetch detailed Singapore PSI data."
            
            keyboarimport requests
import json
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import asyncio
import os

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class JakartaAQIBot:
    def __init__(self, telegram_token, aqicn_token):
        self.telegram_token = telegram_token
        self.aqicn_token = aqicn_token
        self.base_url = "https://api.waqi.info"
        self.sg_psi_url = "https://api.data.gov.sg/v1/environment/psi"
        
    def get_psi_level(self, psi_value):
        """Convert PSI value to health level description (Singapore system)"""
        if psi_value <= 50:
            return "Good 🟢", "Normal activities"
        elif psi_value <= 100:
            return "Moderate 🟡", "Normal activities for most people"
        elif psi_value <= 200:
            return "Unhealthy 🟠", "Reduce prolonged outdoor activities"
        elif psi_value <= 300:
            return "Very Unhealthy 🔴", "Avoid prolonged outdoor activities"
        else:
            return "Hazardous ⚫", "Avoid outdoor activities"
    
    def get_aqi_level(self, aqi_value):
        """Convert AQI value to health level description"""
        if aqi_value <= 50:
            return "Good 🟢", "Air quality is considered satisfactory"
        elif aqi_value <= 100:
            return "Moderate 🟡", "Air quality is acceptable for most people"
        elif aqi_value <= 150:
            return "Unhealthy for Sensitive Groups 🟠", "Sensitive individuals may experience health issues"
        elif aqi_value <= 200:
            return "Unhealthy 🔴", "Everyone may experience health issues"
        elif aqi_value <= 300:
            return "Very Unhealthy 🟣", "Health warnings of emergency conditions"
        else:
            return "Hazardous ⚫", "Health alert: everyone may experience serious health effects"
    
    def fetch_singapore_psi(self):
        """Fetch Singapore PSI data from Singapore government API"""
        try:
            response = requests.get(self.sg_psi_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'items' in data and len(data['items']) > 0:
                    latest_data = data['items'][0]
                    return {
                        'timestamp': latest_data['timestamp'],
                        'readings': latest_data['readings']
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching Singapore PSI data: {str(e)}")
            return None
    
    def fetch_jakarta_aqi(self):
        """Fetch Jakarta air quality data from AQICN API"""
        try:
            # Try multiple Jakarta station IDs for better coverage
            stations = [
                "jakarta",
                "jakarta-selatan", 
                "jakarta-utara",
                "jakarta-barat",
                "jakarta-timur",
                "jakarta-pusat"
            ]
            
            results = []
            for station in stations:
                url = f"{self.base_url}/feed/{station}/?token={self.aqicn_token}"
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('status') == 'ok':
                        results.append({
                            'station': station,
                            'data': data['data']
                        })
            
            return results
            
        except Exception as e:
            logger.error(f"Error fetching AQI data: {str(e)}")
            return None
    
    def format_aqi_message(self, aqi_data, sg_psi_data):
        """Format AQI data and Singapore PSI into a readable message"""
        message = "🌍 **Regional Air Quality Report**\n"
        message += f"📅 Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        # Jakarta AQI Section
        message += "🇮🇩 **JAKARTA (AQI)**\n"
        message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        
        if not aqi_data:
            message += "❌ Unable to fetch Jakarta air quality data.\n\n"
        else:
            # Show average AQI for Jakarta
            valid_aqi = [int(d['data']['aqi']) for d in aqi_data if d['data'].get('aqi') != 'N/A']
            if valid_aqi:
                avg_aqi = sum(valid_aqi) / len(valid_aqi)
                level, description = self.get_aqi_level(int(avg_aqi))
                
                message += f"📊 **Average AQI: {int(avg_aqi)}**\n"
                message += f"🏥 Status: {level}\n"
                message += f"ℹ️ {description}\n\n"
                
                # Show top 2 stations
                for station_data in aqi_data[:2]:
                    station = station_data['station']
                    data = station_data['data']
                    
                    aqi_value = data.get('aqi', 'N/A')
                    if aqi_value != 'N/A':
                        level, _ = self.get_aqi_level(int(aqi_value))
                        message += f"📍 {station.title().replace('-', ' ')}: {aqi_value} {level.split()[0]}\n"
        
        # Singapore PSI Section
        message += "\n🇸🇬 **SINGAPORE (PSI)**\n"
        message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        
        if not sg_psi_data:
            message += "❌ Unable to fetch Singapore PSI data.\n\n"
        else:
            readings = sg_psi_data.get('readings', {})
            psi_24h = readings.get('psi_twenty_four_hourly', {})
            
            if psi_24h:
                # Get national average
                national_psi = psi_24h.get('national', 'N/A')
                if national_psi != 'N/A':
                    level, description = self.get_psi_level(int(national_psi))
                    message += f"📊 **National PSI: {national_psi}**\n"
                    message += f"🏥 Status: {level}\n"
                    message += f"ℹ️ {description}\n\n"
                
                # Show regional breakdown
                regions = ['north', 'south', 'east', 'west', 'central']
                for region in regions:
                    if region in psi_24h and psi_24h[region] != 'N/A':
                        psi_val = psi_24h[region]
                        level, _ = self.get_psi_level(int(psi_val))
                        message += f"📍 {region.title()}: {psi_val} {level.split()[0]}\n"
        
        # Comparison Section
        message += "\n📈 **COMPARISON**\n"
        message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        
        # Try to compare if both data are available
        if aqi_data and sg_psi_data:
            valid_aqi = [int(d['data']['aqi']) for d in aqi_data if d['data'].get('aqi') != 'N/A']
            readings = sg_psi_data.get('readings', {})
            psi_24h = readings.get('psi_twenty_four_hourly', {})
            national_psi = psi_24h.get('national', 'N/A')
            
            if valid_aqi and national_psi != 'N/A':
                avg_aqi = sum(valid_aqi) / len(valid_aqi)
                
                if avg_aqi < national_psi:
                    message += f"🟢 Jakarta air quality is currently better than Singapore\n"
                    message += f"   Jakarta AQI: {int(avg_aqi)} | Singapore PSI: {national_psi}\n"
                elif avg_aqi > national_psi:
                    message += f"🔴 Singapore air quality is currently better than Jakarta\n"
                    message += f"   Jakarta AQI: {int(avg_aqi)} | Singapore PSI: {national_psi}\n"
                else:
                    message += f"🟡 Both cities have similar air quality levels\n"
                    message += f"   Jakarta AQI: {int(avg_aqi)} | Singapore PSI: {national_psi}\n"
        
        # Health Recommendations
        message += "\n💡 **HEALTH RECOMMENDATIONS**\n"
        message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        
        # Base recommendations on Jakarta AQI (primary focus)
        if aqi_data:
            valid_aqi = [int(d['data']['aqi']) for d in aqi_data if d['data'].get('aqi') != 'N/A']
            if valid_aqi:
                avg_aqi = sum(valid_aqi) / len(valid_aqi)
                
                if avg_aqi <= 50:
                    message += "• Perfect for outdoor activities\n"
                    message += "• All age groups can enjoy outdoor exercise\n"
                elif avg_aqi <= 100:
                    message += "• Safe for most outdoor activities\n"
                    message += "• Sensitive individuals should monitor symptoms\n"
                elif avg_aqi <= 150:
                    message += "• Limit prolonged outdoor activities\n"
                    message += "• Sensitive groups should reduce outdoor exercise\n"
                elif avg_aqi <= 200:
                    message += "• Avoid outdoor activities\n"
                    message += "• Everyone should limit outdoor exposure\n"
                else:
                    message += "• Stay indoors, use air purifiers\n"
                    message += "• Wear N95 masks if going outside\n"
        
        message += "\n🔄 Data sources: AQICN.org (Jakarta) | Data.gov.sg (Singapore)"
        
        return message
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_message = """
🌟 **Welcome to Regional Air Quality Bot!**

This bot provides real-time air quality information for Jakarta (AQI) and Singapore (PSI) using official data sources.

**Available Commands:**
• /aqi - Get current air quality comparison
• /help - Show this help message
• /subscribe - Get notifications (coming soon)

**Features:**
✅ Real-time Jakarta AQI data
✅ Real-time Singapore PSI data
✅ Regional comparison
✅ Health recommendations
✅ Pollutant breakdown

Click the button below to check current air quality!
        """
        
        keyboard = [
            [InlineKeyboardButton("🌍 Check Air Quality", callback_data='check_aqi')],
            [InlineKeyboardButton("ℹ️ About AQI & PSI", callback_data='about_aqi')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def aqi_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /aqi command"""
        await update.message.reply_text("🔄 Fetching regional air quality data...")
        
        # Fetch both Jakarta AQI and Singapore PSI
        aqi_data = self.fetch_jakarta_aqi()
        sg_psi_data = self.fetch_singapore_psi()
        
        message = self.format_aqi_message(aqi_data, sg_psi_data)
        
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh", callback_data='check_aqi')],
            [InlineKeyboardButton("📊 Detailed Jakarta", callback_data='detailed_aqi')],
            [InlineKeyboardButton("🇸🇬 Singapore Details", callback_data='sg_details')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
🆘 **Regional Air Quality Bot Help**

**Commands:**
• `/start` - Welcome message and main menu
• `/air` - Get current air quality comparison
• `/help` - Show this help message

**Understanding AQI vs PSI:**

🇮🇩 **AQI (Air Quality Index) - Jakarta:**
• 0-50: Good 🟢
• 51-100: Moderate 🟡
• 101-150: Unhealthy for Sensitive Groups 🟠
• 151-200: Unhealthy 🔴
• 201-300: Very Unhealthy 🟣
• 301+: Hazardous ⚫

🇸🇬 **PSI (Pollutant Standards Index) - Singapore:**
• 0-50: Good 🟢
• 51-100: Moderate 🟡
• 101-200: Unhealthy 🟠
• 201-300: Very Unhealthy 🔴
• 301+: Hazardous ⚫

**Pollutants Monitored:**
• PM2.5 & PM10: Particulate matter
• NO2: Nitrogen dioxide
• O3: Ozone
• CO: Carbon monoxide
• SO2: Sulfur dioxide

**Data Sources:** 
• Jakarta: AQICN.org
• Singapore: Data.gov.sg

**Developer:** @your_username

For issues or suggestions, contact the developer.
        """
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        if query.data == 'check_aqi':
            await query.edit_message_text("🔄 Fetching Jakarta air quality data...")
            
            aqi_data = self.fetch_jakarta_aqi()
            message = self.format_aqi_message(aqi_data)
            
            keyboard = [
                [InlineKeyboardButton("🔄 Refresh", callback_data='check_aqi')],
                [InlineKeyboardButton("📊 Detailed View", callback_data='detailed_aqi')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        
        elif query.data == 'about_aqi':
            about_text = """
📊 **About Air Quality Index (AQI)**

AQI is a standardized way to communicate air quality to the public. It considers multiple pollutants and converts them into a single number.

**Health Impact Scale:**
🟢 **Good (0-50):** Minimal impact
🟡 **Moderate (51-100):** Acceptable
🟠 **Unhealthy for Sensitive (101-150):** Sensitive groups affected
🔴 **Unhealthy (151-200):** Everyone affected
🟣 **Very Unhealthy (201-300):** Health warnings
⚫ **Hazardous (301+):** Emergency conditions

**Main Pollutants:**
• PM2.5: Fine particles (most dangerous)
• PM10: Coarse particles
• Ozone (O3): Ground-level ozone
• NO2: Traffic pollution
• SO2: Industrial pollution

Data is updated hourly from official monitoring stations.
            """
            
            keyboard = [
                [InlineKeyboardButton("🔙 Back to Menu", callback_data='back_to_menu')],
                [InlineKeyboardButton("🌍 Check Air Quality", callback_data='check_aqi')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(about_text, reply_markup=reply_markup, parse_mode='Markdown')
        
        elif query.data == 'detailed_aqi':
            await query.edit_message_text("🔄 Fetching detailed air quality data...")
            
            aqi_data = self.fetch_jakarta_aqi()
            if aqi_data:
                detailed_message = "📊 **Detailed Jakarta Air Quality Report**\n\n"
                
                for station_data in aqi_data:
                    station = station_data['station']
                    data = station_data['data']
                    
                    detailed_message += f"📍 **{station.title().replace('-', ' ')}**\n"
                    detailed_message += f"🔢 AQI: {data.get('aqi', 'N/A')}\n"
                    
                    if 'iaqi' in data:
                        detailed_message += "🧪 **Pollutant Details:**\n"
                        for pollutant, value in data['iaqi'].items():
                            if pollutant in ['pm25', 'pm10', 'no2', 'o3', 'co', 'so2']:
                                detailed_message += f"  • {pollutant.upper()}: {value['v']}\n"
                    
                    if 'time' in data:
                        detailed_message += f"⏰ Last Updated: {data['time']['s']}\n"
                    
                    detailed_message += "\n"
            else:
                detailed_message = "❌ Unable to fetch detailed data."
            
            keyboard = [
                [InlineKeyboardButton("🔄 Refresh", callback_data='detailed_aqi')],
                [InlineKeyboardButton("🔙 Back", callback_data='check_aqi')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(detailed_message, reply_markup=reply_markup, parse_mode='Markdown')
    
    def run(self):
        """Run the bot"""
        application = Application.builder().token(self.telegram_token).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("aqi", self.aqi_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Start the bot
        print("🤖 Jakarta Air Quality Bot starting...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    # Configuration
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
    AQICN_API_TOKEN = os.getenv("AQICN_API_TOKEN", "YOUR_AQICN_API_TOKEN")
    
    # Validate tokens
    if TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
        print("❌ Please set your Telegram bot token!")
        print("1. Message @BotFather on Telegram")
        print("2. Create a new bot with /newbot")
        print("3. Set TELEGRAM_BOT_TOKEN environment variable")
        exit(1)
    
    if AQICN_API_TOKEN == "YOUR_AQICN_API_TOKEN":
        print("❌ Please set your AQICN API token!")
        print("1. Visit https://aqicn.org/data-platform/token/")
        print("2. Request a free API token")
        print("3. Set AQICN_API_TOKEN environment variable")
        exit(1)
    
    # Create and run bot
    bot = JakartaAQIBot(TELEGRAM_BOT_TOKEN, AQICN_API_TOKEN)
    bot.run()