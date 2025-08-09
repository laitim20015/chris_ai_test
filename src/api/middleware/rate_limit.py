"""
API限流中間件
Rate Limit Middleware

實現基於IP和用戶的API限流功能，保護系統免受過度請求的影響。
支援多種限流策略和存儲後端。

功能特性：
- IP級別限流
- 用戶級別限流
- 多種限流算法（令牌桶、滑動窗口）
- Redis分佈式支援
- 自定義響應和錯誤處理
- 白名單和黑名單
- 動態配置更新

限流策略：
- 令牌桶算法：平滑突發流量
- 滑動窗口：精確時間窗口控制
- 固定窗口：簡單計數器方式
"""

from typing import Dict, List, Optional, Callable, Any, Union
import time
import asyncio
import json
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import hashlib

from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.config.logging_config import get_logger

logger = get_logger("api.middleware.rate_limit")

class RateLimitStrategy(Enum):
    """限流策略枚舉"""
    TOKEN_BUCKET = "token_bucket"       # 令牌桶算法
    SLIDING_WINDOW = "sliding_window"   # 滑動窗口
    FIXED_WINDOW = "fixed_window"       # 固定窗口

class RateLimitScope(Enum):
    """限流範圍枚舉"""
    IP = "ip"                          # IP地址
    USER = "user"                      # 用戶ID
    API_KEY = "api_key"               # API金鑰
    ENDPOINT = "endpoint"             # 接口端點

@dataclass
class RateLimitRule:
    """限流規則配置"""
    # 基本配置
    requests_per_minute: int = 60      # 每分鐘請求數
    requests_per_hour: int = 1000      # 每小時請求數
    requests_per_day: int = 10000      # 每天請求數
    
    # 突發允許
    burst_limit: int = 10              # 突發限制
    burst_window_seconds: int = 1      # 突發窗口
    
    # 策略配置
    strategy: RateLimitStrategy = RateLimitStrategy.TOKEN_BUCKET
    scope: RateLimitScope = RateLimitScope.IP
    
    # 路徑匹配
    path_patterns: List[str] = field(default_factory=list)
    methods: List[str] = field(default_factory=lambda: ["GET", "POST", "PUT", "DELETE"])
    
    # 高級選項
    enabled: bool = True
    priority: int = 100                # 規則優先級，數字越小優先級越高
    
    def matches_request(self, request: Request) -> bool:
        """檢查規則是否匹配請求"""
        if not self.enabled:
            return False
        
        # 檢查HTTP方法
        if request.method not in self.methods:
            return False
        
        # 檢查路徑模式
        if self.path_patterns:
            import fnmatch
            request_path = str(request.url.path)
            
            for pattern in self.path_patterns:
                if fnmatch.fnmatch(request_path, pattern):
                    return True
            return False
        
        return True

@dataclass
class RateLimitConfig:
    """限流配置"""
    # 基本配置
    enabled: bool = True
    default_rule: RateLimitRule = field(default_factory=RateLimitRule)
    
    # 規則列表
    rules: List[RateLimitRule] = field(default_factory=list)
    
    # 白名單和黑名單
    whitelist_ips: List[str] = field(default_factory=list)
    blacklist_ips: List[str] = field(default_factory=list)
    
    # Redis配置（分佈式限流）
    redis_url: Optional[str] = None
    redis_key_prefix: str = "rate_limit"
    
    # 錯誤響應配置
    error_message: str = "請求過於頻繁，請稍後再試"
    error_details: bool = True         # 是否包含詳細錯誤信息
    
    # 標頭配置
    include_headers: bool = True       # 是否包含限流標頭
    
    def get_matching_rule(self, request: Request) -> RateLimitRule:
        """獲取匹配的限流規則"""
        # 按優先級排序規則
        sorted_rules = sorted(self.rules, key=lambda r: r.priority)
        
        # 查找第一個匹配的規則
        for rule in sorted_rules:
            if rule.matches_request(request):
                return rule
        
        # 返回默認規則
        return self.default_rule

class RateLimitStorage:
    """限流存儲接口"""
    
    async def get_current_count(self, key: str, window_seconds: int) -> int:
        """獲取當前窗口的請求計數"""
        raise NotImplementedError
    
    async def increment_count(self, key: str, window_seconds: int, expire_seconds: int = None) -> int:
        """增加請求計數"""
        raise NotImplementedError
    
    async def get_token_bucket(self, key: str) -> Dict[str, Any]:
        """獲取令牌桶狀態"""
        raise NotImplementedError
    
    async def update_token_bucket(self, key: str, tokens: float, last_refill: float, expire_seconds: int = None):
        """更新令牌桶狀態"""
        raise NotImplementedError

class MemoryRateLimitStorage(RateLimitStorage):
    """內存限流存儲"""
    
    def __init__(self):
        self._counters: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self._token_buckets: Dict[str, Dict[str, Any]] = {}
    
    async def get_current_count(self, key: str, window_seconds: int) -> int:
        """獲取當前窗口的請求計數"""
        current_time = int(time.time())
        window_start = current_time - (current_time % window_seconds)
        window_key = f"{key}:{window_start}"
        
        return self._counters.get(window_key, {}).get("count", 0)
    
    async def increment_count(self, key: str, window_seconds: int, expire_seconds: int = None) -> int:
        """增加請求計數"""
        current_time = int(time.time())
        window_start = current_time - (current_time % window_seconds)
        window_key = f"{key}:{window_start}"
        
        if window_key not in self._counters:
            self._counters[window_key] = {"count": 0, "expires": current_time + (expire_seconds or window_seconds)}
        
        self._counters[window_key]["count"] += 1
        
        # 清理過期的窗口
        expired_keys = [
            k for k, v in self._counters.items() 
            if v.get("expires", 0) < current_time
        ]
        for expired_key in expired_keys:
            del self._counters[expired_key]
        
        return self._counters[window_key]["count"]
    
    async def get_token_bucket(self, key: str) -> Dict[str, Any]:
        """獲取令牌桶狀態"""
        return self._token_buckets.get(key, {
            "tokens": 0.0,
            "last_refill": time.time()
        })
    
    async def update_token_bucket(self, key: str, tokens: float, last_refill: float, expire_seconds: int = None):
        """更新令牌桶狀態"""
        self._token_buckets[key] = {
            "tokens": tokens,
            "last_refill": last_refill
        }

class RedisRateLimitStorage(RateLimitStorage):
    """Redis限流存儲"""
    
    def __init__(self, redis_url: str, key_prefix: str = "rate_limit"):
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self._redis = None
    
    async def _get_redis(self):
        """獲取Redis連接"""
        if self._redis is None:
            try:
                import aioredis
                self._redis = aioredis.from_url(self.redis_url)
            except ImportError:
                logger.error("Redis限流需要安裝aioredis: pip install aioredis")
                raise
        return self._redis
    
    async def get_current_count(self, key: str, window_seconds: int) -> int:
        """獲取當前窗口的請求計數"""
        redis = await self._get_redis()
        current_time = int(time.time())
        window_start = current_time - (current_time % window_seconds)
        redis_key = f"{self.key_prefix}:counter:{key}:{window_start}"
        
        count = await redis.get(redis_key)
        return int(count) if count else 0
    
    async def increment_count(self, key: str, window_seconds: int, expire_seconds: int = None) -> int:
        """增加請求計數"""
        redis = await self._get_redis()
        current_time = int(time.time())
        window_start = current_time - (current_time % window_seconds)
        redis_key = f"{self.key_prefix}:counter:{key}:{window_start}"
        
        # 使用Redis管道進行原子操作
        pipe = redis.pipeline()
        pipe.incr(redis_key)
        pipe.expire(redis_key, expire_seconds or window_seconds)
        results = await pipe.execute()
        
        return results[0]
    
    async def get_token_bucket(self, key: str) -> Dict[str, Any]:
        """獲取令牌桶狀態"""
        redis = await self._get_redis()
        redis_key = f"{self.key_prefix}:bucket:{key}"
        
        data = await redis.hgetall(redis_key)
        if data:
            return {
                "tokens": float(data.get(b"tokens", 0)),
                "last_refill": float(data.get(b"last_refill", time.time()))
            }
        else:
            return {
                "tokens": 0.0,
                "last_refill": time.time()
            }
    
    async def update_token_bucket(self, key: str, tokens: float, last_refill: float, expire_seconds: int = None):
        """更新令牌桶狀態"""
        redis = await self._get_redis()
        redis_key = f"{self.key_prefix}:bucket:{key}"
        
        await redis.hset(redis_key, mapping={
            "tokens": str(tokens),
            "last_refill": str(last_refill)
        })
        
        if expire_seconds:
            await redis.expire(redis_key, expire_seconds)

class RateLimiter:
    """限流器"""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        
        # 初始化存儲
        if config.redis_url:
            self.storage = RedisRateLimitStorage(config.redis_url, config.redis_key_prefix)
        else:
            self.storage = MemoryRateLimitStorage()
        
        logger.info(f"限流器初始化完成，使用存儲: {type(self.storage).__name__}")
    
    def _get_client_key(self, request: Request, rule: RateLimitRule) -> str:
        """獲取客戶端標識"""
        if rule.scope == RateLimitScope.IP:
            # 優先使用X-Forwarded-For標頭
            forwarded_for = request.headers.get("X-Forwarded-For")
            if forwarded_for:
                return forwarded_for.split(",")[0].strip()
            
            # 使用X-Real-IP標頭
            real_ip = request.headers.get("X-Real-IP")
            if real_ip:
                return real_ip
            
            # 使用客戶端IP
            return str(request.client.host) if request.client else "unknown"
        
        elif rule.scope == RateLimitScope.USER:
            # 從認證信息中提取用戶ID
            user_id = getattr(request.state, "user_id", None)
            if user_id:
                return f"user:{user_id}"
            
            # 如果沒有用戶ID，回退到IP
            return self._get_client_key(request, 
                RateLimitRule(scope=RateLimitScope.IP))
        
        elif rule.scope == RateLimitScope.API_KEY:
            # 從標頭或查詢參數中提取API金鑰
            api_key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
            if api_key:
                # 使用API金鑰的哈希值作為標識
                return f"apikey:{hashlib.sha256(api_key.encode()).hexdigest()[:16]}"
            
            # 回退到IP
            return self._get_client_key(request, 
                RateLimitRule(scope=RateLimitScope.IP))
        
        elif rule.scope == RateLimitScope.ENDPOINT:
            # 使用端點路徑
            return f"endpoint:{request.url.path}"
        
        else:
            return "default"
    
    async def _check_token_bucket(self, client_key: str, rule: RateLimitRule) -> tuple[bool, Dict[str, Any]]:
        """檢查令牌桶限流"""
        current_time = time.time()
        
        # 獲取令牌桶狀態
        bucket = await self.storage.get_token_bucket(client_key)
        tokens = bucket["tokens"]
        last_refill = bucket["last_refill"]
        
        # 計算需要補充的令牌
        time_passed = current_time - last_refill
        tokens_to_add = time_passed * (rule.requests_per_minute / 60.0)
        tokens = min(rule.burst_limit, tokens + tokens_to_add)
        
        # 更新令牌桶
        await self.storage.update_token_bucket(
            client_key, tokens, current_time, expire_seconds=3600
        )
        
        # 檢查是否有足夠的令牌
        if tokens >= 1.0:
            tokens -= 1.0
            await self.storage.update_token_bucket(
                client_key, tokens, current_time, expire_seconds=3600
            )
            
            return True, {
                "allowed": True,
                "tokens_remaining": int(tokens),
                "reset_time": None,
                "retry_after": None
            }
        else:
            return False, {
                "allowed": False,
                "tokens_remaining": 0,
                "reset_time": current_time + (1.0 - tokens) * (60.0 / rule.requests_per_minute),
                "retry_after": int((1.0 - tokens) * (60.0 / rule.requests_per_minute)) + 1
            }
    
    async def _check_sliding_window(self, client_key: str, rule: RateLimitRule) -> tuple[bool, Dict[str, Any]]:
        """檢查滑動窗口限流"""
        current_time = int(time.time())
        
        # 檢查不同時間窗口
        windows = [
            (60, rule.requests_per_minute),    # 1分鐘窗口
            (3600, rule.requests_per_hour),    # 1小時窗口
            (86400, rule.requests_per_day)     # 1天窗口
        ]
        
        for window_seconds, limit in windows:
            count = await self.storage.get_current_count(
                f"{client_key}:sliding:{window_seconds}", window_seconds
            )
            
            if count >= limit:
                reset_time = current_time + window_seconds - (current_time % window_seconds)
                return False, {
                    "allowed": False,
                    "requests_remaining": 0,
                    "reset_time": reset_time,
                    "retry_after": reset_time - current_time,
                    "window_seconds": window_seconds,
                    "limit": limit
                }
        
        # 增加計數
        for window_seconds, limit in windows:
            await self.storage.increment_count(
                f"{client_key}:sliding:{window_seconds}", 
                window_seconds, 
                expire_seconds=window_seconds
            )
        
        # 計算剩餘請求數
        remaining = min(
            rule.requests_per_minute - await self.storage.get_current_count(
                f"{client_key}:sliding:60", 60
            ),
            rule.requests_per_hour - await self.storage.get_current_count(
                f"{client_key}:sliding:3600", 3600
            ),
            rule.requests_per_day - await self.storage.get_current_count(
                f"{client_key}:sliding:86400", 86400
            )
        )
        
        return True, {
            "allowed": True,
            "requests_remaining": max(0, remaining),
            "reset_time": current_time + 60,
            "retry_after": None
        }
    
    async def check_rate_limit(self, request: Request) -> tuple[bool, Dict[str, Any]]:
        """檢查限流"""
        if not self.config.enabled:
            return True, {"allowed": True}
        
        # 檢查IP白名單
        client_ip = self._get_client_key(request, RateLimitRule(scope=RateLimitScope.IP))
        if client_ip in self.config.whitelist_ips:
            return True, {"allowed": True, "whitelisted": True}
        
        # 檢查IP黑名單
        if client_ip in self.config.blacklist_ips:
            return False, {"allowed": False, "blacklisted": True}
        
        # 獲取匹配的規則
        rule = self.config.get_matching_rule(request)
        if not rule.enabled:
            return True, {"allowed": True}
        
        # 獲取客戶端標識
        client_key = self._get_client_key(request, rule)
        
        # 根據策略檢查限流
        if rule.strategy == RateLimitStrategy.TOKEN_BUCKET:
            return await self._check_token_bucket(client_key, rule)
        elif rule.strategy == RateLimitStrategy.SLIDING_WINDOW:
            return await self._check_sliding_window(client_key, rule)
        else:
            # 默認使用滑動窗口
            return await self._check_sliding_window(client_key, rule)

class RateLimitMiddleware(BaseHTTPMiddleware):
    """限流中間件"""
    
    def __init__(self, app: ASGIApp, config: RateLimitConfig = None):
        super().__init__(app)
        self.config = config or RateLimitConfig()
        self.limiter = RateLimiter(self.config)
        
        logger.info("限流中間件初始化完成")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """處理請求"""
        try:
            # 檢查限流
            allowed, limit_info = await self.limiter.check_rate_limit(request)
            
            if not allowed:
                # 構建錯誤響應
                error_response = {
                    "error": "rate_limit_exceeded",
                    "message": self.config.error_message
                }
                
                if self.config.error_details:
                    error_response.update({
                        "retry_after": limit_info.get("retry_after"),
                        "reset_time": limit_info.get("reset_time"),
                        "limit_info": limit_info
                    })
                
                response = JSONResponse(
                    status_code=429,
                    content=error_response
                )
                
                # 添加標準限流標頭
                if self.config.include_headers:
                    if limit_info.get("retry_after"):
                        response.headers["Retry-After"] = str(limit_info["retry_after"])
                    
                    if limit_info.get("reset_time"):
                        response.headers["X-RateLimit-Reset"] = str(int(limit_info["reset_time"]))
                
                logger.warning(
                    f"請求被限流: {request.client.host} {request.method} {request.url.path}"
                )
                
                return response
            
            # 處理請求
            response = await call_next(request)
            
            # 添加限流標頭
            if self.config.include_headers and allowed:
                if "requests_remaining" in limit_info:
                    response.headers["X-RateLimit-Remaining"] = str(limit_info["requests_remaining"])
                
                if "reset_time" in limit_info:
                    response.headers["X-RateLimit-Reset"] = str(int(limit_info["reset_time"]))
            
            return response
            
        except Exception as e:
            logger.error(f"限流中間件錯誤: {e}")
            # 在錯誤情況下允許請求通過
            return await call_next(request)

# 便捷函數
def create_rate_limit_middleware(
    requests_per_minute: int = 60,
    requests_per_hour: int = 1000,
    requests_per_day: int = 10000,
    burst_limit: int = 10,
    strategy: RateLimitStrategy = RateLimitStrategy.TOKEN_BUCKET,
    scope: RateLimitScope = RateLimitScope.IP,
    redis_url: Optional[str] = None,
    whitelist_ips: List[str] = None,
    **kwargs
) -> RateLimitMiddleware:
    """
    創建限流中間件（便捷函數）
    
    Args:
        requests_per_minute: 每分鐘請求數
        requests_per_hour: 每小時請求數
        requests_per_day: 每天請求數
        burst_limit: 突發限制
        strategy: 限流策略
        scope: 限流範圍
        redis_url: Redis URL（用於分佈式限流）
        whitelist_ips: IP白名單
        **kwargs: 其他配置參數
        
    Returns:
        RateLimitMiddleware: 限流中間件實例
    """
    default_rule = RateLimitRule(
        requests_per_minute=requests_per_minute,
        requests_per_hour=requests_per_hour,
        requests_per_day=requests_per_day,
        burst_limit=burst_limit,
        strategy=strategy,
        scope=scope
    )
    
    config = RateLimitConfig(
        default_rule=default_rule,
        redis_url=redis_url,
        whitelist_ips=whitelist_ips or [],
        **kwargs
    )
    
    return lambda app: RateLimitMiddleware(app, config)
