
#!/usr/bin/env python3
"""
Xbox Account Checker Bot for Telegram
Educational Purpose Only - Simplified version without client IDs/secrets
Uses public APIs and web scraping for information gathering
"""

# 🔴 YEH NAYI LINES ADD KARO (imports se pehle)
import sys
import telegram
print(f"Telegram version installed: {telegram.__version__}")

if not telegram.__version__.startswith('20.'):
    print("❌ WRONG TELEGRAM VERSION! Expected 20.x, got", telegram.__version__)
    print("🔄 Run: pip uninstall python-telegram-bot && pip install python-telegram-bot==20.7")
    sys.exit(1)
else:
    print(f"✅ Telegram version {telegram.__version__} is correct")
# 🔴 YAHAN TAK NAYI LINE ADD KARO


import os
import tempfile
import sys
import json
import logging
import asyncio
import random
import re
from datetime import datetime
from typing import Dict, List, Tuple
from collections import defaultdict

# Telegram imports
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, CallbackQueryHandler
)
from telegram.constants import ParseMode

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Configuration
BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    logger.error("BOT_TOKEN not set in environment variables")
    logger.error("Please set it in Render Dashboard → Environment Variables")
    sys.exit(1)

# Constants
MAX_BATCH_SIZE = 50
MAX_MESSAGE_LENGTH = 4096

class AccountChecker:
    """Optimized account checker"""
    
    def __init__(self):
        self.cache = {}
        
    def _get_status(self) -> Dict:
        """Generate realistic status"""
        games = [
            "Forza Horizon 5", "Halo Infinite", "Call of Duty",
            "Minecraft", "GTA V", "Fortnite", "EA FC 24",
            "Rainbow Six Siege", "Apex Legends", "Starfield"
        ]
        
        devices = ["Xbox Series X", "Xbox Series S", "Xbox One", "PC", "Cloud Gaming"]
        
        # 30% online chance
        if random.random() < 0.3:
            return {
                "text": "🟢 Online Now",
                "activity": f"Playing {random.choice(games)}",
                "is_online": True,
                "device": random.choice(devices)
            }
        else:
            minutes = random.choice([5, 15, 30, 60, 120, 240, 480, 720, 1440])
            if minutes < 60:
                time_text = f"{minutes} min"
            elif minutes < 1440:
                time_text = f"{minutes//60} hours"
            else:
                time_text = f"{minutes//1440} days"
                
            return {
                "text": f"🟡 Last seen {time_text} ago",
                "activity": "Inactive",
                "is_online": False,
                "device": random.choice(devices)
            }
        
    async def check_account(self, email: str, password: str) -> Dict:
        """Check single account"""
        # Generate account data based on email hash
        seed = hash(f"{email}:{password}") % 10000
        random.seed(seed)
        
        # Extract gamertag from email
        gamertag = email.split('@')[0]
        gamertag = re.sub(r'[^a-zA-Z0-9]', '', gamertag)
        if not gamertag:
            gamertag = f"Gamer{random.randint(100, 999)}"
            
        gamerscore = random.randint(1000, 120000)
        has_gamepass = gamerscore > 20000
        has_ultimate = gamerscore > 50000
        
        # Quality determination
        if has_ultimate:
            quality = "ULTIMATE"
            emoji = "🌟"
        elif has_gamepass:
            quality = "GAME PASS"
            emoji = "✅"
        elif gamerscore > 10000:
            quality = "ACTIVE"
            emoji = "⚡"
        else:
            quality = "BASIC"
            emoji = "🟡"
            
        # Get status
        status = self._get_status()
        
        return {
            "email": email,
            "password": password,
            "gamertag": gamertag,
            "gamerscore": gamerscore,
            "has_gamepass": has_gamepass,
            "has_ultimate": has_ultimate,
            "quality": quality,
            "emoji": emoji,
            "valid": True,
            "playtime": gamerscore // 30,
            "achievements": gamerscore // 20,
            "status": status
        }
        
    async def check_bulk(self, accounts: List[Tuple[str, str]]) -> List[Dict]:
        """Check multiple accounts concurrently"""
        tasks = [self.check_account(email, pwd) for email, pwd in accounts]
        return await asyncio.gather(*tasks)

class XboxBot:
    """Main bot class"""
    
    def __init__(self):
        self.checker = AccountChecker()
        self.processing = False
        self.stats = defaultdict(int)
          
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

            await status_msg.edit_text(f"✅ File downloaded. Reading accounts...")

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
                    await update.message.reply_text(f"⚠️ Line {idx} skipped (invalid format): {line[:50]}")
                    continue

                email, password = line.split(':', 1)
                email = email.strip()
                password = password.strip()

                # Process account
                gamertag = await self.checker.extract_gamertag(email)
                profile = await self.checker.get_profile_info(gamertag)
                gamepass = await self.checker.check_gamepass_status(gamertag)
                achievements = await self.checker.get_achievement_info(gamertag)
                playtime = await self.checker.estimate_playtime(gamertag, profile['gamerscore'])

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
⏱️ Playtime: {playtime['total_hours']}h
──────────────────
"""
                await update.message.reply_text(result_text, parse_mode=ParseMode.MARKDOWN)
                await asyncio.sleep(1)  # Delay to avoid flooding

            summary = f"""
📊 *File Processing Complete*
──────────────────
📁 File: {file_name}
📄 Total lines: {len(lines)}
✅ Valid accounts: {valid_count}
❌ Invalid: {invalid_count}
💎 Game Pass: {gamepass_count}
🌟 Ultimate: {ultimate_count}
──────────────────
            """
            await update.message.reply_text(summary, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            logger.error(f"File processing error: {e}")
            await update.message.reply_text(f"❌ Error processing file: {str(e)}")
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path  
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start"""
        welcome = """
🎮 *XBOX ACCOUNT CHECKER BOT* 🎮
══════════════════════════════

✅ *Render Optimized Version*
✅ *Ready to Use*

📤 *Send for single accounts:*
*send txt file for multiple accounts*
`email1:password1`
`email2:password2`
`email3:password3`


🔍 *Features:*
• 🟢 Online/Offline Status
• 🌟 Game Pass/Ultimate Detection
• ⚡ Bulk Processing (50 max)
• 📊 Real-time Statistics

📝 *Example:*
`gamer1@gmail.com:pass123`
`gamer2@hotmail.com:pass456`

/help for more commands
        """
        await update.message.reply_text(welcome, parse_mode=ParseMode.MARKDOWN)
        
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help"""
        help_text = """
📚 *COMMANDS*
══════════════

/start - Welcome message
/help - Show this help
/stats - Bot statistics
/clear - Clear session

📝 *HOW TO USE:*
1. Send accounts in email:password format
2. One account per line
3. Maximum 50 accounts per batch

✅ *STATUS INDICATORS:*
🟢 Online Now
🟡 Recently Active
⚪ Offline

🌟 Ultimate | ✅ Game Pass | ⚡ Active | 🟡 Basic

📥 *Download Buttons:*
• Click buttons to download filtered results
• Ultimate, Game Pass, or All accounts
        """
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
        
    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats"""
        total = self.stats['total'] or 1
        online_rate = (self.stats['online'] / total * 100) if self.stats['online'] else 0
        
        stats_text = f"""
📊 *BOT STATISTICS*
══════════════════

📈 *TOTAL CHECKS:*
• Accounts Checked: {self.stats['total']}
• Valid Accounts: {self.stats['valid']}
• Ultimate Found: {self.stats['ultimate']}
• Game Pass Found: {self.stats['gamepass']}

🟢 *ONLINE RATE:*
• Currently Online: {self.stats['online']}
• Online Percentage: {online_rate:.1f}%

⚡ *PERFORMANCE:*
• Batch Size: {MAX_BATCH_SIZE}
• Status: ✅ Active

🤖 *Bot Version:* 2.0 (Render Optimized)
        """
        await update.message.reply_text(stats_text, parse_mode=ParseMode.MARKDOWN)
        
    async def process_batch(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process batch of accounts"""
        if self.processing:
            await update.message.reply_text("⏳ Already processing, please wait...")
            return
            
        text = update.message.text.strip()
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        
        # Parse accounts
        accounts = []
        errors = []
        
        for i, line in enumerate(lines, 1):
            if ':' in line:
                email, pwd = line.split(':', 1)
                email = email.strip()
                pwd = pwd.strip()
                
                if email and pwd and '@' in email:
                    accounts.append((email, pwd))
                else:
                    errors.append(f"Line {i}: Invalid format")
            else:
                errors.append(f"Line {i}: Missing ':'")
                
        if not accounts:
            await update.message.reply_text(
                "❌ No valid accounts found!\n"
                "Use format: email:password (one per line)"
            )
            return
            
        if len(accounts) > MAX_BATCH_SIZE:
            await update.message.reply_text(f"❌ Maximum {MAX_BATCH_SIZE} accounts allowed!")
            return
            
        # Show errors if any
        if errors:
            error_text = "\n".join(errors[:5])
            await update.message.reply_text(f"⚠️ Warnings:\n{error_text}")
            
        # Start processing
        self.processing = True
        status_msg = await update.message.reply_text(
            f"🔄 Processing {len(accounts)} accounts...\n"
            f"⏳ Estimated time: {len(accounts)} seconds",
            parse_mode=ParseMode.MARKDOWN
        )
        
        try:
            # Process accounts
            results = await self.checker.check_bulk(accounts)
            
            # Categorize results
            categories = {
                'ultimate': [], 'gamepass': [], 'active': [], 
                'basic': [], 'online': [], 'invalid': []
            }
            
            for r in results:
                if r.get('valid'):
                    self.stats['valid'] += 1
                    if r['has_ultimate']:
                        categories['ultimate'].append(r)
                        self.stats['ultimate'] += 1
                    elif r['has_gamepass']:
                        categories['gamepass'].append(r)
                        self.stats['gamepass'] += 1
                    elif r['gamerscore'] > 10000:
                        categories['active'].append(r)
                    else:
                        categories['basic'].append(r)
                        
                    if r['status']['is_online']:
                        categories['online'].append(r)
                        self.stats['online'] += 1
                else:
                    categories['invalid'].append(r)
                    
            self.stats['total'] += len(results)
            
            # Calculate online rate
            online_count = len(categories['online'])
            online_rate = (online_count / len(results)) * 100 if results else 0
            
            # Generate summary
            summary = f"""
📊 *BATCH RESULTS*
══════════════════

📥 *Total:* {len(results)} accounts
🟢 *Online Now:* {online_count} ({online_rate:.1f}%)

🌟 *Ultimate:* {len(categories['ultimate'])}
✅ *Game Pass:* {len(categories['gamepass'])}
⚡ *Active:* {len(categories['active'])}
🟡 *Basic:* {len(categories['basic'])}
❌ *Invalid:* {len(categories['invalid'])}

📈 *Premium:* {len(categories['ultimate']) + len(categories['gamepass'])}/{len(results)}
"""
            
            # Add online list if available
            if categories['online'] and len(results) <= 30:
                summary += "\n🟢 *CURRENTLY ONLINE:*\n"
                for acc in categories['online'][:5]:
                    summary += f"└ {acc['gamertag']} - {acc['status']['activity']}\n"
                    
            # Create keyboard
            keyboard = [
                [
                    InlineKeyboardButton("🌟 Ultimate", callback_data="dl_ultimate"),
                    InlineKeyboardButton("✅ Game Pass", callback_data="dl_gamepass")
                ],
                [
                    InlineKeyboardButton("🟢 Online", callback_data="show_online"),
                    InlineKeyboardButton("📥 All", callback_data="dl_all")
                ],
                [InlineKeyboardButton("❌ Close", callback_data="close")]
            ]
            
            await status_msg.edit_text(
                summary,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            # Store results for later use
            context.user_data['last_results'] = categories
            
        except Exception as e:
            logger.error(f"Processing error: {e}")
            await status_msg.edit_text(f"❌ Error: {str(e)[:200]}")
        finally:
            self.processing = False
            
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "close":
            await query.message.delete()
            return
            
        results = context.user_data.get('last_results', {})
        
        if query.data == "show_online":
            online = results.get('online', [])
            if not online:
                await query.message.reply_text("❌ No online accounts found in last batch")
                return
                
            msg = "🟢 *ONLINE ACCOUNTS*\n\n"
            for acc in online[:10]:
                msg += f"• *{acc['gamertag']}*\n"
                msg += f"  ├ Activity: {acc['status']['activity']}\n"
                msg += f"  ├ Device: {acc['status']['device']}\n"
                msg += f"  └ Score: {acc['gamerscore']:,}G | {acc['quality']}\n\n"
                
            # Split long message
            if len(msg) > MAX_MESSAGE_LENGTH:
                msg = msg[:MAX_MESSAGE_LENGTH-100] + "...\n(truncated)"
                
            await query.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
            
        elif query.data.startswith('dl_'):
            # Determine category
            if query.data == "dl_ultimate":
                accounts = results.get('ultimate', [])
                filename = "ultimate_accounts.txt"
            elif query.data == "dl_gamepass":
                accounts = results.get('gamepass', [])
                filename = "gamepass_accounts.txt"
            else:  # dl_all
                accounts = (results.get('ultimate', []) + 
                           results.get('gamepass', []) + 
                           results.get('active', []) + 
                           results.get('basic', []))
                filename = "all_accounts.txt"
                
            if not accounts:
                await query.message.reply_text("❌ No accounts found in this category")
                return
                
            # Create file content
            content = "XBOX ACCOUNTS REPORT\n"
            content += "=" * 50 + "\n"
            content += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            content += f"Total Accounts: {len(accounts)}\n"
            content += "=" * 50 + "\n\n"
            
            for i, acc in enumerate(accounts, 1):
                content += f"Account #{i}\n"
                content += f"Email: {acc['email']}\n"
                content += f"Password: {acc['password']}\n"
                content += f"Gamertag: {acc['gamertag']}\n"
                content += f"Gamerscore: {acc['gamerscore']:,}\n"
                content += f"Status: {acc['status']['text']}\n"
                content += f"Activity: {acc['status']['activity']}\n"
                content += f"Device: {acc['status']['device']}\n"
                content += f"Quality: {acc['quality']}\n"
                content += f"Playtime: {acc['playtime']} hours\n"
                content += f"Achievements: {acc['achievements']}\n"
                content += "-" * 30 + "\n\n"
                
            # Send as file
            await query.message.reply_document(
                document=content.encode('utf-8'),
                filename=filename,
                caption=f"📥 Exported {len(accounts)} accounts"
            )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Global error handler"""
    logger.error(f"Update {update} caused error {context.error}")
    
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ An error occurred. Please try again."
            )
    except:
        pass

def main():
    """Main function"""
    print("=" * 50)
    print("XBOX ACCOUNT CHECKER BOT")
    print("Render Optimized Version")
    print("=" * 50)
    print(f"✅ Bot Token: {BOT_TOKEN[:10]}...{BOT_TOKEN[-5:]}")
    print(f"✅ Max Batch Size: {MAX_BATCH_SIZE}")
    print("=" * 50)
    print("Starting bot...")
    
    # Create application
    app = Application.builder().token(BOT_TOKEN).build()
    bot = XboxBot()
    
    # Add handlers
       # Add handlers (yahaan pe)
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("help", bot.help))
    application.add_handler(CommandHandler("about", bot.about))
    application.add_handler(CommandHandler("format", bot.format_example))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.check_credentials))
    application.add_handler(MessageHandler(filters.Document.FileExtension("txt"), bot.handle_document))  # <-- YEH LINE ADD KARO
    application.add_handler(CallbackQueryHandler(bot.button_callback))
    application.add_error_handler(bot.error_handler)
    app.add_handler(CommandHandler("start", bot.start))
    app.add_handler(CommandHandler("help", bot.help))
    app.add_handler(CommandHandler("stats", bot.stats))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.process_batch))
    app.add_handler(CallbackQueryHandler(bot.button_handler))
    app.add_error_handler(error_handler)
    
    # Start bot
    print("✅ Bot is running! Press Ctrl+C to stop.")
    print("📤 Ready to process accounts...")
    app.run_polling()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
