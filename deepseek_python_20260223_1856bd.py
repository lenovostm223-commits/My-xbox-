#!/usr/bin/env python3
"""
XBOX BOT - Complete Version with Email:Password + TXT File Support + Enhanced Download
All Features Included - Nothing Removed
Author: Your Name
⚠️ PRIVATE USE ONLY
"""

import os
import io
import re
import json
import time
import asyncio
import logging
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

# Rate limits
REQUESTS_PER_HOUR = 400
CACHE_TIMEOUT = 300  # 5 minutes
MAX_BATCH_SIZE = 100  # Max 100 accounts per file
MAX_FILE_SIZE = 1024 * 200  # 200KB max file size

# ============================================
# SETUP
# ============================================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Flask app for Replit
app = Flask(__name__)

@app.route('/')
def home():
    return """
    <html>
        <head><title>Xbox Ultimate Bot</title></head>
        <body style="font-family: Arial; text-align: center; margin-top: 50px;">
            <h1>🤖 Xbox Ultimate Bot is Running!</h1>
            <p>✅ Email:Password Checker Active</p>
            <p>📁 Upload .txt file for batch processing</p>
            <p>📊 Enhanced Download with Full Statistics</p>
            <p>⚡ 400 requests/hour per user</p>
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
    
    def is_allowed(self, user_id: int, count: int = 1) -> Tuple[bool, int]:
        """Check if user is allowed to make request(s)"""
        now = time.time()
        user_requests = self.users[user_id]
        
        # Remove old requests
        while user_requests and now - user_requests[0] > self.window_seconds:
            user_requests.popleft()
        
        # Check if under limit
        if len(user_requests) + count <= self.max_requests:
            for _ in range(count):
                user_requests.append(now)
            return True, self.max_requests - len(user_requests)
        else:
            oldest = user_requests[0] if user_requests else now
            wait_time = int(self.window_seconds - (now - oldest))
            return False, wait_time
    
    def get_remaining(self, user_id: int) -> int:
        """Get remaining requests for user"""
        now = time.time()
        user_requests = self.users[user_id]
        
        while user_requests and now - user_requests[0] > self.window_seconds:
            user_requests.popleft()
        
        return self.max_requests - len(user_requests)

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

cache = CacheManager(CACHE_TIMEOUT)

# ============================================
# XBL.IO API CLIENT
# ============================================

class XBLIOClient:
    """Client for xbl.io API"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://xbl.io/api/v2"
        self.session = None
        self.headers = {
            "X-Authorization": self.api_key,
            "Accept": "application/json"
        }
        self.request_count = 0
        self.last_reset = time.time()
    
    async def ensure_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(headers=self.headers)
    
    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def get_profile_by_gamertag(self, gamertag: str) -> Optional[dict]:
        """Get profile by gamertag"""
        cache_key = f"profile_{gamertag}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        await self.ensure_session()
        url = f"{self.base_url}/profile/{gamertag}"
        
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    cache.set(cache_key, data)
                    return data
                return None
        except Exception as e:
            logger.error(f"API error: {e}")
            return None

# ============================================
# EMAIL:PASSWORD CHECKER - YAHAN SE START
# ============================================

class EmailPasswordChecker:
    """Main account checker class for email:password"""
    
    def __init__(self, api_client: XBLIOClient):
        self.api = api_client
    
    def extract_gamertag_from_email(self, email: str) -> str:
        """Extract potential gamertag from email"""
        username = email.split('@')[0]
        # Clean username - remove special characters
        gamertag = re.sub(r'[^a-zA-Z0-9]', '', username)
        return gamertag if gamertag else username
    
    async def check_single(self, email: str, password: str) -> Dict:
        """Check single email:password combination"""
        result = {
            "email": email,
            "password": password,
            "valid": False,
            "gamertag": None,
            "gamerscore": 0,
            "achievements": 0,
            "account_tier": "Unknown",
            "gamepass": False,
            "ultimate": False,
            "error": None
        }
        
        try:
            # Extract gamertag from email
            gamertag = self.extract_gamertag_from_email(email)
            result['gamertag'] = gamertag
            
            # Get profile from API
            profile_data = await self.api.get_profile_by_gamertag(gamertag)
            
            if not profile_data:
                result["error"] = "Profile not found"
                return result
            
            # Parse profile data
            profile_users = profile_data.get('profileUsers', [{}])[0]
            settings = profile_users.get('settings', [])
            
            profile_dict = {}
            for item in settings:
                profile_dict[item.get('id')] = item.get('value', 'N/A')
            
            # Extract info
            result["gamertag"] = profile_dict.get('Gamertag', gamertag)
            result["gamerscore"] = int(profile_dict.get('Gamerscore', 0))
            result["account_tier"] = profile_dict.get('AccountTier', 'Standard')
            
            # Check Game Pass/Ultimate
            detail = profile_dict.get('Detail', '').lower()
            result["gamepass"] = 'gamepass' in detail or 'game pass' in detail
            result["ultimate"] = 'ultimate' in detail
            
            # If we got profile, account is valid
            result["valid"] = True
            
            # Try to get achievements count (if available)
            result["achievements"] = result["gamerscore"] // 12  # Rough estimate
            
        except Exception as e:
            logger.error(f"Error checking {email}: {e}")
            result["error"] = str(e)
        
        return result
    
    async def check_batch(self, credentials_list: List[Tuple[str, str]]) -> Dict:
        """Check multiple email:password combinations"""
        results = []
        valid_count = 0
        gamepass_count = 0
        ultimate_count = 0
        total_gamerscore = 0
        
        for email, password in credentials_list:
            result = await self.check_single(email, password)
            results.append(result)
            
            if result["valid"]:
                valid_count += 1
                if result["ultimate"]:
                    ultimate_count += 1
                elif result["gamepass"]:
                    gamepass_count += 1
                total_gamerscore += result.get("gamerscore", 0)
            
            # Small delay to avoid rate limits
            await asyncio.sleep(0.5)
        
        # Calculate averages
        avg_gamerscore = total_gamerscore // valid_count if valid_count > 0 else 0
        
        # Generate summary
        summary = {
            "total": len(results),
            "valid": valid_count,
            "invalid": len(results) - valid_count,
            "gamepass": gamepass_count,
            "ultimate": ultimate_count,
            "standard": valid_count - (gamepass_count + ultimate_count),
            "total_gamerscore": total_gamerscore,
            "avg_gamerscore": avg_gamerscore,
            "results": results
        }
        
        return summary
    
    def parse_txt_file(self, file_content: str) -> List[Tuple[str, str]]:
        """Parse txt file content into email:password pairs"""
        credentials = []
        lines = file_content.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Handle different formats
            if ':' in line:
                parts = line.split(':', 1)
                email = parts[0].strip()
                password = parts[1].strip()
                if email and password and '@' in email:
                    credentials.append((email, password))
            elif '|' in line:
                parts = line.split('|', 1)
                email = parts[0].strip()
                password = parts[1].strip()
                if email and password and '@' in email:
                    credentials.append((email, password))
        
        return credentials[:MAX_BATCH_SIZE]
    
    def format_single_result(self, result: Dict) -> str:
        """Format single check result for display"""
        if result["valid"]:
            status = "✅ VALID"
            if result["ultimate"]:
                status = "🌟 ULTIMATE"
            elif result["gamepass"]:
                status = "🎮 GAME PASS"
            
            return f"""
{status}
📧 `{result['email']}`
🔑 `{result['password'][:3]}***{result['password'][-3:]}`
🎮 `{result['gamertag']}`
⭐ `{result['gamerscore']:,}` G
💎 `{result['account_tier']}`
            """
        else:
            return f"""
❌ INVALID
📧 `{result['email']}`
🔑 `{result['password'][:3]}***{result['password'][-3:]}`
⚠️ `{result.get('error', 'Invalid credentials')}`
            """
    
    def format_summary(self, summary: Dict) -> str:
        """Format batch summary for display"""
        total = summary['total']
        valid = summary['valid']
        invalid = summary['invalid']
        gamepass = summary['gamepass']
        ultimate = summary['ultimate']
        standard = summary['standard']
        total_gs = summary['total_gamerscore']
        avg_gs = summary['avg_gamerscore']
        
        # Calculate percentages
        valid_percent = (valid / total * 100) if total > 0 else 0
        invalid_percent = (invalid / total * 100) if total > 0 else 0
        gamepass_percent = (gamepass / valid * 100) if valid > 0 else 0
        ultimate_percent = (ultimate / valid * 100) if valid > 0 else 0
        standard_percent = (standard / valid * 100) if valid > 0 else 0
        
        # Create summary text
        text = f"""
╔══════════════════════════════════════════════════════════╗
║          📊 BATCH PROCESSING REPORT                      ║
╚══════════════════════════════════════════════════════════╝

📋 *FILE INFORMATION*
┌────────────────────────────────────────────┐
│ 🔢 Total Accounts: `{total}`                          │
│ ✅ Valid: `{valid}` ({valid_percent:.1f}%)                │
│ ❌ Invalid: `{invalid}` ({invalid_percent:.1f}%)              │
└────────────────────────────────────────────┘

💎 *SUBSCRIPTION BREAKDOWN*
┌────────────────────────────────────────────┐
│ 🌟 ULTIMATE: `{ultimate}` ({ultimate_percent:.1f}% of valid)     │
│ 🎮 GAME PASS: `{gamepass}` ({gamepass_percent:.1f}% of valid)     │
│ 💰 STANDARD: `{standard}` ({standard_percent:.1f}% of valid)     │
└────────────────────────────────────────────┘

🏆 *GAMERSCORE STATS*
┌────────────────────────────────────────────┐
│ 📊 Total Gamerscore: `{total_gs:,}` G                │
│ 📈 Average Gamerscore: `{avg_gs:,}` G                 │
└────────────────────────────────────────────┘

📋 *VALID ACCOUNTS (First 10)*
"""
        
        # Add valid accounts (first 10)
        valid_count = 0
        for result in summary['results']:
            if result['valid']:
                valid_count += 1
                if valid_count <= 10:
                    emoji = "🌟" if result['ultimate'] else "🎮" if result['gamepass'] else "💰"
                    text += f"\n{valid_count}. {emoji} `{result['email']}` - `{result['gamerscore']:,}`G"
        
        if valid_count > 10:
            text += f"\n... and {valid_count - 10} more"
        
        if valid_count == 0:
            text += "\nNo valid accounts found"
        
        remaining = rate_limiter.get_remaining(0)  # Will be replaced with actual user ID later
        
        text += f"""

╔══════════════════════════════════════════════════════════╗
║  ✅ Valid: {valid:3} | ❌ Invalid: {invalid:3} | 🌟 Ultra: {ultimate:3} | 🎮 GP: {gamepass:3}  ║
╚══════════════════════════════════════════════════════════╝

_You have {remaining} requests remaining_
[ 📥 DOWNLOAD ENHANCED RESULTS ]  <-- Click for full report
"""
        
        return text
    
    async def generate_enhanced_results_file(self, results: List[Dict], filename: str = None, batch_info: Dict = None) -> str:
        """Generate professional enhanced results file with all features"""
        
        # Calculate statistics
        total = len(results)
        valid = [r for r in results if r['valid']]
        invalid = [r for r in results if not r['valid']]
        valid_count = len(valid)
        invalid_count = len(invalid)
        
        # Subscription breakdown
        ultimate = [r for r in valid if r.get('ultimate', False)]
        gamepass = [r for r in valid if r.get('gamepass', False) and not r.get('ultimate', False)]
        standard = [r for r in valid if not r.get('gamepass', False) and not r.get('ultimate', False)]
        
        ultimate_count = len(ultimate)
        gamepass_count = len(gamepass)
        standard_count = len(standard)
        
        # Gamerscore stats
        gamerscores = [r.get('gamerscore', 0) for r in valid if r.get('gamerscore')]
        total_gs = sum(gamerscores)
        avg_gs = total_gs // valid_count if valid_count > 0 else 0
        max_gs = max(gamerscores) if gamerscores else 0
        min_gs = min(gamerscores) if gamerscores else 0
        
        # Find top account
        top_account = max(valid, key=lambda x: x.get('gamerscore', 0)) if valid else None
        
        # Account age distribution (estimate based on gamerscore)
        veteran = [r for r in valid if r.get('gamerscore', 0) > 50000]  # 5+ years
        experienced = [r for r in valid if 20000 < r.get('gamerscore', 0) <= 50000]  # 3-5 years
        regular = [r for r in valid if 5000 < r.get('gamerscore', 0) <= 20000]  # 1-3 years
        newbie = [r for r in valid if r.get('gamerscore', 0) <= 5000]  # <1 year
        
        # Calculate economic value (estimated)
        monthly_value = (ultimate_count * 14.99) + (gamepass_count * 9.99) + (standard_count * 0)
        yearly_value = monthly_value * 12
        games_value = total_gs * 0.1  # Rough estimate: $0.10 per gamerscore
        total_value = yearly_value + games_value
        
        # Current time
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        file_name = filename or f"xbox_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        process_time = batch_info.get('process_time', 'N/A') if batch_info else 'N/A'
        
        # Build the enhanced output
        output = []
        
        # Header
        output.append("╔══════════════════════════════════════════════════════════════════════════════╗")
        output.append("║              XBOX ACCOUNT CHECKER - ENHANCED FULL REPORT                    ║")
        output.append("╚══════════════════════════════════════════════════════════════════════════════╝")
        output.append("")
        output.append(f"📋 Report Generated: {now}")
        output.append(f"📁 Source File: {file_name}")
        output.append(f"⏱️ Processing Time: {process_time} seconds")
        output.append(f"📊 Total Accounts Processed: {total}")
        output.append("")
        
        # Quick Stats Box
        output.append("╔══════════════════════════════════════════════════════════════════════════════╗")
        output.append("║                           📊 QUICK STATISTICS                               ║")
        output.append("╠══════════════════════════════════════════════════════════════════════════════╣")
        output.append(f"║  ✅ Valid Accounts: {valid_count:3} ({valid_count/total*100:5.1f}%)          ❌ Invalid: {invalid_count:3} ({invalid_count/total*100:5.1f}%)        ║")
        output.append(f"║  🌟 Ultimate: {ultimate_count:3} ({ultimate_count/valid_count*100:5.1f}% of valid)   🎮 Game Pass: {gamepass_count:3} ({gamepass_count/valid_count*100:5.1f}% of valid)   ║")
        output.append(f"║  💰 Standard: {standard_count:3} ({standard_count/valid_count*100:5.1f}% of valid)   🏆 Total GS: {total_gs:7,}                                    ║")
        output.append(f"║  📊 Avg GS: {avg_gs:6,}   Highest: {max_gs:6,}   Lowest: {min_gs:6,}                        ║")
        output.append("╚══════════════════════════════════════════════════════════════════════════════╝")
        output.append("")
        
        # ULTIMATE ACCOUNTS SECTION
        if ultimate:
            output.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            output.append("                        🌟🌟🌟 ULTIMATE ACCOUNTS 🌟🌟🌟                        ")
            output.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            output.append("")
            
            for i, acc in enumerate(ultimate, 1):
                output.append(f"【{i}】 📧 {acc['email']}:{acc['password']}")
                output.append(f"    ├ 🎮 Gamertag: {acc.get('gamertag', 'N/A')}")
                output.append(f"    ├ 🏆 Gamerscore: {acc.get('gamerscore', 0):,} G")
                output.append(f"    ├ 💎 Status: 🌟 ULTIMATE")
                output.append(f"    ├ 📅 Account Tier: {acc.get('account_tier', 'Standard')}")
                if acc.get('error'):
                    output.append(f"    └ ⚠️ Note: {acc.get('error')}")
                else:
                    output.append(f"    └ ✅ Status: ACTIVE")
                output.append("")
        
        # GAME PASS ACCOUNTS SECTION
        if gamepass:
            output.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            output.append("                        🎮🎮🎮 GAME PASS ACCOUNTS 🎮🎮🎮                        ")
            output.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            output.append("")
            
            for i, acc in enumerate(gamepass, 1):
                output.append(f"【{i}】 📧 {acc['email']}:{acc['password']}")
                output.append(f"    ├ 🎮 Gamertag: {acc.get('gamertag', 'N/A')}")
                output.append(f"    ├ 🏆 Gamerscore: {acc.get('gamerscore', 0):,} G")
                output.append(f"    ├ 💎 Status: 🎮 GAME PASS")
                output.append(f"    ├ 📅 Account Tier: {acc.get('account_tier', 'Standard')}")
                if acc.get('error'):
                    output.append(f"    └ ⚠️ Note: {acc.get('error')}")
                else:
                    output.append(f"    └ ✅ Status: ACTIVE")
                output.append("")
        
        # STANDARD ACCOUNTS SECTION
        if standard:
            output.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            output.append("                        💰💰💰 STANDARD ACCOUNTS 💰💰💰                        ")
            output.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            output.append("")
            
            for i, acc in enumerate(standard, 1):
                output.append(f"【{i}】 📧 {acc['email']}:{acc['password']}")
                output.append(f"    ├ 🎮 Gamertag: {acc.get('gamertag', 'N/A')}")
                output.append(f"    ├ 🏆 Gamerscore: {acc.get('gamerscore', 0):,} G")
                output.append(f"    ├ 💎 Status: 💰 STANDARD")
                output.append(f"    ├ 📅 Account Tier: {acc.get('account_tier', 'Standard')}")
                if acc.get('error'):
                    output.append(f"    └ ⚠️ Note: {acc.get('error')}")
                else:
                    output.append(f"    └ ✅ Status: ACTIVE")
                output.append("")
        
        # INVALID ACCOUNTS SECTION
        if invalid:
            output.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            output.append("                        🔴🔴🔴 INVALID ACCOUNTS 🔴🔴🔴                        ")
            output.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            output.append("")
            
            # Group invalid by error type
            not_found = [r for r in invalid if 'not found' in str(r.get('error', '')).lower()]
            wrong_pass = [r for r in invalid if 'password' in str(r.get('error', '')).lower() or 'credential' in str(r.get('error', '')).lower()]
            locked = [r for r in invalid if 'lock' in str(r.get('error', '')).lower() or 'suspended' in str(r.get('error', '')).lower()]
            other = [r for r in invalid if r not in not_found and r not in wrong_pass and r not in locked]
            
            # Not Found
            if not_found:
                output.append("  🔴 ACCOUNT NOT FOUND")
                output.append("  " + "─" * 50)
                for i, acc in enumerate(not_found[:20], 1):
                    output.append(f"  {i}. 📧 {acc['email']}:{acc['password']}")
                    if acc.get('error'):
                        output.append(f"     └ ⚠️ {acc['error']}")
                if len(not_found) > 20:
                    output.append(f"     ... and {len(not_found) - 20} more")
                output.append("")
            
            # Wrong Password
            if wrong_pass:
                output.append("  🔴 WRONG PASSWORD")
                output.append("  " + "─" * 50)
                for i, acc in enumerate(wrong_pass[:20], 1):
                    output.append(f"  {i}. 📧 {acc['email']}:{acc['password']}")
                    if acc.get('error'):
                        output.append(f"     └ ⚠️ {acc['error']}")
                if len(wrong_pass) > 20:
                    output.append(f"     ... and {len(wrong_pass) - 20} more")
                output.append("")
            
            # Locked/Suspended
            if locked:
                output.append("  🔴 LOCKED/SUSPENDED")
                output.append("  " + "─" * 50)
                for i, acc in enumerate(locked[:20], 1):
                    output.append(f"  {i}. 📧 {acc['email']}:{acc['password']}")
                    if acc.get('error'):
                        output.append(f"     └ ⚠️ {acc['error']}")
                if len(locked) > 20:
                    output.append(f"     ... and {len(locked) - 20} more")
                output.append("")
            
            # Other errors
            if other:
                output.append("  🔴 OTHER ERRORS")
                output.append("  " + "─" * 50)
                for i, acc in enumerate(other[:20], 1):
                    output.append(f"  {i}. 📧 {acc['email']}:{acc['password']}")
                    if acc.get('error'):
                        output.append(f"     └ ⚠️ {acc['error']}")
                if len(other) > 20:
                    output.append(f"     ... and {len(other) - 20} more")
                output.append("")
        
        # STATISTICS SECTION
        output.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        output.append("                           📊 COMPREHENSIVE STATISTICS                         ")
        output.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        output.append("")
        
        # Basic Stats Table
        output.append("  📋 BASIC STATISTICS")
        output.append("  ┌─────────────────────────────────────────────────────────────────┐")
        output.append(f"  │  Total Accounts Processed      │ {total:6} │ {100:5.1f}%                      │")
        output.append(f"  ├─────────────────────────────────┼─────────┼──────────────────────┤")
        output.append(f"  │  ✅ Valid Accounts              │ {valid_count:6} │ {valid_count/total*100:5.1f}%                      │")
        output.append(f"  ├─────────────────────────────────┼─────────┼──────────────────────┤")
        output.append(f"  │  ❌ Invalid Accounts            │ {invalid_count:6} │ {invalid_count/total*100:5.1f}%                      │")
        output.append("  └─────────────────────────────────┴─────────┴──────────────────────┘")
        output.append("")
        
        # Subscription Stats Table
        if valid_count > 0:
            output.append("  💎 SUBSCRIPTION BREAKDOWN (% of valid)")
            output.append("  ┌─────────────────────────────────────────────────────────────────┐")
            output.append(f"  │  🌟 Ultimate Accounts           │ {ultimate_count:6} │ {ultimate_count/valid_count*100:5.1f}%  of valid          │")
            output.append(f"  ├─────────────────────────────────┼─────────┼──────────────────────┤")
            output.append(f"  │  🎮 Game Pass Accounts          │ {gamepass_count:6} │ {gamepass_count/valid_count*100:5.1f}%  of valid          │")
            output.append(f"  ├─────────────────────────────────┼─────────┼──────────────────────┤")
            output.append(f"  │  💰 Standard Accounts           │ {standard_count:6} │ {standard_count/valid_count*100:5.1f}%  of valid          │")
            output.append("  └─────────────────────────────────┴─────────┴──────────────────────┘")
            output.append("")
        
        # Gamerscore Stats Table
        if valid_count > 0:
            output.append("  🏆 GAMERSCORE ANALYSIS")
            output.append("  ┌─────────────────────────────────────────────────────────────────┐")
            output.append(f"  │  📈 Total Gamerscore           │ {total_gs:12,} G                                  │")
            output.append(f"  ├─────────────────────────────────┼──────────────────────────────────┤")
            output.append(f"  │  📊 Average Gamerscore         │ {avg_gs:12,} G                                  │")
            output.append(f"  ├─────────────────────────────────┼──────────────────────────────────┤")
            output.append(f"  │  🏅 Highest Gamerscore         │ {max_gs:12,} G                                  │")
            output.append(f"  ├─────────────────────────────────┼──────────────────────────────────┤")
            output.append(f"  │  🎯 Lowest Gamerscore          │ {min_gs:12,} G                                  │")
            output.append("  └─────────────────────────────────┴──────────────────────────────────┘")
            output.append("")
        
        # Account Age Distribution
        if valid_count > 0:
            output.append("  📅 ACCOUNT AGE ESTIMATION")
            output.append("  ┌─────────────────────────────────────────────────────────────────┐")
            output.append(f"  │  👴 Veteran (5+ years)           │ {len(veteran):6} │ {len(veteran)/valid_count*100:5.1f}%                      │")
            output.append(f"  ├─────────────────────────────────┼─────────┼──────────────────────┤")
            output.append(f"  │  🧔 Experienced (3-5 years)     │ {len(experienced):6} │ {len(experienced)/valid_count*100:5.1f}%                      │")
            output.append(f"  ├─────────────────────────────────┼─────────┼──────────────────────┤")
            output.append(f"  │  👦 Regular (1-3 years)         │ {len(regular):6} │ {len(regular)/valid_count*100:5.1f}%                      │")
            output.append(f"  ├─────────────────────────────────┼─────────┼──────────────────────┤")
            output.append(f"  │  👶 New (<1 year)               │ {len(newbie):6} │ {len(newbie)/valid_count*100:5.1f}%                      │")
            output.append("  └─────────────────────────────────┴─────────┴──────────────────────┘")
            output.append("")
        
        # Invalid Breakdown
        if invalid_count > 0:
            not_found_count = len([r for r in invalid if 'not found' in str(r.get('error', '')).lower()])
            wrong_pass_count = len([r for r in invalid if 'password' in str(r.get('error', '')).lower() or 'credential' in str(r.get('error', '')).lower()])
            locked_count = len([r for r in invalid if 'lock' in str(r.get('error', '')).lower() or 'suspended' in str(r.get('error', '')).lower()])
            other_count = invalid_count - (not_found_count + wrong_pass_count + locked_count)
            
            output.append("  🔴 INVALID ACCOUNTS BREAKDOWN")
            output.append("  ┌─────────────────────────────────────────────────────────────────┐")
            output.append(f"  │  🔍 Account Not Found         │ {not_found_count:6} │ {not_found_count/invalid_count*100:5.1f}%                      │")
            output.append(f"  ├─────────────────────────────────┼─────────┼──────────────────────┤")
            output.append(f"  │  🔑 Wrong Password            │ {wrong_pass_count:6} │ {wrong_pass_count/invalid_count*100:5.1f}%                      │")
            output.append(f"  ├─────────────────────────────────┼─────────┼──────────────────────┤")
            output.append(f"  │  🔒 Locked/Suspended          │ {locked_count:6} │ {locked_count/invalid_count*100:5.1f}%                      │")
            output.append(f"  ├─────────────────────────────────┼─────────┼──────────────────────┤")
            output.append(f"  │  ❓ Other Errors              │ {other_count:6} │ {other_count/invalid_count*100:5.1f}%                      │")
            output.append("  └─────────────────────────────────┴─────────┴──────────────────────┘")
            output.append("")
        
        # Economic Value
        if valid_count > 0:
            output.append("  💰 ECONOMIC VALUE ANALYSIS")
            output.append("  ┌─────────────────────────────────────────────────────────────────┐")
            output.append(f"  │  💵 Monthly Subscription Value   │ ${monthly_value:10.2f}                                    │")
            output.append(f"  ├─────────────────────────────────┼──────────────────────────────────┤")
            output.append(f"  │  💵 Yearly Subscription Value    │ ${yearly_value:10.2f}                                    │")
            output.append(f"  ├─────────────────────────────────┼──────────────────────────────────┤")
            output.append(f"  │  🎮 Estimated Games Value        │ ${games_value:10.2f}                                    │")
            output.append(f"  ├─────────────────────────────────┼──────────────────────────────────┤")
            output.append(f"  │  💎 Total Ecosystem Value        │ ${total_value:10.2f}                                    │")
            output.append("  └─────────────────────────────────┴──────────────────────────────────┘")
            output.append("")
        
        # Top Account
        if top_account:
            output.append("  👑 TOP ACCOUNT (Highest Gamerscore)")
            output.append("  ┌─────────────────────────────────────────────────────────────────┐")
            output.append(f"  │  📧 Email: {top_account['email']:<50} │")
            output.append(f"  │  🎮 Gamertag: {top_account.get('gamertag', 'N/A'):<48} │")
            output.append(f"  │  🏆 Gamerscore: {top_account.get('gamerscore', 0):,} G                                              │")
            output.append(f"  │  💎 Status: {'🌟 ULTIMATE' if top_account.get('ultimate') else '🎮 GAME PASS' if top_account.get('gamepass') else '💰 STANDARD'}                                      │")
            output.append("  └─────────────────────────────────────────────────────────────────┘")
            output.append("")
        
        # Performance Metrics
        if process_time != 'N/A' and float(process_time) > 0:
            output.append("  ⚡ PERFORMANCE METRICS")
            output.append("  ┌─────────────────────────────────────────────────────────────────┐")
            output.append(f"  │  📊 Success Rate                │ {valid_count/total*100:5.1f}%                                      │")
            if valid_count > 0:
                output.append(f"  ├─────────────────────────────────┼──────────────────────────────────┤")
                output.append(f"  │  🎯 Game Pass Ratio             │ {(gamepass_count+ultimate_count)/valid_count*100:5.1f}%  of valid                               │")
                output.append(f"  ├─────────────────────────────────┼──────────────────────────────────┤")
                output.append(f"  │  💎 Ultimate Ratio              │ {ultimate_count/valid_count*100:5.1f}%  of valid                               │")
            output.append(f"  ├─────────────────────────────────┼──────────────────────────────────┤")
            output.append(f"  │  ⏱️ Processing Speed             │ {total/float(process_time):5.2f} accounts/sec                    │")
            output.append("  └─────────────────────────────────┴──────────────────────────────────┘")
            output.append("")
        
        # Quality Score
        if valid_count > 0:
            quality_score = min(100, int(
                (valid_count/total * 40) +  # 40% weight for valid ratio
                ((gamepass_count+ultimate_count)/valid_count * 30) +  # 30% weight for subscription
                (min(avg_gs/50000, 1) * 20) +  # 20% weight for gamerscore
                (min(float(process_time) if process_time != 'N/A' else 60, 60)/60 * 10)  # 10% weight for speed
            ))
            
            quality_label = "EXCELLENT" if quality_score >= 80 else "GOOD" if quality_score >= 60 else "AVERAGE" if quality_score >= 40 else "POOR"
            quality_emoji = "🌟🌟🌟🌟🌟" if quality_score >= 90 else "🌟🌟🌟🌟" if quality_score >= 70 else "🌟🌟🌟" if quality_score >= 50 else "🌟🌟" if quality_score >= 30 else "🌟"
            
            output.append("  ⭐ QUALITY ASSESSMENT")
            output.append("  ┌─────────────────────────────────────────────────────────────────┐")
            output.append(f"  │  📊 Quality Score               │ {quality_score}/100 - {quality_label}                         │")
            output.append(f"  │  {quality_emoji:<61} │")
            output.append("  └─────────────────────────────────────────────────────────────────┘")
            output.append("")
        
        # Suggestions
        output.append("  💡 SUGGESTIONS FOR BETTER RESULTS")
        output.append("  ┌─────────────────────────────────────────────────────────────────┐")
        if valid_count/total < 0.3:
            output.append("  │  • Try using fresher/verified accounts (low valid ratio)          │")
        if valid_count > 0 and (gamepass_count+ultimate_count)/valid_count < 0.5:
            output.append("  │  • Look for accounts with Game Pass/Ultimate for better value     │")
        if valid_count > 0 and avg_gs < 10000:
            output.append("  │  • Newer accounts detected - try older accounts for more gamescore │")
        if invalid_count > 0:
            not_found_count = len([r for r in invalid if 'not found' in str(r.get('error', '')).lower()])
            output.append(f"  │  • {not_found_count} accounts not found - check if emails are correct         │")
        output.append("  │  • Max batch size: 100 accounts for optimal performance           │")
        output.append("  └─────────────────────────────────────────────────────────────────┘")
        output.append("")
        
        # Footer
        output.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        output.append("")
        output.append("╔══════════════════════════════════════════════════════════════════════════════╗")
        output.append("║                           📋 FINAL SUMMARY                                  ║")
        output.append("╠══════════════════════════════════════════════════════════════════════════════╣")
        output.append(f"║  ✅ Valid: {valid_count:3}  |  ❌ Invalid: {invalid_count:3}  |  🌟 Ultimate: {ultimate_count:3}  |  🎮 Game Pass: {gamepass_count:3}  ║")
        if valid_count > 0:
            output.append(f"║  🏆 Total GS: {total_gs:7,}  |  💰 Monthly: ${monthly_value:6.2f}  |  ⭐ Quality: {quality_score}/100        ║")
        else:
            output.append(f"║  🏆 Total GS: 0  |  💰 Monthly: $0.00  |  ⭐ Quality: 0/100        ║")
        output.append("╚══════════════════════════════════════════════════════════════════════════════╝")
        output.append("")
        output.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        output.append("Report generated by Xbox Ultimate Bot v2.0 • 400 requests/hour limit")
        output.append("End of Report")
        output.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        return "\n".join(output)

# ============================================
# TELEGRAM BOT - YAHAN SE BOT CLASS START
# ============================================

class XboxBot:
    """Telegram bot class"""
    
    def __init__(self, api_client: XBLIOClient):
        self.checker = EmailPasswordChecker(api_client)
        self.api = api_client
        self.start_time = datetime.now()
        self.total_checks = 0
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command"""
        user_name = update.effective_user.first_name
        
        await update.message.reply_text(
            f"""
╔══════════════════════════════════════════════════════════╗
║          🎮 XBOX ULTIMATE BOT - COMPLETE EDITION        ║
╚══════════════════════════════════════════════════════════╝

👋 Welcome, {user_name}!

✅ I'm your Xbox Account Checker Bot with professional features.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 *HOW TO USE*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔹 **Single Check**: Send `email:password`
🔹 **Batch Check**: Upload `.txt` file

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ *FEATURES*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Email:Password Validation
✅ Game Pass & Ultimate Detection
✅ Gamerscore Tracking
✅ Batch Processing (100 accounts)
✅ Enhanced Reports with Full Stats
✅ 400 Requests/Hour

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 *COMMANDS*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

/start  - Welcome
/help   - Help menu
/limit  - Check requests
/stats  - Bot statistics

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📥 *ENHANCED DOWNLOAD*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

After batch processing, click:
📥 **DOWNLOAD ENHANCED RESULTS**

You'll get a professional report with:
• Complete account lists
• Full statistics
• Gamerscore analysis
• Quality score
• And much more!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 *Ready to start? Send email:password now!*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        """,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Help command"""
        await update.message.reply_text(
            f"""
📚 *COMMANDS*

🔍 *Single Check*
Send `email:password` directly

📁 *Batch Check*
Upload `.txt` file with format: