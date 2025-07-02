require('dotenv').config();
const TelegramBot = require('node-telegram-bot-api');
const axios = require('axios');

// Bot token from BotFather
const token = process.env.TELEGRAM_BOT_TOKEN;
const weatherApiKey = process.env.OPENWEATHER_API_KEY;

// Create bot instance
const bot = new TelegramBot(token, { polling: true });

// Jakarta coordinates
const JAKARTA_LAT = -6.2088;
const JAKARTA_LON = 106.8456;

// Convert PM2.5 to approximate PSI
const calculatePSI = (pm25) => {
  if (pm25 <= 12) return Math.round(pm25 * 4.17); // 0-50 PSI
  if (pm25 <= 35.4) return Math.round(50 + (pm25 - 12) * 2.13); // 51-100 PSI
  if (pm25 <= 55.4) return Math.round(100 + (pm25 - 35.4) * 5); // 101-200 PSI
  if (pm25 <= 150.4) return Math.round(200 + (pm25 - 55.4) * 1.05); // 201-300 PSI
  return Math.min(500, Math.round(300 + (pm25 - 150.4) * 1.33)); // 301+ PSI
};

// Get PSI status with emoji and text
const getPSIStatus = (psi) => {
  if (psi <= 50) return { emoji: "🟢", text: "Good", color: "Good" };
  if (psi <= 100) return { emoji: "🟡", text: "Moderate", color: "Moderate" };
  if (psi <= 200) return { emoji: "🔴", text: "Unhealthy", color: "Unhealthy" };
  if (psi <= 300) return { emoji: "🟣", text: "Very Unhealthy", color: "Very Unhealthy" };
  return { emoji: "🔴", text: "Hazardous", color: "Hazardous" };
};

// Get OpenWeather AQI description (keeping for reference)
const getAQIDescription = (aqi) => {
  switch(aqi) {
    case 1: return "Good 😊)";
    case 2: return "Fair 😐";
    case 3: return "Moderate 😷";
    case 4: return "Poor 😰";
    case 5: return "Very Poor 💀";
    default: return "Unknown";
  }
};

// Healthy reference levels (WHO guidelines)
const getHealthyLevels = () => {
  return `
📊 **WHO Healthy Guidelines:**
• PM2.5: ≤ 5 μg/m³ (annual) / ≤ 15 μg/m³ (24hr)
• PM10: ≤ 15 μg/m³ (annual) / ≤ 45 μg/m³ (24hr)
• NO₂: ≤ 10 μg/m³ (annual) / ≤ 25 μg/m³ (24hr)
• O₃: ≤ 60 μg/m³ (8hr average)

🇸🇬 **Singapore PSI Scale:**
• 0-50: Good 🟢
• 51-100: Moderate 🟡
• 101-200: Unhealthy 🔴
• 201-300: Very Unhealthy 🟣
• 301+: Hazardous 🔴
  `;
};

// Function to get air quality data
async function getJakartaAirQuality() {
  try {
    const response = await axios.get(
      `http://api.openweathermap.org/data/2.5/air_pollution?lat=${JAKARTA_LAT}&lon=${JAKARTA_LON}&appid=${weatherApiKey}`
    );
    
    const data = response.data;
    const aqi = data.list[0].main.aqi;
    const components = data.list[0].components;
    
    return {
      aqi: aqi,
      description: getAQIDescription(aqi),
      co: components.co,
      no: components.no,
      no2: components.no2,
      o3: components.o3,
      so2: components.so2,
      pm2_5: components.pm2_5,
      pm10: components.pm10,
      nh3: components.nh3
    };
  } catch (error) {
    console.error('Error fetching air quality:', error);
    throw new Error('Failed to fetch air quality data');
  }
}

// Start command
bot.onText(/\/start/, (msg) => {
  const chatId = msg.chat.id;
  const welcomeMessage = `
🌬️ Welcome to Jakarta Air Quality Bot! 

I can provide you with real-time air quality information for Jakarta.

Commands:
/air - Get current air quality
/help - Show this help message

Just type /air to get started!
  `;
  bot.sendMessage(chatId, welcomeMessage);
});

// Help command
bot.onText(/\/help/, (msg) => {
  const chatId = msg.chat.id;
  const helpMessage = `
🆘 Help - Jakarta Air Quality Bot

Commands:
/air - Get current air quality for Jakarta
/healthy - Show healthy air quality guidelines
/start - Show welcome message
/help - Show this help message

The bot provides:
• PSI (Pollutant Standards Index) based on PM2.5
• PM2.5 and PM10 levels with health indicators
• WHO healthy guidelines for comparison
• Other pollutant measurements

AQI Scale:
1 - Good 😊 (PSI: 0-50)
2 - Fair 😐 (PSI: 51-100)
3 - Moderate 😷 (PSI: 101-200)
4 - Poor 😰 (PSI: 201-300)
5 - Very Poor 💀 (PSI: 301+)

PSI Scale:
🟢 0-50: Good
🟡 51-100: Moderate
🔴 101-200: Unhealthy
🟣 201-300: Very Unhealthy
🔴 301+: Hazardous

Health Indicators:
✅ Good (within WHO guidelines)
⚠️ Moderate (above guidelines)
🔴 Unhealthy (significantly above)
🚨 Very Unhealthy (dangerous levels)
  `;
  bot.sendMessage(chatId, helpMessage);
});

// Healthy levels command
bot.onText(/\/healthy/, (msg) => {
  const chatId = msg.chat.id;
  const healthyMessage = `
🏥 **Healthy Air Quality Guidelines**

${getHealthyLevels()}

🔍 **What These Numbers Mean:**
• **PM2.5/PM10**: Tiny particles that get into your lungs
• **NO₂**: Nitrogen dioxide from cars and factories  
• **O₃**: Ground-level ozone (smog)
• **SO₂**: Sulfur dioxide from burning fuel

⚠️ **Important Notes:**
• WHO guidelines are for long-term health
• Short-term exposure above limits may be okay
• Sensitive people (children, elderly, asthma) should be more careful
• Singapore's PSI is commonly used in Southeast Asia

💡 **Quick Reference:**
If PM2.5 is under 15 μg/m³, air quality is generally acceptable for daily activities!
  `;
  bot.sendMessage(chatId, healthyMessage, { parse_mode: 'Markdown' });
});

// Air quality command - MAIN CHANGE HERE
bot.onText(/\/air/, async (msg) => {
  const chatId = msg.chat.id;
  
  try {
    // Send "loading" message
    const loadingMsg = await bot.sendMessage(chatId, "🔄 Fetching Jakarta air quality data...");
    
    const airQuality = await getJakartaAirQuality();
    const calculatedPSI = calculatePSI(airQuality.pm2_5);
    const psiStatus = getPSIStatus(calculatedPSI);
    
    // NEW CLEANER FORMAT
    const message = `
🌫️ **Jakarta Air Quality Report**
📊 **Overall AQI**: ${airQuality.aqi}/5 - ${airQuality.description}
PSI: ${calculatedPSI} ${psiStatus.emoji} ${psiStatus.text}

🔍 **Current Levels:**
• PM2.5: ${airQuality.pm2_5} μg/m³ ${getPollutantStatus(airQuality.pm2_5, 'pm25')}
• PM10: ${airQuality.pm10} μg/m³ ${getPollutantStatus(airQuality.pm10, 'pm10')}
• NO₂: ${airQuality.no2} μg/m³ ${getPollutantStatus(airQuality.no2, 'no2')}
• O₃: ${airQuality.o3} μg/m³ ${getPollutantStatus(airQuality.o3, 'o3')}

📅 Updated: ${new Date().toLocaleString('en-US', { timeZone: 'Asia/Jakarta' })} WIB

💡 **Health Advice:**
${getHealthAdvice(calculatedPSI)}

📊 *Data source: OpenWeather*
    `;
    
    // Delete loading message and send result
    await bot.deleteMessage(chatId, loadingMsg.message_id);
    bot.sendMessage(chatId, message, { parse_mode: 'Markdown' });
    
  } catch (error) {
    bot.sendMessage(chatId, "❌ Sorry, I couldn't fetch the air quality data right now. Please try again later.");
    console.error('Air quality command error:', error);
  }
});

// Function to check if pollutant levels are healthy
function getPollutantStatus(value, type) {
  const thresholds = {
    pm25: { good: 5, moderate: 15, unhealthy: 25 },
    pm10: { good: 15, moderate: 45, unhealthy: 75 },
    no2: { good: 10, moderate: 25, unhealthy: 40 },
    o3: { good: 60, moderate: 100, unhealthy: 140 }
  };
  
  if (!thresholds[type]) return '';
  
  const t = thresholds[type];
  if (value <= t.good) return '✅';
  if (value <= t.moderate) return '⚠️';
  if (value <= t.unhealthy) return '🔴';
  return '🚨';
}

// Function to provide health advice based on PSI (not AQI)
function getHealthAdvice(psi) {
  if (psi <= 50) {
    return "Perfect for outdoor activities! 🌟";
  } else if (psi <= 100) {
    return "Good air quality. Enjoy outdoor activities! 👍";
  } else if (psi <= 200) {
    return "Sensitive individuals should limit prolonged outdoor activities. 😷";
  } else if (psi <= 300) {
    return "Everyone should limit outdoor activities. Wear a mask if going out. 😰";
  } else {
    return "Avoid outdoor activities. Stay indoors and use air purifiers if available. 🏠";
  }
}

// Handle any text message (fallback)
bot.on('message', (msg) => {
  const chatId = msg.chat.id;
  const text = msg.text;
  
  // If message doesn't start with /, provide helpful response
  if (!text.startsWith('/')) {
    bot.sendMessage(chatId, "👋 Hi! Use /air to check Jakarta's air quality or /help for more commands.");
  }
});

// Error handling
bot.on('error', (error) => {
  console.error('Bot error:', error);
});

console.log('🤖 Jakarta Air Quality Bot is running...');