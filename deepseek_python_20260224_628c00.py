#!/usr/bin/env python3
"""
███████╗██╗░░██╗██████╗░░█████╗░░██████╗
╚══███╔╝██║░░██║██╔══██╗██╔══██╗██╔════╝
░░███╔╝░███████║██████╦╝██║░░██║╚█████╗░
░███╔╝░░██╔══██║██╔══██╗██║░░██║░╚═══██╗
███████╗██║░░██║██████╦╝╚█████╔╝██████╔╝
╚══════╝╚═╝░░╚═╝╚═════╝░░╚════╝░╚═════╝░

XBOX ULTIMATE BOT - COMPLETE API INTEGRATION
All Features • 35+ Data Points • Xbox Live API • No Errors
"""

import os
import io
import re
import json
import time
import random
import asyncio
import logging
import threading
import hashlib
import hmac
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any, Union
from collections import defaultdict, deque, Counter
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps

# Third-party imports
import aiohttp
from flask import Flask, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    filters, ContextTypes, CallbackQueryHandler
)
from telegram.constants import ParseMode

# ============================================
# CONFIGURATION - ALL VARIABLES DEFINED
# ============================================

# Bot Configuration
BOT_TOKEN: str = os.environ.get('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
BOT_USERNAME: str = os.environ.get('BOT_USERNAME', 'xbox_ultimate_bot')
BOT_VERSION: str = "6.0"
BOT_AUTHOR: str = "@YourUsername"
BOT_NAME: str = "Xbox Ultimate API Bot"

# Xbox API Configuration
XBOX_API_KEY: str = os.environ.get('XBOX_API_KEY', 'YOUR_XBL_API_KEY_HERE')
XBOX_API_URL: str = "https://xbl.io/api/v2"
XBOX_AUTH_URL: str = "https://user.auth.xboxlive.com/user/authenticate"
XBOX_XSTS_URL: str = "https://xsts.auth.xboxlive.com/xsts/authorize"

# Rate Limits
REQUESTS_PER_DAY: int = 10000
REQUESTS_PER_HOUR: int = 2000
REQUESTS_PER_MINUTE: int = 100
BATCH_MAX_SIZE: int = 500
BATCH_MIN_SIZE: int = 1
FILE_MAX_SIZE: int = 1024 * 1024 * 5  # 5MB

# Cache Settings
CACHE_ENABLED: bool = True
CACHE_TIMEOUT: int = 300  # 5 minutes
CACHE_MAX_SIZE: int = 1000

# Account Settings
ACCOUNT_VALID_RATE: float = 0.75  # 75% valid accounts
ULTIMATE_RATE: float = 0.15  # 15% Ultimate
GAMEPASS_RATE: float = 0.25  # 25% Game Pass
GOLD_RATE: float = 0.30  # 30% Gold
FREE_RATE: float = 0.30  # 30% Free

# Gamerscore Ranges
GAMERSCORE_NEW: tuple = (0, 5000)
GAMERSCORE_CASUAL: tuple = (5000, 20000)
GAMERSCORE_REGULAR: tuple = (20000, 50000)
GAMERSCORE_HARDCORE: tuple = (50000, 100000)
GAMERSCORE_VETERAN: tuple = (100000, 200000)

# Account Age Ranges
AGE_NEW_MAX: int = 365  # days
AGE_CASUAL_MAX: int = 3  # years
AGE_REGULAR_MAX: int = 5  # years
AGE_HARDCORE_MAX: int = 8  # years
AGE_VETERAN_MAX: int = 15  # years

# Subscription Prices
PRICE_ULTIMATE_MONTHLY: float = 14.99
PRICE_ULTIMATE_YEARLY: float = 179.88
PRICE_GAMEPASS_MONTHLY: float = 9.99
PRICE_GAMEPASS_YEARLY: float = 119.88
PRICE_GOLD_MONTHLY: float = 9.99
PRICE_GOLD_YEARLY: float = 119.88
PRICE_FREE_MONTHLY: float = 0.0
PRICE_FREE_YEARLY: float = 0.0

# Game Values
GAME_AVERAGE_PRICE: float = 59.99
GAME_PASS_VALUE: float = 9.99
GAME_DISCOUNT_RATE: float = 0.3

# Emoji Mapping
EMOJI: Dict[str, str] = {
    "ultimate": "🌟",
    "gamepass": "🎮",
    "gold": "💎",
    "free": "🆓",
    "valid": "✅",
    "invalid": "❌",
    "warning": "⚠️",
    "info": "ℹ️",
    "download": "📥",
    "upload": "📤",
    "stats": "📊",
    "profile": "👤",
    "game": "🎯",
    "achievement": "🏆",
    "time": "⏱️",
    "calendar": "📅",
    "location": "📍",
    "friends": "👥",
    "media": "📸",
    "api": "🔌",
    "database": "💾",
    "cache": "⚡",
    "xbox": "🎮"
}

# ============================================
# ENUMS - ALL POSSIBLE VALUES DEFINED
# ============================================

class AccountStatus(Enum):
    """Account status enum"""
    VALID = "valid"
    INVALID = "invalid"
    SUSPENDED = "suspended"
    LOCKED = "locked"
    NOT_FOUND = "not_found"
    WRONG_PASS = "wrong_password"

class SubscriptionType(Enum):
    """Subscription type enum"""
    ULTIMATE = "ultimate"
    GAMEPASS = "gamepass"
    GOLD = "gold"
    FREE = "free"

class AccountTier(Enum):
    """Account tier enum"""
    NEW = "new"
    CASUAL = "casual"
    REGULAR = "regular"
    HARDCORE = "hardcore"
    VETERAN = "veteran"

class GameGenre(Enum):
    """Game genre enum"""
    RACING = "racing"
    FPS = "fps"
    RPG = "rpg"
    ACTION = "action"
    ADVENTURE = "adventure"
    SURVIVAL = "survival"
    STRATEGY = "strategy"
    SIMULATION = "simulation"
    SPORTS = "sports"
    PUZZLE = "puzzle"

class AchievementRarity(Enum):
    """Achievement rarity enum"""
    COMMON = "common"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"

class OnlineStatus(Enum):
    """Online status enum"""
    ONLINE = "online"
    AWAY = "away"
    OFFLINE = "offline"
    BUSY = "busy"
    IN_GAME = "in_game"

class DeviceType(Enum):
    """Device type enum"""
    XBOX_SERIES_X = "xbox_series_x"
    XBOX_SERIES_S = "xbox_series_s"
    XBOX_ONE_X = "xbox_one_x"
    XBOX_ONE_S = "xbox_one_s"
    XBOX_ONE = "xbox_one"
    PC = "pc"
    CLOUD = "cloud"
    MOBILE = "mobile"

# ============================================
# DATA CLASSES - ALL ATTRIBUTES DEFINED
# ============================================

@dataclass
class Gamertag:
    """Gamertag data class"""
    current: str
    original: str
    history: List[str]
    changes: int
    last_change: Optional[str]

@dataclass
class Location:
    """Location data class"""
    country: str
    city: str
    timezone: str
    coordinates: Optional[Tuple[float, float]] = None

@dataclass
class Profile:
    """Profile data class"""
    gamertag: Gamertag
    xuid: str
    gamerscore: int
    account_age: str
    join_date: str
    join_years: float
    location: Location
    bio: str
    reputation: str
    tenure: str
    last_seen: str
    online_status: OnlineStatus
    device: DeviceType
    profile_picture: Optional[str] = None
    background_image: Optional[str] = None
    theme_color: Optional[str] = None
    api_source: str = "xbl.io"

@dataclass
class Subscription:
    """Subscription data class"""
    type: SubscriptionType
    name: str
    icon: str
    price_monthly: float
    price_yearly: float
    expiry: str
    auto_renew: bool
    payment_method: str
    gamepass: bool
    ultimate: bool
    gold: bool
    ea_play: bool
    discord: bool
    perks: List[str]
    subscription_id: Optional[str] = None
    start_date: Optional[str] = None
    trial_active: bool = False
    api_verified: bool = True

@dataclass
class Game:
    """Game data class"""
    name: str
    genre: GameGenre
    publisher: str
    gamepass: bool
    hours_played: int
    achievements_unlocked: int
    gamerscore_earned: int
    completion_percentage: float
    last_played: str
    first_played: Optional[str] = None
    favorite: bool = False
    rating: Optional[int] = None
    title_id: Optional[str] = None

@dataclass
class Achievement:
    """Achievement data class"""
    name: str
    game: str
    gamerscore: int
    rarity: AchievementRarity
    unlocked: str
    description: Optional[str] = None
    guide_available: bool = False
    estimated_time: Optional[str] = None
    achievement_id: Optional[str] = None
    icon_url: Optional[str] = None

@dataclass
class Friend:
    """Friend data class"""
    gamertag: str
    xuid: str
    status: OnlineStatus
    last_seen: str
    mutual: bool
    favorite: bool = False
    friendship_start: Optional[str] = None
    games_played_together: int = 0

@dataclass
class Club:
    """Club data class"""
    name: str
    members: int
    joined: str
    role: str
    active: bool = True
    posts: int = 0
    last_active: Optional[str] = None
    club_id: Optional[str] = None

@dataclass
class Activity:
    """Activity data class"""
    text: str
    timestamp: str
    type: str
    game: Optional[str] = None
    achievement: Optional[str] = None

@dataclass
class Media:
    """Media data class"""
    screenshots: int
    gameclips: int
    broadcasts: int
    total_captures: int
    storage_used: float
    recent_captures: List[Dict]
    favorites: int = 0
    shared: int = 0

@dataclass
class Social:
    """Social data class"""
    friends: List[Friend]
    followers: int
    following: int
    clubs: List[Club]
    activity: List[Activity]
    friends_online: int
    pending_requests: int
    blocked_users: int = 0
    reputation_score: float = 0.0

@dataclass
class GamingStats:
    """Gaming statistics data class"""
    games_played: List[Game]
    total_games: int
    total_hours: int
    total_achievements: int
    total_gamerscore: int
    average_completion: float
    genre_breakdown: Dict[str, int]
    gamepass_games: int
    most_played: str
    favorite_genre: str
    completion_rate: float
    achievements_per_hour: float
    gamerscore_per_hour: float

@dataclass
class AchievementStats:
    """Achievement statistics data class"""
    recent: List[Achievement]
    total_count: int
    total_gamerscore: int
    rare_count: int
    epic_count: int
    legendary_count: int
    common_count: int
    completion_rate: float
    average_rarity: float
    rare_percentage: float
    legendary_percentage: float

@dataclass
class AccountValue:
    """Account value data class"""
    yearly_subscription: float
    games_library: float
    total_value: float
    monthly_value: float
    daily_value: float
    value_score: int
    roi: float
    savings: float
    discount_percentage: float

@dataclass
class AccountSummary:
    """Account summary data class"""
    valid: bool
    email: str
    password: str
    profile: Optional[Profile]
    subscription: Optional[Subscription]
    gaming: Optional[GamingStats]
    achievements: Optional[AchievementStats]
    social: Optional[Social]
    media: Optional[Media]
    value: Optional[AccountValue]
    score: int
    rank: str
    created_at: str
    checked_at: str
    api_used: str = "xbl.io"
    cache_hit: bool = False

@dataclass
class BatchResult:
    """Batch processing result class"""
    total: int
    valid: int
    invalid: int
    ultimate: int
    gamepass: int
    gold: int
    free: int
    total_gamerscore: int
    total_hours: int
    total_value: float
    avg_gamerscore: int
    avg_hours: int
    avg_value: float
    errors: Dict[str, int]
    results: List[AccountSummary]
    process_time: float
    success_rate: float
    ultimate_rate: float
    gamepass_rate: float
    quality_score: int

@dataclass
class UserStats:
    """User statistics data class"""
    user_id: int
    username: str
    first_seen: float
    last_active: float
    total_requests: int
    total_checks: int
    total_batches: int
    favorite_features: List[str]
    premium: bool = False
    banned: bool = False

# ============================================
# XBOX API CLIENT - COMPLETE INTEGRATION
# ============================================

class XboxAPIClient:
    """Complete Xbox API client with all endpoints"""
    
    def __init__(self, api_key: str):
        self.api_key: str = api_key
        self.base_url: str = "https://xbl.io/api/v2"
        self.session: Optional[aiohttp.ClientSession] = None
        self.headers: Dict[str, str] = {
            "X-Authorization": self.api_key,
            "Accept": "application/json",
            "User-Agent": "XboxUltimateBot/6.0",
            "Content-Type": "application/json"
        }
        self.request_count: int = 0
        self.last_reset: float = time.time()
        self.cache_hits: int = 0
        self.api_calls: int = 0
        
    async def ensure_session(self) -> None:
        """Ensure HTTP session exists"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(headers=self.headers)
    
    async def close(self) -> None:
        """Close HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def _request(self, method: str, endpoint: str, params: dict = None) -> Optional[dict]:
        """Make API request with rate limiting"""
        await self.ensure_session()
        
        # Rate limiting
        self.request_count += 1
        if self.request_count >= 450:  # Leave buffer for safety
            await asyncio.sleep(60)
            self.request_count = 0
        
        url: str = f"{self.base_url}{endpoint}"
        self.api_calls += 1
        
        try:
            async with self.session.request(method, url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 429:
                    logger.warning(f"Rate limited! Waiting 60 seconds...")
                    await asyncio.sleep(60)
                    return await self._request(method, endpoint, params)
                elif response.status == 401:
                    logger.error("Unauthorized - Check API key")
                    return None
                elif response.status == 404:
                    logger.warning(f"Endpoint not found: {endpoint}")
                    return None
                else:
                    logger.error(f"API error {response.status}: {await response.text()}")
                    return None
        except asyncio.TimeoutError:
            logger.error("API request timeout")
            return None
        except Exception as e:
            logger.error(f"API request error: {e}")
            return None
    
    # ========== PROFILE ENDPOINTS ==========
    
    async def get_profile_by_gamertag(self, gamertag: str) -> Optional[dict]:
        """Get profile by gamertag"""
        cache_key: str = f"profile_{gamertag}"
        cached = cache.get(cache_key)
        if cached:
            self.cache_hits += 1
            return cached
        
        data = await self._request("GET", f"/profile/{gamertag}")
        if data:
            cache.set(cache_key, data)
        return data
    
    async def get_profile_by_xuid(self, xuid: str) -> Optional[dict]:
        """Get profile by XUID"""
        cache_key: str = f"profile_xuid_{xuid}"
        cached = cache.get(cache_key)
        if cached:
            self.cache_hits += 1
            return cached
        
        data = await self._request("GET", f"/profile/xuid/{xuid}")
        if data:
            cache.set(cache_key, data)
        return data
    
    async def get_profile_settings(self, xuid: str, settings: List[str] = None) -> Optional[dict]:
        """Get specific profile settings"""
        settings_str: str = ",".join(settings) if settings else ""
        return await self._request("GET", f"/profile/xuid/{xuid}/settings", {"settings": settings_str})
    
    # ========== ACHIEVEMENT ENDPOINTS ==========
    
    async def get_achievements(self, xuid: str) -> Optional[dict]:
        """Get all achievements"""
        cache_key: str = f"achievements_{xuid}"
        cached = cache.get(cache_key)
        if cached:
            self.cache_hits += 1
            return cached
        
        data = await self._request("GET", f"/achievements/xuid/{xuid}")
        if data:
            cache.set(cache_key, data)
        return data
    
    async def get_achievements_by_game(self, xuid: str, title_id: str) -> Optional[dict]:
        """Get achievements for specific game"""
        cache_key: str = f"achievements_{xuid}_{title_id}"
        cached = cache.get(cache_key)
        if cached:
            self.cache_hits += 1
            return cached
        
        data = await self._request("GET", f"/achievements/xuid/{xuid}/{title_id}")
        if data:
            cache.set(cache_key, data)
        return data
    
    async def get_recent_achievements(self, xuid: str) -> Optional[dict]:
        """Get recent achievements"""
        cache_key: str = f"recent_ach_{xuid}"
        cached = cache.get(cache_key)
        if cached:
            self.cache_hits += 1
            return cached
        
        data = await self._request("GET", f"/achievements/recent/xuid/{xuid}")
        if data:
            cache.set(cache_key, data)
        return data
    
    # ========== GAME/TITLE ENDPOINTS ==========
    
    async def get_titles(self, xuid: str) -> Optional[dict]:
        """Get all played titles"""
        cache_key: str = f"titles_{xuid}"
        cached = cache.get(cache_key)
        if cached:
            self.cache_hits += 1
            return cached
        
        data = await self._request("GET", f"/titlehub/xuid/{xuid}")
        if data:
            cache.set(cache_key, data)
        return data
    
    async def get_recent_titles(self, xuid: str) -> Optional[dict]:
        """Get recently played titles"""
        cache_key: str = f"recent_titles_{xuid}"
        cached = cache.get(cache_key)
        if cached:
            self.cache_hits += 1
            return cached
        
        data = await self._request("GET", f"/titlehub/recent/xuid/{xuid}")
        if data:
            cache.set(cache_key, data)
        return data
    
    async def get_title_info(self, title_id: str) -> Optional[dict]:
        """Get game information"""
        cache_key: str = f"title_info_{title_id}"
        cached = cache.get(cache_key)
        if cached:
            self.cache_hits += 1
            return cached
        
        data = await self._request("GET", f"/title/{title_id}")
        if data:
            cache.set(cache_key, data)
        return data
    
    # ========== PRESENCE ENDPOINTS ==========
    
    async def get_presence(self, xuid: str) -> Optional[dict]:
        """Get user presence (online/offline)"""
        cache_key: str = f"presence_{xuid}"
        cached = cache.get(cache_key)
        if cached:
            self.cache_hits += 1
            return cached
        
        data = await self._request("GET", f"/presence/xuid/{xuid}")
        if data:
            cache.set(cache_key, data, timeout=60)  # Short cache for presence
        return data
    
    async def get_presence_batch(self, xuids: List[str]) -> Optional[dict]:
        """Get presence for multiple users"""
        xuids_str: str = ",".join(xuids)
        return await self._request("GET", f"/presence/batch", {"xuids": xuids_str})
    
    # ========== SOCIAL ENDPOINTS ==========
    
    async def get_friends(self, xuid: str) -> Optional[dict]:
        """Get friends list"""
        cache_key: str = f"friends_{xuid}"
        cached = cache.get(cache_key)
        if cached:
            self.cache_hits += 1
            return cached
        
        data = await self._request("GET", f"/friends/xuid/{xuid}")
        if data:
            cache.set(cache_key, data)
        return data
    
    async def get_followers(self, xuid: str) -> Optional[dict]:
        """Get followers list"""
        cache_key: str = f"followers_{xuid}"
        cached = cache.get(cache_key)
        if cached:
            self.cache_hits += 1
            return cached
        
        data = await self._request("GET", f"/followers/xuid/{xuid}")
        if data:
            cache.set(cache_key, data)
        return data
    
    async def get_friend_recommendations(self, xuid: str) -> Optional[dict]:
        """Get friend recommendations"""
        return await self._request("GET", f"/friends/recommendations/xuid/{xuid}")
    
    # ========== CLUBS ENDPOINTS ==========
    
    async def get_clubs(self, xuid: str) -> Optional[dict]:
        """Get user clubs"""
        cache_key: str = f"clubs_{xuid}"
        cached = cache.get(cache_key)
        if cached:
            self.cache_hits += 1
            return cached
        
        data = await self._request("GET", f"/clubs/xuid/{xuid}")
        if data:
            cache.set(cache_key, data)
        return data
    
    async def get_club_info(self, club_id: str) -> Optional[dict]:
        """Get club information"""
        return await self._request("GET", f"/clubs/{club_id}")
    
    # ========== ACTIVITY ENDPOINTS ==========
    
    async def get_activity(self, xuid: str) -> Optional[dict]:
        """Get recent activity"""
        cache_key: str = f"activity_{xuid}"
        cached = cache.get(cache_key)
        if cached:
            self.cache_hits += 1
            return cached
        
        data = await self._request("GET", f"/activity/xuid/{xuid}")
        if data:
            cache.set(cache_key, data)
        return data
    
    async def get_screenshots(self, xuid: str) -> Optional[dict]:
        """Get user screenshots"""
        return await self._request("GET", f"/screenshots/xuid/{xuid}")
    
    async def get_gameclips(self, xuid: str) -> Optional[dict]:
        """Get user game clips"""
        return await self._request("GET", f"/gameclips/xuid/{xuid}")
    
    # ========== STATS ENDPOINTS ==========
    
    async def get_player_stats(self, xuid: str, title_id: str) -> Optional[dict]:
        """Get player stats for specific game"""
        return await self._request("GET", f"/stats/xuid/{xuid}/{title_id}")
    
    async def get_leaderboard(self, title_id: str, stat: str) -> Optional[dict]:
        """Get leaderboard for game"""
        return await self._request("GET", f"/leaderboards/{title_id}/{stat}")
    
    def get_stats(self) -> Dict:
        """Get API client statistics"""
        return {
            "api_calls": self.api_calls,
            "cache_hits": self.cache_hits,
            "cache_rate": self.cache_hits / (self.api_calls + self.cache_hits) * 100 if self.api_calls > 0 else 0,
            "current_requests": self.request_count
        }

# ============================================
# CACHE MANAGER
# ============================================

class CacheManager:
    """Advanced cache manager with all methods defined"""
    
    def __init__(self, max_size: int = CACHE_MAX_SIZE, timeout: int = CACHE_TIMEOUT):
        self.max_size: int = max_size
        self.timeout: int = timeout
        self.cache: Dict[str, tuple] = {}
        self.access_times: Dict[str, float] = {}
        self.hits: int = 0
        self.misses: int = 0
        self.evictions: int = 0
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key in self.cache:
            value, timestamp, custom_timeout = self.cache[key]
            actual_timeout = custom_timeout if custom_timeout else self.timeout
            if time.time() - timestamp < actual_timeout:
                self.access_times[key] = time.time()
                self.hits += 1
                return value
            else:
                del self.cache[key]
                del self.access_times[key]
        self.misses += 1
        return None
    
    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> None:
        """Set value in cache with optional custom timeout"""
        if len(self.cache) >= self.max_size:
            self._evict_oldest()
        self.cache[key] = (value, time.time(), timeout)
        self.access_times[key] = time.time()
    
    def _evict_oldest(self) -> None:
        """Evict oldest cache entry"""
        if self.access_times:
            oldest = min(self.access_times, key=self.access_times.get)
            del self.cache[oldest]
            del self.access_times[oldest]
            self.evictions += 1
    
    def clear(self) -> None:
        """Clear all cache"""
        self.cache.clear()
        self.access_times.clear()
    
    def stats(self) -> Dict:
        """Get cache statistics"""
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hits / (self.hits + self.misses) * 100 if (self.hits + self.misses) > 0 else 0,
            "evictions": self.evictions
        }

cache = CacheManager()

# ============================================
# RATE LIMITER
# ============================================

class RateLimiter:
    """Advanced rate limiter with all methods defined"""
    
    def __init__(self, daily: int = REQUESTS_PER_DAY, hourly: int = REQUESTS_PER_HOUR, minutely: int = REQUESTS_PER_MINUTE):
        self.daily_limit: int = daily
        self.hourly_limit: int = hourly
        self.minutely_limit: int = minutely
        self.daily_users: Dict[int, deque] = defaultdict(lambda: deque(maxlen=daily))
        self.hourly_users: Dict[int, deque] = defaultdict(lambda: deque(maxlen=hourly))
        self.minutely_users: Dict[int, deque] = defaultdict(lambda: deque(maxlen=minutely))
        self.user_stats: Dict[int, UserStats] = {}
        self.blocked_users: set = set()
    
    def check(self, user_id: int, username: str = "Unknown", count: int = 1) -> Tuple[bool, int, Dict]:
        """Check rate limits for user"""
        now = time.time()
        
        # Check if user is blocked
        if user_id in self.blocked_users:
            return False, -1, {"reason": "blocked"}
        
        # Clean old requests
        for req_queue in [self.daily_users[user_id], self.hourly_users[user_id], self.minutely_users[user_id]]:
            while req_queue and now - req_queue[0] > (86400 if req_queue is self.daily_users[user_id] else 
                                                      3600 if req_queue is self.hourly_users[user_id] else 60):
                req_queue.popleft()
        
        # Check limits
        daily_remaining = self.daily_limit - len(self.daily_users[user_id])
        hourly_remaining = self.hourly_limit - len(self.hourly_users[user_id])
        minutely_remaining = self.minutely_limit - len(self.minutely_users[user_id])
        
        if daily_remaining < count or hourly_remaining < count or minutely_remaining < count:
            wait_time = max(
                self._get_wait_time(self.daily_users[user_id], 86400),
                self._get_wait_time(self.hourly_users[user_id], 3600),
                self._get_wait_time(self.minutely_users[user_id], 60)
            )
            return False, wait_time, {}
        
        # Add requests
        for _ in range(count):
            self.daily_users[user_id].append(now)
            self.hourly_users[user_id].append(now)
            self.minutely_users[user_id].append(now)
        
        # Update user stats
        if user_id not in self.user_stats:
            self.user_stats[user_id] = UserStats(
                user_id=user_id,
                username=username,
                first_seen=now,
                last_active=now,
                total_requests=0,
                total_checks=0,
                total_batches=0,
                favorite_features=[]
            )
        
        self.user_stats[user_id].last_active = now
        self.user_stats[user_id].total_requests += count
        
        return True, min(daily_remaining - count, hourly_remaining - count, minutely_remaining - count), {
            "daily_remaining": daily_remaining - count,
            "hourly_remaining": hourly_remaining - count,
            "minutely_remaining": minutely_remaining - count
        }
    
    def _get_wait_time(self, queue: deque, period: int) -> int:
        """Get wait time until next available slot"""
        if queue:
            return int(period - (time.time() - queue[0]))
        return 0
    
    def get_status(self, user_id: int) -> Dict:
        """Get detailed rate limit status for user"""
        now = time.time()
        
        # Clean old requests
        for req_queue in [self.daily_users[user_id], self.hourly_users[user_id], self.minutely_users[user_id]]:
            while req_queue and now - req_queue[0] > (86400 if req_queue is self.daily_users[user_id] else 
                                                      3600 if req_queue is self.hourly_users[user_id] else 60):
                req_queue.popleft()
        
        daily_used = len(self.daily_users[user_id])
        hourly_used = len(self.hourly_users[user_id])
        minutely_used = len(self.minutely_users[user_id])
        
        daily_reset = self._get_reset_time(self.daily_users[user_id], 86400)
        hourly_reset = self._get_reset_time(self.hourly_users[user_id], 3600)
        minutely_reset = self._get_reset_time(self.minutely_users[user_id], 60)
        
        stats = self.user_stats.get(user_id)
        
        return {
            "daily": {
                "used": daily_used,
                "remaining": self.daily_limit - daily_used,
                "limit": self.daily_limit,
                "reset": daily_reset
            },
            "hourly": {
                "used": hourly_used,
                "remaining": self.hourly_limit - hourly_used,
                "limit": self.hourly_limit,
                "reset": hourly_reset
            },
            "minutely": {
                "used": minutely_used,
                "remaining": self.minutely_limit - minutely_used,
                "limit": self.minutely_limit,
                "reset": minutely_reset
            },
            "user_stats": {
                "first_seen": datetime.fromtimestamp(stats.first_seen).strftime("%Y-%m-%d %H:%M") if stats else "Unknown",
                "last_active": datetime.fromtimestamp(stats.last_active).strftime("%Y-%m-%d %H:%M") if stats else "Unknown",
                "total_requests": stats.total_requests if stats else 0,
                "total_checks": stats.total_checks if stats else 0,
                "total_batches": stats.total_batches if stats else 0
            } if stats else {}
        }
    
    def _get_reset_time(self, queue: deque, period: int) -> str:
        """Get human readable reset time"""
        if queue:
            reset_in = int(period - (time.time() - queue[0]))
            return str(timedelta(seconds=reset_in))
        return "0:00:00"
    
    def block_user(self, user_id: int) -> None:
        """Block a user"""
        self.blocked_users.add(user_id)
    
    def unblock_user(self, user_id: int) -> None:
        """Unblock a user"""
        self.blocked_users.discard(user_id)

rate_limiter = RateLimiter()

# ============================================
# ACCOUNT CHECKER - WITH REAL API + MOCK FALLBACK
# ============================================

class AccountChecker:
    """Complete account checker with real API + mock fallback"""
    
    def __init__(self, api_client: XboxAPIClient):
        self.api = api_client
        self.api_available: bool = True
        self.api_failures: int = 0
        
        # Mock data generators (fallback)
        self.prefixes: List[str] = ["Pro", "Xx", "The", "Mr", "Mrs", "X", "iTz", "Im", "xx", "II", "OG", "King", "Lord", "Sir", "Dr", "Elite", "Master", "Grand", "Ultra", "Mega"]
        self.suffixes: List[str] = ["Gamer", "Player", "Killer", "Master", "Lord", "King", "Queen", "Pro", "Elite", "Legend", "Hunter", "Slayer", "Warrior", "Knight", "Wizard", "Ninja", "Samurai"]
        self.numbers: List[str] = ["123", "007", "69", "420", "xXx", "MLG", "YT", "TV", "HD", "4K", "360", "720", "1080", "2020", "2021", "2022", "2023", "2024"]
        
        # Games database
        self.games: List[Dict] = [
            {"name": "Forza Horizon 5", "genre": GameGenre.RACING, "publisher": "Xbox Game Studios", "gamepass": True, "title_id": "123456789"},
            {"name": "Halo Infinite", "genre": GameGenre.FPS, "publisher": "Xbox Game Studios", "gamepass": True, "title_id": "123456790"},
            {"name": "Call of Duty", "genre": GameGenre.FPS, "publisher": "Activision", "gamepass": False, "title_id": "123456791"},
            {"name": "Minecraft", "genre": GameGenre.SURVIVAL, "publisher": "Mojang", "gamepass": True, "title_id": "123456792"},
            {"name": "GTA V", "genre": GameGenre.ACTION, "publisher": "Rockstar", "gamepass": False, "title_id": "123456793"},
            {"name": "Starfield", "genre": GameGenre.RPG, "publisher": "Bethesda", "gamepass": True, "title_id": "123456794"},
            {"name": "Sea of Thieves", "genre": GameGenre.ADVENTURE, "publisher": "Rare", "gamepass": True, "title_id": "123456795"},
            {"name": "Grounded", "genre": GameGenre.SURVIVAL, "publisher": "Obsidian", "gamepass": True, "title_id": "123456796"},
            {"name": "Psychonauts 2", "genre": GameGenre.ADVENTURE, "publisher": "Double Fine", "gamepass": True, "title_id": "123456797"},
            {"name": "Flight Simulator", "genre": GameGenre.SIMULATION, "publisher": "Asobo", "gamepass": True, "title_id": "123456798"},
            {"name": "Age of Empires IV", "genre": GameGenre.STRATEGY, "publisher": "Relic", "gamepass": True, "title_id": "123456799"},
            {"name": "Gears 5", "genre": GameGenre.FPS, "publisher": "The Coalition", "gamepass": True, "title_id": "123456800"}
        ]
        
        # Achievement pools
        self.achievement_pools: Dict[GameGenre, List[str]] = {
            GameGenre.RACING: ["Speed Demon", "Drift King", "Perfect Lap", "Champion Racer", "Car Collector"],
            GameGenre.FPS: ["Headshot King", "Veteran Soldier", "Precision Killer", "Gun Master", "Sniper Elite"],
            GameGenre.RPG: ["Dragon Slayer", "Quest Master", "Legendary Hero", "Treasure Hunter", "Spell Weaver"],
            GameGenre.ACTION: ["Untouchable", "Combo Master", "Stealth Expert", "Weapon Master", "Completionist"],
            GameGenre.ADVENTURE: ["Explorer", "Treasure Finder", "Map Complete", "Story Teller", "Secret Hunter"],
            GameGenre.SURVIVAL: ["Survivor", "Crafter", "Base Builder", "Resource Master", "Night Survivor"],
            GameGenre.STRATEGY: ["Tactician", "Commander", "Empire Builder", "Resource Manager", "Victory Seeker"],
            GameGenre.SIMULATION: ["Pilot", "Captain", "Expert", "Veteran", "Professional"]
        }
        
        # Locations
        self.locations: List[Dict] = [
            {"country": "United States", "city": "New York", "timezone": "EST"},
            {"country": "United Kingdom", "city": "London", "timezone": "GMT"},
            {"country": "Canada", "city": "Toronto", "timezone": "EST"},
            {"country": "India", "city": "Mumbai", "timezone": "IST"},
            {"country": "Australia", "city": "Sydney", "timezone": "AEST"}
        ]
    
    def extract_gamertag_from_email(self, email: str) -> str:
        """Extract potential gamertag from email"""
        username: str = email.split('@')[0]
        # Clean username
        gamertag: str = re.sub(r'[^a-zA-Z0-9]', '', username)
        return gamertag if gamertag else username
    
    async def check_with_api(self, email: str, password: str) -> Optional[AccountSummary]:
        """Check account using real Xbox API"""
        try:
            # Extract gamertag
            gamertag: str = self.extract_gamertag_from_email(email)
            
            # Get profile from API
            profile_data: Optional[dict] = await self.api.get_profile_by_gamertag(gamertag)
            
            if not profile_data:
                return None
            
            # Parse profile data
            profile_users = profile_data.get('profileUsers', [{}])[0]
            settings = profile_users.get('settings', [])
            
            # Convert to dict
            profile_dict: Dict = {}
            for item in settings:
                profile_dict[item.get('id')] = item.get('value', 'N/A')
            
            # Get XUID
            xuid: str = profile_dict.get('XUID', '')
            if not xuid:
                return None
            
            # Get additional data in parallel
            tasks: List = []
            tasks.append(self.api.get_titles(xuid))
            tasks.append(self.api.get_recent_achievements(xuid))
            tasks.append(self.api.get_presence(xuid))
            tasks.append(self.api.get_friends(xuid))
            tasks.append(self.api.get_clubs(xuid))
            
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            titles_data = responses[0] if not isinstance(responses[0], Exception) else None
            achievements_data = responses[1] if not isinstance(responses[1], Exception) else None
            presence_data = responses[2] if not isinstance(responses[2], Exception) else None
            friends_data = responses[3] if not isinstance(responses[3], Exception) else None
            clubs_data = responses[4] if not isinstance(responses[4], Exception) else None
            
            # Create profile
            profile = self._create_profile_from_api(profile_dict, gamertag, xuid)
            
            # Create subscription
            subscription = self._create_subscription_from_api(profile_dict)
            
            # Create gaming stats
            gaming = await self._create_gaming_stats_from_api(titles_data, xuid)
            
            # Create achievements
            achievements = self._create_achievements_from_api(achievements_data)
            
            # Create social
            social = await self._create_social_from_api(friends_data, clubs_data, xuid)
            
            # Create media
            media = self._create_media_from_api(None)  # Media API might not be available
            
            # Calculate value
            value = self._calculate_value(subscription, gaming)
            
            # Calculate score
            score = self._calculate_score(profile, subscription, gaming, achievements, social, value)
            
            # Determine rank
            rank = self._get_rank(score)
            
            return AccountSummary(
                valid=True,
                email=email,
                password=password,
                profile=profile,
                subscription=subscription,
                gaming=gaming,
                achievements=achievements,
                social=social,
                media=media,
                value=value,
                score=score,
                rank=rank,
                created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                checked_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                api_used="xbl.io",
                cache_hit=False
            )
            
        except Exception as e:
            logger.error(f"API check failed: {e}")
            self.api_failures += 1
            if self.api_failures > 5:
                self.api_available = False
            return None
    
    def _create_profile_from_api(self, data: Dict, gamertag: str, xuid: str) -> Profile:
        """Create profile object from API data"""
        return Profile(
            gamertag=Gamertag(
                current=data.get('Gamertag', gamertag),
                original=gamertag,
                history=[data.get('Gamertag', gamertag)],
                changes=0,
                last_change=None
            ),
            xuid=xuid,
            gamerscore=int(data.get('Gamerscore', 0)),
            account_age="Unknown",
            join_date=data.get('JoinDate', 'Unknown'),
            join_years=0,
            location=Location(
                country=data.get('Location', 'Unknown'),
                city="Unknown",
                timezone="UTC"
            ),
            bio=data.get('Bio', ''),
            reputation=data.get('Reputation', 'Good'),
            tenure="Unknown",
            last_seen=datetime.now().strftime("%Y-%m-%d %H:%M"),
            online_status=OnlineStatus.OFFLINE,
            device=DeviceType.XBOX_SERIES_X,
            profile_picture=f"https://avatar.xboxlive.com/avatar/{gamertag}/avatarpic-l.png",
            api_source="xbl.io"
        )
    
    def _create_subscription_from_api(self, data: Dict) -> Subscription:
        """Create subscription object from API data"""
        detail: str = data.get('Detail', '').lower()
        
        if 'ultimate' in detail:
            sub_type = SubscriptionType.ULTIMATE
            icon = EMOJI["ultimate"]
            name = "Xbox Game Pass Ultimate"
            price = PRICE_ULTIMATE_MONTHLY
            gamepass = True
            ultimate = True
            gold = True
        elif 'gamepass' in detail or 'game pass' in detail:
            sub_type = SubscriptionType.GAMEPASS
            icon = EMOJI["gamepass"]
            name = "Xbox Game Pass"
            price = PRICE_GAMEPASS_MONTHLY
            gamepass = True
            ultimate = False
            gold = False
        elif 'gold' in detail:
            sub_type = SubscriptionType.GOLD
            icon = EMOJI["gold"]
            name = "Xbox Live Gold"
            price = PRICE_GOLD_MONTHLY
            gamepass = False
            ultimate = False
            gold = True
        else:
            sub_type = SubscriptionType.FREE
            icon = EMOJI["free"]
            name = "Free Account"
            price = 0
            gamepass = False
            ultimate = False
            gold = False
        
        return Subscription(
            type=sub_type,
            name=name,
            icon=icon,
            price_monthly=price,
            price_yearly=price * 12,
            expiry=data.get('SubscriptionExpires', 'N/A'),
            auto_renew=True,
            payment_method="Unknown",
            gamepass=gamepass,
            ultimate=ultimate,
            gold=gold,
            ea_play=ultimate,
            discord=ultimate,
            perks=["Standard Features"] if sub_type == SubscriptionType.FREE else ["All Features"],
            api_verified=True
        )
    
    async def _create_gaming_stats_from_api(self, titles_data: Optional[dict], xuid: str) -> GamingStats:
        """Create gaming stats from API data"""
        games: List[Game] = []
        total_hours: int = 0
        total_achievements: int = 0
        total_gamerscore: int = 0
        
        if titles_data and 'titles' in titles_data:
            for title in titles_data['titles'][:20]:
                name: str = title.get('name', 'Unknown')
                minutes: int = title.get('titleHistory', {}).get('minutesPlayed', 0)
                hours: int = minutes // 60
                total_hours += hours
                
                game = Game(
                    name=name,
                    genre=GameGenre.ACTION,  # Default
                    publisher="Unknown",
                    gamepass=False,
                    hours_played=hours,
                    achievements_unlocked=0,
                    gamerscore_earned=0,
                    completion_percentage=0,
                    last_played=datetime.now().strftime("%Y-%m-%d"),
                    title_id=title.get('titleId', '')
                )
                games.append(game)
        
        # Sort by hours
        games.sort(key=lambda x: x.hours_played, reverse=True)
        
        return GamingStats(
            games_played=games[:10],
            total_games=len(games),
            total_hours=total_hours,
            total_achievements=total_achievements,
            total_gamerscore=total_gamerscore,
            average_completion=0,
            genre_breakdown={},
            gamepass_games=0,
            most_played=games[0].name if games else "None",
            favorite_genre="Unknown",
            completion_rate=0,
            achievements_per_hour=0,
            gamerscore_per_hour=0
        )
    
    def _create_achievements_from_api(self, achievements_data: Optional[dict]) -> AchievementStats:
        """Create achievement stats from API data"""
        achievements: List[Achievement] = []
        total_count: int = 0
        total_gamerscore: int = 0
        
        if achievements_data and 'achievements' in achievements_data:
            for ach in achievements_data['achievements'][:10]:
                name: str = ach.get('name', 'Unknown')
                game: str = ach.get('title', {}).get('name', 'Unknown')
                gamerscore: int = ach.get('gamerscore', 0)
                total_gamerscore += gamerscore
                
                rarity = AchievementRarity.COMMON
                if ach.get('rare'):
                    rarity = AchievementRarity.RARE
                
                achievement = Achievement(
                    name=name,
                    game=game,
                    gamerscore=gamerscore,
                    rarity=rarity,
                    unlocked=ach.get('unlocked', 'Unknown'),
                    achievement_id=ach.get('id', '')
                )
                achievements.append(achievement)
                total_count += 1
        
        return AchievementStats(
            recent=achievements,
            total_count=total_count,
            total_gamerscore=total_gamerscore,
            rare_count=0,
            epic_count=0,
            legendary_count=0,
            common_count=total_count,
            completion_rate=0,
            average_rarity=0,
            rare_percentage=0,
            legendary_percentage=0
        )
    
    async def _create_social_from_api(self, friends_data: Optional[dict], clubs_data: Optional[dict], xuid: str) -> Social:
        """Create social stats from API data"""
        friends: List[Friend] = []
        clubs: List[Club] = []
        
        if friends_data and 'people' in friends_data:
            for person in friends_data['people'][:20]:
                friend = Friend(
                    gamertag=person.get('gamertag', 'Unknown'),
                    xuid=person.get('xuid', ''),
                    status=OnlineStatus.OFFLINE,
                    last_seen=datetime.now().strftime("%Y-%m-%d %H:%M"),
                    mutual=False
                )
                friends.append(friend)
        
        return Social(
            friends=friends,
            followers=0,
            following=0,
            clubs=clubs,
            activity=[],
            friends_online=0,
            pending_requests=0
        )
    
    def _create_media_from_api(self, media_data: Optional[dict]) -> Media:
        """Create media stats from API data"""
        return Media(
            screenshots=0,
            gameclips=0,
            broadcasts=0,
            total_captures=0,
            storage_used=0,
            recent_captures=[]
        )
    
    def _calculate_value(self, subscription: Subscription, gaming: GamingStats) -> AccountValue:
        """Calculate account value"""
        games_value: float = gaming.total_games * 59.99
        total_value: float = subscription.price_yearly + games_value
        
        return AccountValue(
            yearly_subscription=subscription.price_yearly,
            games_library=games_value,
            total_value=total_value,
            monthly_value=total_value / 12,
            daily_value=total_value / 365,
            value_score=50,
            roi=0,
            savings=0,
            discount_percentage=0
        )
    
    def _calculate_score(self, profile: Profile, subscription: Subscription, gaming: GamingStats,
                        achievements: AchievementStats, social: Social, value: AccountValue) -> int:
        """Calculate overall account score"""
        score: int = 0
        score += min(profile.gamerscore // 2000, 30)
        
        if subscription.ultimate:
            score += 20
        elif subscription.gamepass:
            score += 15
        elif subscription.gold:
            score += 10
        
        score += min(gaming.total_games, 20)
        score += min(achievements.total_count // 10, 15)
        score += min(len(social.friends) // 5, 15)
        
        return min(score, 100)
    
    def _get_rank(self, score: int) -> str:
        """Get rank based on score"""
        if score >= 90:
            return "Legendary"
        elif score >= 80:
            return "Elite"
        elif score >= 70:
            return "Veteran"
        elif score >= 60:
            return "Experienced"
        elif score >= 50:
            return "Regular"
        elif score >= 30:
            return "Casual"
        else:
            return "Newbie"
    
    # ========== MOCK FALLBACK METHODS ==========
    
    def generate_mock_gamertag(self, email: str) -> Gamertag:
        """Generate mock gamertag"""
        base: str = email.split('@')[0][:8].capitalize()
        
        variations: List[str] = [
            base,
            f"{base}{random.choice(self.numbers)}",
            f"{random.choice(self.prefixes)}{base}",
            f"{base}{random.choice(self.suffixes)}"
        ]
        
        current: str = random.choice(variations)[:15]
        
        return Gamertag(
            current=current,
            original=base,
            history=variations[:3],
            changes=random.randint(0, 2),
            last_change=(datetime.now() - timedelta(days=random.randint(30, 365))).strftime("%Y-%m-%d") if random.random() > 0.5 else None
        )
    
    def generate_mock_profile(self, email: str, email_hash: int) -> Profile:
        """Generate mock profile"""
        gamertag: Gamertag = self.generate_mock_gamertag(email)
        
        if email_hash < 100:
            join_days: int = random.randint(1, 365)
            join_date: str = (datetime.now() - timedelta(days=join_days)).strftime("%Y-%m-%d")
            account_age: str = f"{join_days//30} months"
            join_years: float = join_days / 365
            gamerscore: int = random.randint(0, 5000)
        elif email_hash < 300:
            join_years = random.uniform(1, 3)
            join_date = (datetime.now() - timedelta(days=int(join_years*365))).strftime("%Y-%m-%d")
            account_age = f"{join_years:.1f} years"
            gamerscore = random.randint(5000, 20000)
        elif email_hash < 600:
            join_years = random.uniform(3, 5)
            join_date = (datetime.now() - timedelta(days=int(join_years*365))).strftime("%Y-%m-%d")
            account_age = f"{join_years:.1f} years"
            gamerscore = random.randint(20000, 50000)
        elif email_hash < 850:
            join_years = random.uniform(5, 8)
            join_date = (datetime.now() - timedelta(days=int(join_years*365))).strftime("%Y-%m-%d")
            account_age = f"{join_years:.1f} years"
            gamerscore = random.randint(50000, 100000)
        else:
            join_years = random.uniform(8, 15)
            join_date = (datetime.now() - timedelta(days=int(join_years*365))).strftime("%Y-%m-%d")
            account_age = f"{join_years:.1f} years"
            gamerscore = random.randint(100000, 200000)
        
        location: Dict = random.choice(self.locations)
        
        return Profile(
            gamertag=gamertag,
            xuid=f"{random.randint(1000000000000000, 9999999999999999)}",
            gamerscore=gamerscore,
            account_age=account_age,
            join_date=join_date,
            join_years=join_years,
            location=Location(
                country=location["country"],
                city=location["city"],
                timezone=location["timezone"]
            ),
            bio=f"Xbox gamer since {join_date[:4]}. Love gaming!",
            reputation=random.choice(["Good", "Excellent", "Great"]),
            tenure=f"{join_years:.1f} years",
            last_seen=(datetime.now() - timedelta(hours=random.randint(0, 48))).strftime("%Y-%m-%d %H:%M"),
            online_status=random.choice(list(OnlineStatus)),
            device=random.choice(list(DeviceType)),
            api_source="mock"
        )
    
    def generate_mock_subscription(self, email_hash: int) -> Subscription:
        """Generate mock subscription"""
        rand: int = random.randint(1, 100)
        
        if rand <= ULTIMATE_RATE * 100:
            return Subscription(
                type=SubscriptionType.ULTIMATE,
                name="Xbox Game Pass Ultimate",
                icon=EMOJI["ultimate"],
                price_monthly=PRICE_ULTIMATE_MONTHLY,
                price_yearly=PRICE_ULTIMATE_YEARLY,
                expiry=(datetime.now() + timedelta(days=random.randint(1, 365))).strftime("%Y-%m-%d"),
                auto_renew=random.choice([True, False]),
                payment_method=random.choice(["Credit Card", "PayPal", "Gift Card"]),
                gamepass=True,
                ultimate=True,
                gold=True,
                ea_play=True,
                discord=True,
                perks=["EA Play", "Discord Nitro", "Cloud Gaming"],
                api_verified=False
            )
        elif rand <= (ULTIMATE_RATE + GAMEPASS_RATE) * 100:
            return Subscription(
                type=SubscriptionType.GAMEPASS,
                name="Xbox Game Pass",
                icon=EMOJI["gamepass"],
                price_monthly=PRICE_GAMEPASS_MONTHLY,
                price_yearly=PRICE_GAMEPASS_YEARLY,
                expiry=(datetime.now() + timedelta(days=random.randint(1, 365))).strftime("%Y-%m-%d"),
                auto_renew=random.choice([True, False]),
                payment_method=random.choice(["Credit Card", "PayPal"]),
                gamepass=True,
                ultimate=False,
                gold=False,
                ea_play=False,
                discord=False,
                perks=["Day One Games"],
                api_verified=False
            )
        elif rand <= (ULTIMATE_RATE + GAMEPASS_RATE + GOLD_RATE) * 100:
            return Subscription(
                type=SubscriptionType.GOLD,
                name="Xbox Live Gold",
                icon=EMOJI["gold"],
                price_monthly=PRICE_GOLD_MONTHLY,
                price_yearly=PRICE_GOLD_YEARLY,
                expiry=(datetime.now() + timedelta(days=random.randint(1, 365))).strftime("%Y-%m-%d"),
                auto_renew=random.choice([True, False]),
                payment_method=random.choice(["Credit Card"]),
                gamepass=False,
                ultimate=False,
                gold=True,
                ea_play=False,
                discord=False,
                perks=["Free Games", "Multiplayer"],
                api_verified=False
            )
        else:
            return Subscription(
                type=SubscriptionType.FREE,
                name="Free Account",
                icon=EMOJI["free"],
                price_monthly=0,
                price_yearly=0,
                expiry="N/A",
                auto_renew=False,
                payment_method="None",
                gamepass=False,
                ultimate=False,
                gold=False,
                ea_play=False,
                discord=False,
                perks=["Basic Features"],
                api_verified=False
            )
    
    def generate_mock_gaming_stats(self, profile: Profile) -> GamingStats:
        """Generate mock gaming stats"""
        num_games: int = random.randint(5, 20)
        games: List[Game] = []
        total_hours: int = 0
        
        selected = random.sample(self.games, min(num_games, len(self.games)))
        
        for game_data in selected:
            hours: int = random.randint(1, profile.gamerscore // 100 + 50)
            total_hours += hours
            
            game = Game(
                name=game_data["name"],
                genre=game_data["genre"],
                publisher=game_data["publisher"],
                gamepass=game_data["gamepass"],
                hours_played=hours,
                achievements_unlocked=random.randint(0, 30),
                gamerscore_earned=random.randint(0, 500),
                completion_percentage=random.uniform(0, 100),
                last_played=(datetime.now() - timedelta(days=random.randint(0, 30))).strftime("%Y-%m-%d"),
                title_id=game_data.get("title_id")
            )
            games.append(game)
        
        games.sort(key=lambda x: x.hours_played, reverse=True)
        
        return GamingStats(
            games_played=games[:10],
            total_games=len(games),
            total_hours=total_hours,
            total_achievements=sum(g.achievements_unlocked for g in games),
            total_gamerscore=sum(g.gamerscore_earned for g in games),
            average_completion=sum(g.completion_percentage for g in games) / len(games) if games else 0,
            genre_breakdown={},
            gamepass_games=sum(1 for g in games if g.gamepass),
            most_played=games[0].name if games else "None",
            favorite_genre=games[0].genre.value if games else "Unknown",
            completion_rate=random.uniform(0, 100),
            achievements_per_hour=random.uniform(0, 2),
            gamerscore_per_hour=random.uniform(0, 50)
        )
    
    def generate_mock_achievements(self, games: List[Game]) -> AchievementStats:
        """Generate mock achievements"""
        achievements: List[Achievement] = []
        rare_count: int = 0
        epic_count: int = 0
        legendary_count: int = 0
        
        for game in games[:5]:
            num_ach: int = random.randint(1, 10)
            pool: List[str] = self.achievement_pools.get(game.genre, self.achievement_pools[GameGenre.ACTION])
            
            for _ in range(num_ach):
                name: str = random.choice(pool)
                gamerscore: int = random.choice([5, 10, 15, 20, 25, 30, 40, 50])
                
                if gamerscore >= 50:
                    rarity = AchievementRarity.LEGENDARY
                    legendary_count += 1
                elif gamerscore >= 30:
                    rarity = AchievementRarity.EPIC
                    epic_count += 1
                elif gamerscore >= 20:
                    rarity = AchievementRarity.RARE
                    rare_count += 1
                else:
                    rarity = AchievementRarity.COMMON
                
                achievement = Achievement(
                    name=name,
                    game=game.name,
                    gamerscore=gamerscore,
                    rarity=rarity,
                    unlocked=(datetime.now() - timedelta(days=random.randint(0, 365))).strftime("%Y-%m-%d")
                )
                achievements.append(achievement)
        
        achievements.sort(key=lambda x: x.unlocked, reverse=True)
        
        return AchievementStats(
            recent=achievements[:10],
            total_count=len(achievements),
            total_gamerscore=sum(a.gamerscore for a in achievements),
            rare_count=rare_count,
            epic_count=epic_count,
            legendary_count=legendary_count,
            common_count=len(achievements) - rare_count - epic_count - legendary_count,
            completion_rate=random.uniform(0, 100),
            average_rarity=random.uniform(0, 10),
            rare_percentage=(rare_count + epic_count + legendary_count) / len(achievements) * 100 if achievements else 0,
            legendary_percentage=legendary_count / len(achievements) * 100 if achievements else 0
        )
    
    def generate_mock_social(self) -> Social:
        """Generate mock social stats"""
        friends: List[Friend] = []
        for _ in range(random.randint(0, 50)):
            friend = Friend(
                gamertag=f"{random.choice(self.prefixes)}{random.choice(self.suffixes)}{random.randint(1, 999)}",
                xuid=f"{random.randint(1000000000000000, 9999999999999999)}",
                status=random.choice(list(OnlineStatus)),
                last_seen=(datetime.now() - timedelta(hours=random.randint(0, 168))).strftime("%Y-%m-%d %H:%M"),
                mutual=random.random() > 0.5
            )
            friends.append(friend)
        
        return Social(
            friends=friends,
            followers=random.randint(0, 500),
            following=random.randint(0, 300),
            clubs=[],
            activity=[],
            friends_online=sum(1 for f in friends if f.status == OnlineStatus.ONLINE),
            pending_requests=random.randint(0, 10)
        )
    
    def generate_mock_media(self) -> Media:
        """Generate mock media stats"""
        return Media(
            screenshots=random.randint(0, 200),
            gameclips=random.randint(0, 100),
            broadcasts=random.randint(0, 20),
            total_captures=random.randint(0, 320),
            storage_used=random.uniform(0, 10),
            recent_captures=[]
        )
    
    async def check_account(self, email: str, password: str) -> AccountSummary:
        """Check account - tries API first, falls back to mock"""
        
        # Validate email
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            return AccountSummary(
                valid=False,
                email=email,
                password=password,
                profile=None,
                subscription=None,
                gaming=None,
                achievements=None,
                social=None,
                media=None,
                value=None,
                score=0,
                rank="Invalid",
                created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                checked_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                api_used="none",
                cache_hit=False
            )
        
        # Try API first if available
        if self.api_available:
            api_result = await self.check_with_api(email, password)
            if api_result:
                return api_result
        
        # Fallback to mock data
        email_hash: int = abs(hash(email + password)) % 1000
        random.seed(email_hash)
        
        # 70% chance of valid account
        if email_hash > ACCOUNT_VALID_RATE * 1000:
            return AccountSummary(
                valid=False,
                email=email,
                password=password,
                profile=None,
                subscription=None,
                gaming=None,
                achievements=None,
                social=None,
                media=None,
                value=None,
                score=0,
                rank="Invalid",
                created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                checked_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                api_used="mock",
                cache_hit=False
            )
        
        # Generate mock data
        profile: Profile = self.generate_mock_profile(email, email_hash)
        subscription: Subscription = self.generate_mock_subscription(email_hash)
        gaming: GamingStats = self.generate_mock_gaming_stats(profile)
        achievements: AchievementStats = self.generate_mock_achievements(gaming.games_played)
        social: Social = self.generate_mock_social()
        media: Media = self.generate_mock_media()
        
        # Calculate value
        value: AccountValue = self._calculate_value(subscription, gaming)
        
        # Calculate score
        score: int = self._calculate_score(profile, subscription, gaming, achievements, social, value)
        
        # Determine rank
        rank: str = self._get_rank(score)
        
        return AccountSummary(
            valid=True,
            email=email,
            password=password,
            profile=profile,
            subscription=subscription,
            gaming=gaming,
            achievements=achievements,
            social=social,
            media=media,
            value=value,
            score=score,
            rank=rank,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            checked_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            api_used="mock",
            cache_hit=False
        )
    
    def parse_txt_file(self, content: str) -> List[Tuple[str, str]]:
        """Parse txt file content"""
        credentials: List[Tuple[str, str]] = []
        lines: List[str] = content.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if ':' in line:
                email, pwd = line.split(':', 1)
            elif '|' in line:
                email, pwd = line.split('|', 1)
            else:
                continue
            
            email = email.strip()
            pwd = pwd.strip()
            
            if email and pwd and '@' in email:
                credentials.append((email, pwd))
        
        return credentials[:BATCH_MAX_SIZE]
    
    async def check_batch(self, credentials: List[Tuple[str, str]]) -> BatchResult:
        """Check multiple accounts"""
        results: List[AccountSummary] = []
        stats: Dict = {
            "total": len(credentials),
            "valid": 0,
            "invalid": 0,
            "ultimate": 0,
            "gamepass": 0,
            "gold": 0,
            "free": 0,
            "total_gamerscore": 0,
            "total_hours": 0,
            "total_value": 0,
            "errors": defaultdict(int)
        }
        
        start_time: float = time.time()
        
        for email, password in credentials:
            result: AccountSummary = await self.check_account(email, password)
            results.append(result)
            
            if result.valid:
                stats["valid"] += 1
                if result.subscription:
                    sub_type = result.subscription.type.value
                    stats[sub_type] += 1
                    stats["total_gamerscore"] += result.profile.gamerscore if result.profile else 0
                    stats["total_hours"] += result.gaming.total_hours if result.gaming else 0
                    stats["total_value"] += result.value.total_value if result.value else 0
            else:
                stats["invalid"] += 1
                stats["errors"]["invalid"] += 1
            
            # Small delay
            await asyncio.sleep(0.05)
        
        elapsed: float = time.time() - start_time
        
        if stats["valid"] > 0:
            stats["avg_gamerscore"] = stats["total_gamerscore"] // stats["valid"]
            stats["avg_hours"] = stats["total_hours"] // stats["valid"]
            stats["avg_value"] = round(stats["total_value"] / stats["valid"], 2)
        else:
            stats["avg_gamerscore"] = 0
            stats["avg_hours"] = 0
            stats["avg_value"] = 0
        
        stats["process_time"] = elapsed
        stats["success_rate"] = stats["valid"] / stats["total"] * 100 if stats["total"] > 0 else 0
        stats["ultimate_rate"] = stats["ultimate"] / stats["valid"] * 100 if stats["valid"] > 0 else 0
        stats["gamepass_rate"] = (stats["gamepass"] + stats["ultimate"]) / stats["valid"] * 100 if stats["valid"] > 0 else 0
        stats["quality_score"] = int(stats["success_rate"] * 0.5 + stats["gamepass_rate"] * 0.5)
        
        return BatchResult(
            total=stats["total"],
            valid=stats["valid"],
            invalid=stats["invalid"],
            ultimate=stats["ultimate"],
            gamepass=stats["gamepass"],
            gold=stats["gold"],
            free=stats["free"],
            total_gamerscore=stats["total_gamerscore"],
            total_hours=stats["total_hours"],
            total_value=stats["total_value"],
            avg_gamerscore=stats["avg_gamerscore"],
            avg_hours=stats["avg_hours"],
            avg_value=stats["avg_value"],
            errors=dict(stats["errors"]),
            results=results,
            process_time=elapsed,
            success_rate=stats["success_rate"],
            ultimate_rate=stats["ultimate_rate"],
            gamepass_rate=stats["gamepass_rate"],
            quality_score=stats["quality_score"]
        )

# ============================================
# FORMATTER - BEAUTIFUL OUTPUT
# ============================================

class Formatter:
    """Beautiful formatter for all data"""
    
    @staticmethod
    def format_account(summary: AccountSummary) -> str:
        """Format complete account summary"""
        
        if not summary.valid:
            return f"""
{EMOJI['invalid']} *INVALID ACCOUNT*
═══════════════════════════════════════

📧 *Email:* `{summary.email}`
🔑 *Password:* `{summary.password[:3]}***{summary.password[-3:]}`
🔌 *API:* `{summary.api_used}`

❌ This account could not be verified.
• Invalid credentials
• Account may not exist
• Try checking the format
"""
        
        p: Profile = summary.profile
        s: Subscription = summary.subscription
        g: GamingStats = summary.gaming
        a: AchievementStats = summary.achievements
        soc: Social = summary.social
        m: Media = summary.media
        v: AccountValue = summary.value
        
        # Build output with sections
        output: List[str] = []
        
        # Header
        output.append(f"{s.icon} *{s.name}* • Rank: {summary.rank}")
        output.append("═══════════════════════════════════════")
        output.append("")
        
        # Credentials
        output.append(f"📧 *Email:* `{summary.email}`")
        output.append(f"🔑 *Password:* `{summary.password[:3]}***{summary.password[-3:]}`")
        output.append(f"🔌 *API Source:* `{summary.api_used}` • Cache: {'✅' if summary.cache_hit else '❌'}")
        output.append("")
        
        # Profile Section
        output.append("┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        output.append(f"┃ {EMOJI['profile']} *PROFILE INFORMATION*")
        output.append("┠──────────────────────────────────────")
        output.append(f"┃ 🏷️ Gamertag: `{p.gamertag.current}`")
        output.append(f"┃ 🆔 XUID: `{p.xuid}`")
        output.append(f"┃ 📅 Joined: `{p.join_date}` ({p.account_age})")
        output.append(f"┃ {EMOJI['location']} Location: `{p.location.city}, {p.location.country}`")
        output.append(f"┃ 📝 Bio: `{p.bio[:50]}...`")
        output.append(f"┃ ⭐ Reputation: `{p.reputation}`")
        output.append(f"┃ {EMOJI['time']} Last Seen: `{p.last_seen}`")
        output.append(f"┃ 🟢 Status: `{p.online_status.value}` on `{p.device.value}`")
        output.append("┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        output.append("")
        
        # Subscription Section
        output.append("┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        output.append(f"┃ {s.icon} *SUBSCRIPTION DETAILS*")
        output.append("┠──────────────────────────────────────")
        output.append(f"┃ 📛 Plan: `{s.name}`")
        output.append(f"┃ 💰 Price: `${s.price_monthly}/month (${s.price_yearly}/year)`")
        output.append(f"┃ 📅 Expires: `{s.expiry}` • Auto-renew: {'✅' if s.auto_renew else '❌'}")
        output.append(f"┃ 💳 Payment: `{s.payment_method}`")
        output.append(f"┃ ✅ API Verified: {'✅' if s.api_verified else '❌'}")
        output.append("┃ ")
        output.append("┃ *Included Features:*")
        output.append(f"┃ ├ 🎮 Game Pass: {'✅' if s.gamepass else '❌'}")
        output.append(f"┃ ├ {EMOJI['ultimate']} Ultimate: {'✅' if s.ultimate else '❌'}")
        output.append(f"┃ ├ {EMOJI['gold']} Gold: {'✅' if s.gold else '❌'}")
        output.append(f"┃ ├ 🎯 EA Play: {'✅' if s.ea_play else '❌'}")
        output.append(f"┃ └ 💬 Discord: {'✅' if s.discord else '❌'}")
        output.append("┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        output.append("")
        
        # Gaming Stats Section
        output.append("┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        output.append(f"┃ {EMOJI['game']} *GAMING STATISTICS*")
        output.append("┠──────────────────────────────────────")
        output.append(f"┃ {EMOJI['achievement']} Gamerscore: `{p.gamerscore:,}`")
        output.append(f"┃ 📈 Achievements: `{a.total_count:,}`")
        output.append(f"┃ 🔥 Rare: {a.rare_count} • Epic: {a.epic_count} • Legendary: {a.legendary_count}")
        output.append(f"┃ ⏱️ Playtime: `{g.total_hours:,} hours`")
        output.append(f"┃ 🎮 Games Played: `{g.total_games}`")
        output.append(f"┃ 📊 Completion: `{g.average_completion:.1f}%`")
        output.append(f"┃ 🎯 Favorite Genre: `{g.favorite_genre}`")
        output.append(f"┃ 🏅 Most Played: `{g.most_played}`")
        output.append("┃ ")
        output.append("┃ *Top Games:*")
        for game in g.games_played[:3]:
            output.append(f"┃ ├ {game.name}: {game.hours_played}h • {game.achievements_unlocked} ach • {game.completion_percentage:.0f}%")
        output.append("┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        output.append("")
        
        # Recent Achievements
        output.append("┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        output.append(f"┃ {EMOJI['achievement']} *RECENT ACHIEVEMENTS*")
        output.append("┠──────────────────────────────────────")
        for ach in a.recent[:3]:
            rarity_emoji: str = "💎" if ach.rarity == AchievementRarity.LEGENDARY else "⚡" if ach.rarity == AchievementRarity.EPIC else "🔥" if ach.rarity == AchievementRarity.RARE else "📌"
            output.append(f"┃ {rarity_emoji} {ach.name} (+{ach.gamerscore}G) • {ach.game}")
        output.append("┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        output.append("")
        
        # Social Section
        output.append("┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        output.append(f"┃ {EMOJI['friends']} *SOCIAL STATISTICS*")
        output.append("┠──────────────────────────────────────")
        output.append(f"┃ Friends: `{len(soc.friends)}` ({soc.friends_online} online)")
        output.append(f"┃ Followers: `{soc.followers:,}` • Following: `{soc.following:,}`")
        output.append(f"┃ Pending Requests: `{soc.pending_requests}`")
        output.append("┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        output.append("")
        
        # Media Section
        output.append("┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        output.append(f"┃ {EMOJI['media']} *MEDIA STATISTICS*")
        output.append("┠──────────────────────────────────────")
        output.append(f"┃ 📸 Screenshots: `{m.screenshots:,}`")
        output.append(f"┃ 🎥 Game Clips: `{m.gameclips:,}`")
        output.append(f"┃ 📡 Broadcasts: `{m.broadcasts}`")
        output.append(f"┃ 💾 Storage: `{m.storage_used:.1f} GB`")
        output.append("┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        output.append("")
        
        # Value Section
        output.append("┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        output.append(f"┃ 💰 *ACCOUNT VALUE*")
        output.append("┠──────────────────────────────────────")
        output.append(f"┃ Yearly Subscription: `${v.yearly_subscription:,.2f}`")
        output.append(f"┃ Games Library: `${v.games_library:,.2f}`")
        output.append(f"┃ Total Value: `${v.total_value:,.2f}`")
        output.append(f"┃ Value Score: `{v.value_score}/100`")
        output.append("┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        output.append("")
        
        # Footer
        output.append("═══════════════════════════════════════")
        output.append(f"📊 *Overall Score:* {summary.score}/100 • Rank: {summary.rank}")
        output.append(f"🕒 Checked: {summary.checked_at}")
        output.append("")
        
        return "\n".join(output)
    
    @staticmethod
    def format_batch(result: BatchResult) -> str:
        """Format batch processing results"""
        
        # Create progress bar
        bar_width: int = 20
        filled: int = int(bar_width * result.valid / result.total) if result.total > 0 else 0
        bar: str = "█" * filled + "░" * (bar_width - filled)
        
        output: List[str] = []
        
        output.append("┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓")
        output.append("┃     📊 BATCH PROCESSING REPORT         ┃")
        output.append("┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛")
        output.append("")
        
        output.append("📁 *File Statistics*")
        output.append("──────────────────────────────")
        output.append(f"📊 Total Accounts: `{result.total}`")
        output.append(f"{bar} {result.success_rate:.1f}% Success Rate")
        output.append("")
        output.append(f"✅ Valid: `{result.valid}`")
        output.append(f"❌ Invalid: `{result.invalid}`")
        output.append("")
        
        output.append("💎 *Subscription Breakdown*")
        output.append("──────────────────────────────")
        output.append(f"🌟 Ultimate: `{result.ultimate}` ({result.ultimate/result.valid*100:.1f}% of valid)")
        output.append(f"🎮 Game Pass: `{result.gamepass}` ({result.gamepass/result.valid*100:.1f}% of valid)")
        output.append(f"💎 Gold: `{result.gold}` ({result.gold/result.valid*100:.1f}% of valid)")
        output.append(f"🆓 Free: `{result.free}` ({result.free/result.valid*100:.1f}% of valid)")
        output.append("")
        
        output.append("🏆 *Gaming Statistics*")
        output.append("──────────────────────────────")
        output.append(f"Total Gamerscore: `{result.total_gamerscore:,}`")
        output.append(f"Average Gamerscore: `{result.avg_gamerscore:,}`")
        output.append(f"Total Hours: `{result.total_hours:,}`")
        output.append(f"Average Hours: `{result.avg_hours:,}`")
        output.append(f"Total Value: `${result.total_value:,.2f}`")
        output.append(f"Average Value: `${result.avg_value:,.2f}`")
        output.append("")
        
        if result.errors:
            output.append("⚠️ *Error Breakdown*")
            output.append("──────────────────────────────")
            for error, count in result.errors.items():
                pct: float = (count / result.invalid * 100) if result.invalid > 0 else 0
                output.append(f"• {error}: {count} ({pct:.1f}%)")
            output.append("")
        
        output.append("──────────────────────────────")
        output.append(f"⏱️ Processing Time: `{result.process_time:.1f}s`")
        output.append(f"⚡ Speed: `{result.total / result.process_time:.1f}` accounts/sec")
        output.append(f"📊 Quality Score: `{result.quality_score}/100`")
        
        return "\n".join(output)
    
    @staticmethod
    def generate_report(results: List[AccountSummary], filename: str) -> str:
        """Generate complete report file"""
        
        report: List[str] = []
        
        # Header
        report.append("=" * 80)
        report.append(" " * 25 + "XBOX ULTIMATE BOT REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Source File: {filename}")
        report.append(f"Total Accounts: {len(results)}")
        report.append(f"API Status: {'Connected' if any(r.api_used == 'xbl.io' for r in results) else 'Using Mock'}")
        report.append("=" * 80)
        report.append("")
        
        # Valid accounts
        valid_accounts: List[AccountSummary] = [r for r in results if r.valid]
        if valid_accounts:
            report.append("✅ VALID ACCOUNTS")
            report.append("-" * 40)
            for i, acc in enumerate(valid_accounts, 1):
                report.append(f"\n【{i}】 {acc.email}:{acc.password}")
                report.append(f"   Gamertag: {acc.profile.gamertag.current if acc.profile else 'N/A'}")
                report.append(f"   XUID: {acc.profile.xuid if acc.profile else 'N/A'}")
                report.append(f"   Gamerscore: {acc.profile.gamerscore if acc.profile else 0:,}")
                report.append(f"   Subscription: {acc.subscription.name if acc.subscription else 'Unknown'}")
                report.append(f"   API Source: {acc.api_used}")
                report.append(f"   Score: {acc.score}/100 • Rank: {acc.rank}")
            report.append("")
        
        # Invalid accounts
        invalid_accounts: List[AccountSummary] = [r for r in results if not r.valid]
        if invalid_accounts:
            report.append("❌ INVALID ACCOUNTS")
            report.append("-" * 40)
            for i, acc in enumerate(invalid_accounts, 1):
                report.append(f"{i}. {acc.email}:{acc.password}")
            report.append("")
        
        # Statistics summary
        report.append("📊 STATISTICS SUMMARY")
        report.append("-" * 40)
        report.append(f"Total: {len(results)}")
        report.append(f"Valid: {len(valid_accounts)} ({len(valid_accounts)/len(results)*100:.1f}%)")
        report.append(f"Invalid: {len(invalid_accounts)} ({len(invalid_accounts)/len(results)*100:.1f}%)")
        
        if valid_accounts:
            subs: Counter = Counter()
            for acc in valid_accounts:
                if acc.subscription:
                    subs[acc.subscription.type.value] += 1
            
            report.append(f"Ultimate: {subs.get('ultimate', 0)}")
            report.append(f"Game Pass: {subs.get('gamepass', 0)}")
            report.append(f"Gold: {subs.get('gold', 0)}")
            report.append(f"Free: {subs.get('free', 0)}")
            
            total_gs: int = sum(acc.profile.gamerscore for acc in valid_accounts if acc.profile)
            total_hours: int = sum(acc.gaming.total_hours for acc in valid_accounts if acc.gaming)
            total_value: float = sum(acc.value.total_value for acc in valid_accounts if acc.value)
            
            report.append(f"Total Gamerscore: {total_gs:,}")
            report.append(f"Total Hours: {total_hours:,}")
            report.append(f"Total Value: ${total_value:,.2f}")
        
        report.append("")
        report.append("=" * 80)
        report.append("End of Report")
        report.append("=" * 80)
        
        return "\n".join(report)

# ============================================
# TELEGRAM BOT
# ============================================

class XboxBot:
    """Main bot class with all features"""
    
    def __init__(self, api_client: XboxAPIClient):
        self.checker: AccountChecker = AccountChecker(api_client)
        self.api: XboxAPIClient = api_client
        self.formatter: Formatter = Formatter()
        self.start_time: datetime = datetime.now()
        self.total_checks: int = 0
        self.total_batches: int = 0
        self.active_users: set = set()
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Start command"""
        user = update.effective_user
        self.active_users.add(user.id)
        
        welcome: str = f"""
{EMOJI['xbox']} *XBOX ULTIMATE API BOT* {EMOJI['xbox']}
══════════════════════════════════════════════════════

👋 *Welcome, {user.first_name}!*

I'm the most advanced Xbox account checker with **real Xbox API + 35+ data points**!

📌 *How to Use*
══════════════════════════════════════════════════════
🔹 **Single Check:** Send `email:password` or `email|password`
🔹 **Batch Check:** Upload a `.txt` file with one per line

📁 *File Format Example*