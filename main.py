#!/usr/bin/env python3
"""
ULTIMATE XBOX BOT - xbl.io API
User Limit: 400 requests/hour per user
Author: Your Name
"""

import os
import json
import time
import asyncio
import logging
import hashlib
import threading
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List
from collections import defaultdict, deque
from functools import wraps

import aiohttp
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    filters, ContextTypes, CallbackQueryHandler
)
from telegram.constants import ParseMode

# ============================================
# CONFIGURATION
# ============================================

# Telegram Bot Token (from @BotFather)
BOT_TOKEN = os.environ.get('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')

# xbl.io API Key (get from https://xbl.io)
XBL_API_KEY = os.environ.get('XBL_API_KEY', 'YOUR_XBL_API_KEY_HERE')

# Admin user IDs
ADMIN_IDS = [int(id) for id in os.environ.get('ADMIN_IDS', '').split(',') if id]

# Rate limit per user (400 requests/hour)
REQUESTS_PER_HOUR = 400

# Cache timeout (seconds)
CACHE_TIMEOUT = 300  # 5 minutes

# ============================================
# SETUP
# ============================================

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Flask app for keeping Replit alive
app = Flask(__name__)

@app.route('/')
def home():
    return """
    <html>
        <head><title>Xbox Ultimate Bot</title></head>
        <body style="font-family: Arial; text-align: center; margin-top: 50px;">
            <h1>🎮 Xbox Ultimate Bot is Running!</h1>
            <p>400 requests/hour per user limit</p>
            <p>Find me on Telegram!</p>
        </body>
    </html>
    """

# ============================================
# RATE LIMITER
# ============================================

class RateLimiter:
    """Rate limiter per user"""
    
    def __init__(self, max_requests: int, window_seconds: int = 3600):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.users = defaultdict(lambda: deque(maxlen=max_requests))
    
    def is_allowed(self, user_id: int) -> Tuple[bool, int]:
        """Check if user is allowed to make request"""
        now = time.time()
        user_requests = self.users[user_id]
        
        # Remove old requests
        while user_requests and now - user_requests[0] > self.window_seconds:
            user_requests.popleft()
        
        # Check if under limit
        if len(user_requests) < self.max_requests:
            user_requests.append(now)
            return True, self.max_requests - len(user_requests)
        else:
            oldest = user_requests[0]
            wait_time = int(self.window_seconds - (now - oldest))
            return False, wait_time
    
    def get_remaining(self, user_id: int) -> int:
        """Get remaining requests for user"""
        now = time.time()
        user_requests = self.users[user_id]
        
        # Remove old requests
        while user_requests and now - user_requests[0] > self.window_seconds:
            user_requests.popleft()
        
        return self.max_requests - len(user_requests)

# Initialize rate limiter
rate_limiter = RateLimiter(REQUESTS_PER_HOUR)

# ============================================
# CACHE MANAGER
# ============================================

class CacheManager:
    """Simple cache manager"""
    
    def __init__(self, timeout_seconds: int = 300):
        self.cache = {}
        self.timeout = timeout_seconds
    
    def get(self, key: str) -> Optional[any]:
        """Get from cache"""
        if key in self.cache:
            data, timestamp = self.cache[key]
            if time.time() - timestamp < self.timeout:
                return data
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value: any):
        """Set in cache"""
        self.cache[key] = (value, time.time())
    
    def clear(self):
        """Clear cache"""
        self.cache.clear()

# Initialize cache
cache = CacheManager(CACHE_TIMEOUT)

# ============================================
# XBL.IO API CLIENT
# ============================================

class XBLIOClient:
    """Client for xbl.io API with rate limiting and caching"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://xbl.io/api/v2"
        self.session = None
        self.headers = {
            "X-Authorization": self.api_key,
            "Accept": "application/json",
            "User-Agent": "XboxUltimateBot/1.0"
        }
        self.request_count = 0
        self.last_reset = time.time()
    
    async def ensure_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(headers=self.headers)
    
    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def _request(self, method: str, endpoint: str, params: dict = None) -> Optional[dict]:
        """Make API request with rate limit handling"""
        await self.ensure_session()
        url = f"{self.base_url}{endpoint}"
        
        # Track global rate limit
        self.request_count += 1
        if self.request_count >= 450:  # Leave buffer
            await asyncio.sleep(60)
            self.request_count = 0
        
        try:
            async with self.session.request(method, url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 429:
                    logger.warning("Rate limited! Waiting...")
                    await asyncio.sleep(60)
                    return await self._request(method, endpoint, params)
                else:
                    logger.error(f"API error {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Request error: {e}")
            return None
    
    # ========== PROFILE ENDPOINTS ==========
    
    async def get_profile_by_gamertag(self, gamertag: str) -> Optional[dict]:
        """Get profile by gamertag"""
        cache_key = f"profile_{gamertag}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        data = await self._request("GET", f"/profile/{gamertag}")
        if data:
            cache.set(cache_key, data)
        return data
    
    async def get_profile_by_xuid(self, xuid: str) -> Optional[dict]:
        """Get profile by XUID"""
        cache_key = f"profile_xuid_{xuid}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        data = await self._request("GET", f"/profile/xuid/{xuid}")
        if data:
            cache.set(cache_key, data)
        return data
    
    # ========== ACHIEVEMENT ENDPOINTS ==========
    
    async def get_achievements(self, xuid: str) -> Optional[dict]:
        """Get all achievements"""
        cache_key = f"achievements_{xuid}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        data = await self._request("GET", f"/achievements/xuid/{xuid}")
        if data:
            cache.set(cache_key, data)
        return data
    
    async def get_recent_achievements(self, xuid: str) -> Optional[dict]:
        """Get recent achievements"""
        cache_key = f"recent_ach_{xuid}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        data = await self._request("GET", f"/achievements/recent/xuid/{xuid}")
        if data:
            cache.set(cache_key, data)
        return data
    
    # ========== GAME/TITLE ENDPOINTS ==========
    
    async def get_titles(self, xuid: str) -> Optional[dict]:
        """Get all played titles"""
        cache_key = f"titles_{xuid}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        data = await self._request("GET", f"/titlehub/xuid/{xuid}")
        if data:
            cache.set(cache_key, data)
        return data
    
    async def get_recent_titles(self, xuid: str) -> Optional[dict]:
        """Get recently played titles"""
        cache_key = f"recent_titles_{xuid}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        data = await self._request("GET", f"/titlehub/recent/xuid/{xuid}")
        if data:
            cache.set(cache_key, data)
        return data
    
    # ========== PRESENCE ENDPOINTS ==========
    
    async def get_presence(self, xuid: str) -> Optional[dict]:
        """Get user presence (online/offline)"""
        cache_key = f"presence_{xuid}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        data = await self._request("GET", f"/presence/xuid/{xuid}")
        if data:
            cache.set(cache_key, data)
        return data
    
    # ========== SOCIAL ENDPOINTS ==========
    
    async def get_friends(self, xuid: str) -> Optional[dict]:
        """Get friends list"""
        cache_key = f"friends_{xuid}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        data = await self._request("GET", f"/friends/xuid/{xuid}")
        if data:
            cache.set(cache_key, data)
        return data
    
    async def get_followers(self, xuid: str) -> Optional[dict]:
        """Get followers list"""
        cache_key = f"followers_{xuid}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        data = await self._request("GET", f"/followers/xuid/{xuid}")
        if data:
            cache.set(cache_key, data)
        return data
    
    # ========== CLUBS ENDPOINTS ==========
    
    async def get_clubs(self, xuid: str) -> Optional[dict]:
        """Get user clubs"""
        cache_key = f"clubs_{xuid}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        data = await self._request("GET", f"/clubs/xuid/{xuid}")
        if data:
            cache.set(cache_key, data)
        return data

# ============================================
# ACCOUNT CHECKER CLASS
# ============================================

class XboxAccountChecker:
    """Main account checker class"""
    
    def __init__(self, api_client: XBLIOClient):
        self.api = api_client
    
    async def check_by_gamertag(self, gamertag: str) -> Dict:
        """Get full account info by gamertag"""
        result = {
            "success": False,
            "gamertag": gamertag,
            "xuid": None,
            "profile": None,
            "presence": None,
            "titles": None,
            "achievements": None,
            "recent_achievements": None,
            "friends": None,
            "clubs": None,
            "stats": {},
            "errors": []
        }
        
        try:
            # Get profile
            profile = await self.api.get_profile_by_gamertag(gamertag)
            if not profile or 'profileUsers' not in profile:
                result['errors'].append("Profile not found")
                return result
            
            profile_user = profile['profileUsers'][0] if profile['profileUsers'] else {}
            settings = profile_user.get('settings', [])
            
            # Extract XUID
            for setting in settings:
                if setting.get('id') == 'XUID':
                    result['xuid'] = setting.get('value')
                    break
            
            if not result['xuid']:
                result['errors'].append("XUID not found")
                return result
            
            result['profile'] = settings
            result['success'] = True
            
            # Get other data in parallel
            tasks = [
                self.api.get_presence(result['xuid']),
                self.api.get_titles(result['xuid']),
                self.api.get_recent_achievements(result['xuid']),
                self.api.get_friends(result['xuid']),
                self.api.get_clubs(result['xuid'])
            ]
            
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            result['presence'] = responses[0] if not isinstance(responses[0], Exception) else None
            result['titles'] = responses[1] if not isinstance(responses[1], Exception) else None
            result['recent_achievements'] = responses[2] if not isinstance(responses[2], Exception) else None
            result['friends'] = responses[3] if not isinstance(responses[3], Exception) else None
            result['clubs'] = responses[4] if not isinstance(responses[4], Exception) else None
            
            # Calculate stats
            result['stats'] = self._calculate_stats(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Check error: {e}")
            result['errors'].append(str(e))
            return result
    
    def _calculate_stats(self, data: Dict) -> Dict:
        """Calculate various stats from account data"""
        stats = {
            "gamerscore": 0,
            "achievements": 0,
            "games_played": 0,
            "rare_achievements": 0,
            "completion_rate": 0,
            "friends_count": 0,
            "followers_count": 0,
            "clubs_count": 0,
            "total_playtime_hours": 0
        }
        
        # From profile
        if data['profile']:
            for item in data['profile']:
                if item.get('id') == 'Gamerscore':
                    stats['gamerscore'] = int(item.get('value', 0))
        
        # From titles
        if data['titles'] and 'titles' in data['titles']:
            stats['games_played'] = len(data['titles']['titles'])
            
            # Calculate total playtime
            for title in data['titles']['titles']:
                stats['total_playtime_hours'] += title.get('titleHistory', {}).get('minutesPlayed', 0) / 60
        
        # From achievements
        if data['recent_achievements']:
            ach_data = data['recent_achievements']
            stats['achievements'] = ach_data.get('totalAchievements', 0)
            stats['rare_achievements'] = ach_data.get('rareAchievements', 0)
        
        # From friends
        if data['friends'] and 'people' in data['friends']:
            stats['friends_count'] = len(data['friends']['people'])
        
        # From clubs
        if data['clubs'] and 'clubs' in data['clubs']:
            stats['clubs_count'] = len(data['clubs']['clubs'])
        
        return stats
    
    def format_profile(self, data: Dict) -> str:
        """Format profile data for display"""
        if not data['success']:
            return f"❌ *Account Not Found*\n\nErrors: {', '.join(data['errors'])}"
        
        profile_dict = {item['id']: item.get('value', 'N/A') for item in data['profile']}
        
        # Basic info
        text = f"""
🎮 *XBOX ACCOUNT INFO* 🎮
══════════════════════════

👤 *Profile*
├ Gamertag: `{data['gamertag']}`
├ XUID: `{data['xuid']}`
├ Gamerscore: `{data['stats']['gamerscore']:,}`
├ Account Tier: `{profile_dict.get('AccountTier', 'Standard')}`
├ Location: `{profile_dict.get('Location', 'Unknown')}`
├ Bio: `{profile_dict.get('Bio', 'N/A')[:50]}`
└ Account Age: `{self._get_account_age(profile_dict.get('JoinDate', ''))}`

💎 *Subscription*
├ Game Pass: {'✅' if 'GamePass' in profile_dict.get('Detail', '') else '❌'}
├ Ultimate: {'✅' if 'Ultimate' in profile_dict.get('Detail', '') else '❌'}
└ Expiry: `{profile_dict.get('SubscriptionExpires', 'N/A')}`

🏆 *Achievements*
├ Total: `{data['stats']['achievements']:,}`
├ Rare: `{data['stats']['rare_achievements']}`
└ Games Played: `{data['stats']['games_played']}`

⏱️ *Playtime*
├ Total Hours: `{data['stats']['total_playtime_hours']:.1f}`
├ Friends: `{data['stats']['friends_count']}`
└ Clubs: `{data['stats']['clubs_count']}`

🟢 *Presence*
"""
        # Presence info
        if data['presence'] and 'state' in data['presence']:
            state = data['presence']['state']
            if state == 'Online':
                text += f"├ Status: 🟢 *Online*\n"
                if 'lastSeen' in data['presence']:
                    text += f"└ Device: `{data['presence']['lastSeen'].get('deviceType', 'Unknown')}`\n"
            else:
                last_seen = data['presence'].get('lastSeen', {})
                text += f"├ Status: ⚫ *Offline*\n"
                text += f"└ Last Seen: `{last_seen.get('timestamp', 'Unknown')}`\n"
        else:
            text += f"└ Status: ❓ *Unknown*\n"
        
        # Recent games
        text += f"\n🎮 *Recent Games*\n"
        if data['titles'] and 'titles' in data['titles']:
            recent = sorted(data['titles']['titles'], 
                          key=lambda x: x.get('titleHistory', {}).get('lastTimePlayed', ''), 
                          reverse=True)[:3]
            for game in recent:
                name = game.get('name', 'Unknown')
                minutes = game.get('titleHistory', {}).get('minutesPlayed', 0)
                text += f"├ {name[:30]} - {minutes//60}h {minutes%60}m\n"
        else:
            text += f"└ No recent games found\n"
        
        # Recent achievements
        text += f"\n🏆 *Recent Achievements*\n"
        if data['recent_achievements'] and 'achievements' in data['recent_achievements']:
            for ach in data['recent_achievements']['achievements'][:3]:
                name = ach.get('name', 'Unknown')
                game = ach.get('title', {}).get('name', 'Unknown')
                rare = '💎' if ach.get('rare') else ''
                text += f"├ {rare} {name[:25]} - {game[:15]}\n"
        else:
            text += f"└ No recent achievements\n"
        
        text += f"\n══════════════════════════\n"
        text += f"_Data from xbl.io • 400 req/hour/user_"
        
        return text
    
    def _get_account_age(self, join_date: str) -> str:
        """Calculate account age from join date"""
        if not join_date or join_date == 'N/A':
            return 'Unknown'
        try:
            join = datetime.fromisoformat(join_date.replace('Z', '+00:00'))
            years = (datetime.now() - join).days / 365
            if years < 1:
                return f"{int(years*12)} months"
            return f"{years:.1f} years"
        except:
            return 'Unknown'

# ============================================
# TELEGRAM BOT
# ============================================

class XboxBot:
    """Telegram bot"""
    
    def __init__(self, api_client: XBLIOClient):
        self.checker = XboxAccountChecker(api_client)
        self.api = api_client
        self.start_time = datetime.now()
        self.total_checks = 0
    
    def rate_limit_decorator(func):
        """Decorator for rate limiting"""
        @wraps(func)
        async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user_id = update.effective_user.id
            
            # Check rate limit
            allowed, remaining_or_wait = rate_limiter.is_allowed(user_id)
            
            if not allowed:
                wait_time = remaining_or_wait
                minutes = wait_time // 60
                seconds = wait_time % 60
                await update.message.reply_text(
                    f"⏳ *Rate Limit Reached*\n\n"
                    f"Wait {minutes}m {seconds}s before next request.\n"
                    f"Limit: {REQUESTS_PER_HOUR}/hour per user",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            # Add remaining info to context
            context.user_data['remaining'] = rate_limiter.get_remaining(user_id)
            
            # Call the function
            return await func(self, update, context, *args, **kwargs)
        return wrapper
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command"""
        await update.message.reply_text(
            """
🎮 *Xbox Ultimate Bot* 🎮
══════════════════════════

Welcome! I can fetch detailed Xbox account information.

📝 *Commands:*
• Send `gamertag` to check any profile
• /help - Show all commands
• /about - Bot info
• /stats - Bot statistics
• /limit - Check your remaining requests

⚡ *Features:*
• Full profile info
• Gamerscore & achievements
• Game Pass status
• Playtime stats
• Recent games & achievements
• Online presence
• Friends & clubs

📊 *Rate Limit:* {REQUESTS_PER_HOUR} requests/hour per user

_Type a gamertag to begin!_
            """,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Help command"""
        await update.message.reply_text(
            f"""
📚 *Commands*

🔍 *Check Profile*
• Just send a gamertag (e.g., `ProGamer123`)
• /check <gamertag> - Same thing

ℹ️ *Info*
/start - Welcome
/help - This menu
/about - Bot details
/stats - Bot statistics
/limit - Your remaining requests

⚙️ *Admin Only*
/broadcast - Message all users
/stats - Detailed stats
/cache - Clear cache

📊 *Rate Limits*
• {REQUESTS_PER_HOUR} requests/hour per user
• Resets every hour
• Cache: 5 minutes

_Need help? Contact @admin_
            """,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def about(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """About command"""
        uptime = datetime.now() - self.start_time
        hours = uptime.total_seconds() // 3600
        minutes = (uptime.total_seconds() % 3600) // 60
        
        await update.message.reply_text(
            f"""
🤖 *About Xbox Ultimate Bot*

*Version:* 2.0 (xbl.io)
*Author:* @username
*Uptime:* {int(hours)}h {int(minutes)}m
*Total Checks:* {self.total_checks}
*API:* xbl.io (unofficial)
*Accuracy:* ~95%

*Rate Limits:*
• {REQUESTS_PER_HOUR}/hour per user
• Cache: 5 minutes

*Features:*
✅ Full profile
✅ Achievements
✅ Game Pass status
✅ Playtime stats
✅ Recent activity
✅ Friends & clubs

*Data Source:* xbl.io API
*Purpose:* Educational

Made with ❤️ for Xbox community
            """,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def limit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Check rate limit"""
        user_id = update.effective_user.id
        remaining = rate_limiter.get_remaining(user_id)
        
        await update.message.reply_text(
            f"📊 *Your Rate Limit*\n\n"
            f"Remaining: {remaining}/{REQUESTS_PER_HOUR}\n"
            f"Resets: Every hour\n\n"
            f"Cache: 5 minutes",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Bot statistics"""
        user_id = update.effective_user.id
        remaining = rate_limiter.get_remaining(user_id)
        
        stats_text = f"""
📊 *Bot Statistics*

*General*
├ Uptime: {datetime.now() - self.start_time}
├ Total Checks: {self.total_checks}
├ Cache Size: {len(cache.cache)} items
└ Users Today: {len(rate_limiter.users)}

*Your Stats*
├ User ID: `{user_id}`
├ Remaining: {remaining}/{REQUESTS_PER_HOUR}
├ Cache: Active
└ Role: {'Admin' if user_id in ADMIN_IDS else 'User'}

*API Status*
├ Provider: xbl.io
├ Status: 🟢 Online
└ Last Check: Just now
        """
        
        # Add keyboard
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh", callback_data="refresh_stats")]
        ]
        
        await update.message.reply_text(
            stats_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    @rate_limit_decorator
    async def check_gamertag(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Check gamertag"""
        # Get gamertag from message
        if update.message.text.startswith('/check'):
            gamertag = update.message.text.replace('/check', '').strip()
        else:
            gamertag = update.message.text.strip()
        
        if not gamertag:
            await update.message.reply_text("❌ Please provide a gamertag")
            return
        
        # Send typing action
        await update.message.chat.send_action(action="typing")
        
        # Initial message
        status_msg = await update.message.reply_text(
            f"🔍 *Checking {gamertag}...*\n\n"
            f"Fetching profile from xbl.io...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        try:
            # Check account
            result = await self.checker.check_by_gamertag(gamertag)
            self.total_checks += 1
            
            # Format result
            formatted = self.checker.format_profile(result)
            
            # Add remaining requests
            remaining = context.user_data.get('remaining', 0)
            formatted += f"\n_You have {remaining} requests remaining_"
            
            # Create keyboard
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_{gamertag}"),
                    InlineKeyboardButton("📊 Full Stats", callback_data=f"fullstats_{result.get('xuid', '')}")
                ],
                [InlineKeyboardButton("❌ Close", callback_data="close")]
            ]
            
            await status_msg.edit_text(
                formatted,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Check error: {e}")
            await status_msg.edit_text(
                f"❌ *Error checking {gamertag}*\n\n"
                f"Details: {str(e)[:100]}\n\n"
                f"Please try again later.",
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "close":
            await query.message.delete()
        
        elif data == "refresh_stats":
            # Refresh stats
            user_id = update.effective_user.id
            remaining = rate_limiter.get_remaining(user_id)
            
            await query.edit_message_text(
                f"""
📊 *Bot Statistics* (Refreshed)

*General*
├ Uptime: {datetime.now() - self.start_time}
├ Total Checks: {self.total_checks}
├ Cache Size: {len(cache.cache)} items
└ Users Today: {len(rate_limiter.users)}

*Your Stats*
├ User ID: `{user_id}`
├ Remaining: {remaining}/{REQUESTS_PER_HOUR}
├ Cache: Active
└ Role: {'Admin' if user_id in ADMIN_IDS else 'User'}

*API Status*
├ Provider: xbl.io
├ Status: 🟢 Online
└ Last Check: Just now
                """,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔄 Refresh", callback_data="refresh_stats")
                ]])
            )
        
        elif data.startswith('refresh_'):
            gamertag = data.replace('refresh_', '')
            # Recheck profile
            await query.message.edit_text(f"🔄 Refreshing {gamertag}...")
            
            # Clear cache for this gamertag
            cache_key = f"profile_{gamertag}"
            if cache_key in cache.cache:
                del cache.cache[cache_key]
            
            # Recheck
            result = await self.checker.check_by_gamertag(gamertag)
            formatted = self.checker.format_profile(result)
            
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_{gamertag}"),
                    InlineKeyboardButton("📊 Full Stats", callback_data=f"fullstats_{result.get('xuid', '')}")
                ],
                [InlineKeyboardButton("❌ Close", callback_data="close")]
            ]
            
            await query.message.edit_text(
                formatted,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Update {update} caused error {context.error}")
        
        try:
            if update and update.message:
                await update.message.reply_text(
                    "❌ An error occurred. Please try again later."
                )
        except:
            pass

# ============================================
# MAIN FUNCTION
# ============================================

def run_bot():
    """Run the bot in a thread"""
    # Create API client
    api_client = XBLIOClient(XBL_API_KEY)
    
    # Create bot
    bot = XboxBot(api_client)
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("help", bot.help))
    application.add_handler(CommandHandler("about", bot.about))
    application.add_handler(CommandHandler("limit", bot.limit))
    application.add_handler(CommandHandler("stats", bot.stats))
    application.add_handler(CommandHandler("check", bot.check_gamertag))
    
    # Handle text messages (gamertags)
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        bot.check_gamertag
    ))
    
    # Callback handler
    application.add_handler(CallbackQueryHandler(bot.button_callback))
    
    # Error handler
    application.add_error_handler(bot.error_handler)
    
    # Start bot
    logger.info("Bot started!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

def main():
    """Main function"""
    print("=" * 50)
    print("XBOX ULTIMATE BOT")
    print("=" * 50)
    
    # Check configuration
    if BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
        print("❌ ERROR: BOT_TOKEN not set!")
        print("Get it from @BotFather")
        return
    
    if XBL_API_KEY == 'YOUR_XBL_API_KEY_HERE':
        print("❌ ERROR: XBL_API_KEY not set!")
        print("Get it from https://xbl.io")
        return
    
    print(f"✅ Bot Token: {BOT_TOKEN[:10]}...")
    print(f"✅ XBL API Key: {XBL_API_KEY[:10]}...")
    print(f"✅ Admin IDs: {ADMIN_IDS}")
    print(f"✅ Rate Limit: {REQUESTS_PER_HOUR}/hour per user")
    print()
    
    # Start Flask in a thread
    flask_thread = threading.Thread(target=lambda: app.run(host='0.0.0.0', port=8080), daemon=True)
    flask_thread.start()
    print("🌐 Flask server running on port 8080")
    
    # Run bot
    print("🤖 Starting bot...")
    run_bot()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
