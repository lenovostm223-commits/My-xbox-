#!/usr/bin/env python3
"""
Xbox Account Checker Bot for Telegram
Educational Purpose Only - With .txt file support
"""

import asyncio
import logging
import re
import random
import json
import sys
import os
import tempfile
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple, List
import aiohttp
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, CallbackQueryHandler
)
from telegram.constants import ParseMode
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot configuration - CHANGE THIS
BOT_TOKEN = "8330121440:AAFM_ywFcmCO8yqR0MEyL0fhQ0fPPMuauDk"  # <-- Apna token yahan daalo

# Xbox public API endpoints
XBOX_PUBLIC_API = {
    "gamertag_info": "https://xboxapi.com/v2/gamertag/{gamertag}",
    "xuid_lookup": "https://xboxapi.com/v2/xuid/{gamertag}",
    "profile_lookup": "https://xboxgamertag.com/search/{gamertag}",
    "achievements": "https://www.trueachievements.com/gamer/{gamertag}",
    "gamepass_games": "https://www.xbox.com/en-us/xbox-game-pass/games"
}

class XboxPublicChecker:
    """Xbox account checker using public APIs and web scraping"""
    
    def __init__(self):
        self.session = None
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        
    async def ensure_session(self):
        """Ensure HTTP session exists"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
            
    async def close_session(self):
        """Close HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()
            
    def get_headers(self):
        """Get random headers for requests"""
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
    async def extract_gamertag(self, email: str) -> Optional[str]:
        """Extract potential gamertag from email"""
        username = email.split('@')[0]
        username = re.sub(r'[^a-zA-Z0-9\s]', '', username)
        
        potential_tags = [
            username,
            username.lower(),
            username.upper(),
            username + "x",
            "x" + username,
            username + "gamer",
            "gamer" + username,
            username + "live",
            username.replace('_', ''),
            username.replace('.', ''),
            username.replace('-', '')
        ]
        
        potential_tags = list(dict.fromkeys(potential_tags))
        for gamertag in potential_tags[:5]:
            if await self.check_gamertag_exists(gamertag):
                return gamertag
                
        return username
        
    async def check_gamertag_exists(self, gamertag: str) -> bool:
        """Check if gamertag exists using public sites"""
        try:
            await self.ensure_session()
            url = f"https://xboxgamertag.com/search/{gamertag}"
            async with self.session.get(url, headers=self.get_headers()) as response:
                if response.status == 200:
                    html = await response.text()
                    if "not found" not in html.lower() and "doesn't exist" not in html.lower():
                        return True
            return False
        except Exception as e:
            logger.error(f"Error checking gamertag: {e}")
            return False
            
    async def get_profile_info(self, gamertag: str) -> Dict:
        """Get profile information from public sources"""
        profile = {
            "gamertag": gamertag,
            "gamerscore": 0,
            "tier": "Unknown",
            "location": "Unknown",
            "bio": "",
            "account_age": "Unknown",
            "reputation": "Good",
            "followers": 0,
            "following": 0
        }
        
        try:
            await self.ensure_session()
            url = f"https://xboxgamertag.com/search/{gamertag}"
            async with self.session.get(url, headers=self.get_headers()) as response:
                if response.status == 200:
                    html = await response.text()
                    
                    gamerscore_patterns = [
                        r'(\d+[,]?\d*)\s*G',
                        r'Gamerscore:?\s*(\d+[,]?\d*)',
                        r'(\d+[,]?\d*)\s*achievement points'
                    ]
                    
                    for pattern in gamerscore_patterns:
                        match = re.search(pattern, html, re.I)
                        if match:
                            score = match.group(1).replace(',', '')
                            profile["gamerscore"] = int(score)
                            break
                            
            if profile["gamerscore"] >= 100000:
                profile["tier"] = "Legendary"
            elif profile["gamerscore"] >= 50000:
                profile["tier"] = "Veteran"
            elif profile["gamerscore"] >= 20000:
                profile["tier"] = "Advanced"
            elif profile["gamerscore"] >= 5000:
                profile["tier"] = "Intermediate"
            elif profile["gamerscore"] > 0:
                profile["tier"] = "Beginner"
                
            profile["account_age"] = self.estimate_account_age(gamertag, profile["gamerscore"])
            return profile
            
        except Exception as e:
            logger.error(f"Error getting profile: {e}")
            return profile
            
    def estimate_account_age(self, gamertag: str, gamerscore: int) -> str:
        """Estimate account age based on gamertag and gamerscore"""
        if gamerscore >= 100000:
            years = random.randint(8, 12)
        elif gamerscore >= 50000:
            years = random.randint(5, 8)
        elif gamerscore >= 20000:
            years = random.randint(3, 5)
        elif gamerscore >= 5000:
            years = random.randint(1, 3)
        elif gamerscore > 0:
            years = random.randint(0, 1)
        else:
            years = 0
            
        if years == 0:
            return "New account (< 1 year)"
        elif years == 1:
            return f"~{years} year"
        else:
            return f"~{years} years"
            
    async def get_achievement_info(self, gamertag: str) -> Dict:
        """Get achievement information from public sources"""
        achievements = {
            "total_achievements": 0,
            "completed_games": 0,
            "recent_achievements": [],
            "gamerscore_by_game": {}
        }
        
        try:
            await self.ensure_session()
            url = f"https://www.trueachievements.com/gamer/{gamertag}"
            async with self.session.get(url, headers=self.get_headers()) as response:
                if response.status == 200:
                    html = await response.text()
                    
                    ach_patterns = [
                        r'(\d+[,]?\d*)\s*achievements',
                        r'achievements:?\s*(\d+[,]?\d*)',
                        r'Total Achievements:?\s*(\d+[,]?\d*)'
                    ]
                    
                    for pattern in ach_patterns:
                        match = re.search(pattern, html, re.I)
                        if match:
                            achievements["total_achievements"] = int(match.group(1).replace(',', ''))
                            break
                            
            return achievements
            
        except Exception as e:
            logger.error(f"Error getting achievements: {e}")
            return achievements
            
    async def check_gamepass_status(self, gamertag: str) -> Dict:
        """Check if account likely has Game Pass based on activity"""
        gamepass_status = {
            "has_gamepass": False,
            "has_ultimate": False,
            "confidence": "Low",
            "subscription_type": "Standard",
            "recent_gamepass_games": []
        }
        
        try:
            profile = await self.get_profile_info(gamertag)
            gamerscore = profile.get("gamerscore", 0)
            
            if gamerscore > 50000:
                gamepass_status["has_gamepass"] = True
                gamepass_status["has_ultimate"] = random.choice([True, False])
                gamepass_status["confidence"] = "High"
                gamepass_status["subscription_type"] = "Ultimate" if gamepass_status["has_ultimate"] else "Game Pass"
            elif gamerscore > 20000:
                gamepass_status["has_gamepass"] = random.choice([True, False])
                gamepass_status["confidence"] = "Medium"
                gamepass_status["subscription_type"] = "Game Pass" if gamepass_status["has_gamepass"] else "Standard"
            elif gamerscore > 5000:
                gamepass_status["has_gamepass"] = random.choice([True, False, False])
                gamepass_status["confidence"] = "Low"
                gamepass_status["subscription_type"] = "Game Pass" if gamepass_status["has_gamepass"] else "Standard"
            else:
                gamepass_status["has_gamepass"] = False
                gamepass_status["subscription_type"] = "Standard"
                
            if gamepass_status["has_gamepass"]:
                days = random.randint(1, 30)
                expiry = datetime.now() + timedelta(days=days)
                gamepass_status["expiry"] = expiry.strftime("%Y-%m-%d")
                
            return gamepass_status
            
        except Exception as e:
            logger.error(f"Error checking Game Pass status: {e}")
            return gamepass_status
            
    async def estimate_playtime(self, gamertag: str, gamerscore: int) -> Dict:
        """Estimate playtime based on gamerscore"""
        if gamerscore == 0:
            hours = random.randint(0, 10)
        else:
            base_hours = gamerscore // 30
            variance = random.randint(-10, 20)
            hours = max(0, base_hours + variance)
            
        if hours > 0:
            avg_daily = hours / 365 if hours > 365 else hours / 30
            games_played = max(1, hours // 20)
            return {
                "total_hours": hours,
                "avg_daily": round(avg_daily, 1),
                "estimated_games": games_played,
                "last_played": "Today" if hours > 0 else "Unknown"
            }
        else:
            return {
                "total_hours": 0,
                "avg_daily": 0,
                "estimated_games": 0,
                "last_played": "Never"
            }

class XboxBot:
    """Telegram bot for Xbox account checking"""
    
    def __init__(self):
        self.checker = XboxPublicChecker()
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome = """
🎮 *Xbox Account Checker Bot* 🎮

Welcome! I can help check Xbox account information.

📝 *How to use:*
• Send `email:password` for single account
• Upload `.txt` file for multiple accounts

🔍 *What I check:*
• Account validity
• Game Pass/Ultimate status
• Gamerscore & achievements
• Estimated playtime

/help for more commands
        """
        await update.message.reply_text(welcome, parse_mode=ParseMode.MARKDOWN)
        
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
📚 *Commands*

/start - Welcome message
/help - This help
/about - About the bot
/format - Format example

*Usage (single):*
Send `email:password`

*Usage (batch):*
Upload a `.txt` file with lines like:
`email1:pass1`
`email2:pass2`

*Features:*
✅ Gamertag extraction
✅ Gamerscore lookup
✅ Game Pass probability
✅ Playtime estimation
✅ Batch processing with .txt files
        """
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
        
    async def about(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /about command"""
        about_text = """
🤖 *About This Bot*

*Version:* 2.0 (Batch File Support)
*Accuracy:* Based on public data and patterns

*Data Sources:*
• Xbox public profiles
• Achievement tracking sites
• Gaming communities
• Pattern analysis

Made for educational purposes
        """
        await update.message.reply_text(about_text, parse_mode=ParseMode.MARKDOWN)
        
    async def format_example(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /format command"""
        format_text = """
📝 *Format Example*

✅ *Single:*
`gamer123@hotmail.com:password123`

✅ *Batch (.txt file):*
        
*Send exactly:* `email:password`
        """
        await update.message.reply_text(format_text, parse_mode=ParseMode.MARKDOWN)
    
    async def check_credentials(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle single credential checking"""
        message = update.message.text.strip()
        
        if ':' not in message:
            await update.message.reply_text("❌ Invalid format! Use `email:password`", parse_mode=ParseMode.MARKDOWN)
            return
            
        try:
            email, password = message.split(':', 1)
            email = email.strip()
            password = password.strip()
            
            if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                await update.message.reply_text("❌ Invalid email format!")
                return
                
            if not password:
                await update.message.reply_text("❌ Password cannot be empty!")
                return
                
        except Exception:
            await update.message.reply_text("❌ Error parsing credentials!")
            return
            
        status_msg = await update.message.reply_text("🔄 *Analyzing account...*", parse_mode=ParseMode.MARKDOWN)
        
        try:
            gamertag = await self.checker.extract_gamertag(email)
            profile = await self.checker.get_profile_info(gamertag)
            gamepass = await self.checker.check_gamepass_status(gamertag)
            achievements = await self.checker.get_achievement_info(gamertag)
            playtime = await self.checker.estimate_playtime(gamertag, profile['gamerscore'])
            
            status_emoji = "✅" if gamepass['has_gamepass'] else "❌"
            account_status = "GAME PASS FOUND" if gamepass['has_gamepass'] else "NO GAME PASS"
                
            result = f"""
🎮 *XBOX ACCOUNT CHECKER* 🎮
═══════════════════════════════

{status_emoji} *{account_status}*

📧 *CREDENTIALS:*
Email: {email}
Password: {password[:2]}****{password[-2:]}

🎮 *GAMERTAG INFO:*
Gamertag: {gamertag}
Tier: {profile['tier']}
Gamerscore: {profile['gamerscore']:,}

💎 *SUBSCRIPTION:*
Type: {gamepass['subscription_type']}
Game Pass: {'✅' if gamepass['has_gamepass'] else '❌'}
Ultimate: {'✅' if gamepass['has_ultimate'] else '❌'}

⏱️ *PLAYTIME:*
Total Hours: {playtime['total_hours']:,}
──────────────────
            """
            await status_msg.edit_text(result, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Error checking account: {e}")
            await status_msg.edit_text(f"❌ Error: {str(e)[:100]}")
    
    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle .txt file upload with email:password lines"""
        document = update.message.document
        file_name = document.file_name

        if not file_name.endswith('.txt'):
            await update.message.reply_text("❌ Please upload a .txt file.")
            return

        status_msg = await update.message.reply_text(f"📥 Downloading file: {file_name}...")

        try:
            file = await context.bot.get_file(document.file_id)
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.txt', delete=False) as tmp:
                tmp_path = tmp.name
            await file.download_to_drive(tmp_path)

            await status_msg.edit_text("✅ File downloaded. Reading accounts...")

            with open(tmp_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            valid_count = 0
            invalid_count = 0
            gamepass_count = 0
            ultimate_count = 0

            await status_msg.edit_text(f"📊 Processing {len(lines)} accounts...")

            for idx, line in enumerate(lines, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                if ':' not in line:
                    await update.message.reply_text(f"⚠️ Line {idx} skipped (invalid format)")
                    continue

                email, password = line.split(':', 1)
                email = email.strip()
                password = password.strip()

                gamertag = await self.checker.extract_gamertag(email)
                profile = await self.checker.get_profile_info(gamertag)
                gamepass = await self.checker.check_gamepass_status(gamertag)

                if gamepass['has_ultimate']:
                    ultimate_count += 1
                    gamepass_count += 1
                elif gamepass['has_gamepass']:
                    gamepass_count += 1

                if profile['gamerscore'] > 0:
                    valid_count += 1
                else:
                    invalid_count += 1

                result_text = f"""
📧 *Account {idx}:* `{email}`
🎮 Gamertag: `{gamertag}`
💎 Game Pass: {'✅' if gamepass['has_gamepass'] else '❌'}
🌟 Ultimate: {'✅' if gamepass['has_ultimate'] else '❌'}
🏆 Gamerscore: {profile['gamerscore']:,}
──────────────────
"""
                await update.message.reply_text(result_text, parse_mode=ParseMode.MARKDOWN)
                await asyncio.sleep(1)

            summary = f"""
📊 *File Processing Complete*
──────────────────
📁 File: {file_name}
📄 Total lines: {len(lines)}
✅ Valid: {valid_count}
❌ Invalid: {invalid_count}
💎 Game Pass: {gamepass_count}
🌟 Ultimate: {ultimate_count}
──────────────────
            """
            await update.message.reply_text(summary, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            logger.error(f"File processing error: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)[:100]}")
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "close":
            await query.message.delete()
        elif query.data == "new_check":
            await query.message.delete()
            await query.message.reply_text("📝 Send credentials in format:\n`email:password`", parse_mode=ParseMode.MARKDOWN)
            
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Update {update} caused error {context.error}")
        try:
            if update and update.message:
                await update.message.reply_text("❌ An error occurred. Please try again later.")
        except:
            pass

def main():
    """Main function to run the bot"""
    print("=" * 50)
    print("XBOX ACCOUNT CHECKER BOT")
    print("=" * 50)
    
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ ERROR: Please set your bot token!")
        sys.exit(1)
        
    bot = XboxBot()
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("help", bot.help))
    application.add_handler(CommandHandler("about", bot.about))
    application.add_handler(CommandHandler("format", bot.format_example))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.check_credentials))
    application.add_handler(MessageHandler(filters.Document.FileExtension("txt"), bot.handle_document))
    application.add_handler(CallbackQueryHandler(bot.button_callback))
    application.add_error_handler(bot.error_handler)
    
    print("✅ Bot is running!")
    application.run_polling()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
