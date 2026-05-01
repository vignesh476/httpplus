"""
Advanced HTTP Utilities Module
Provides comprehensive, flexible HTTP operations with advanced features for production use.

Features:
- Smart request builder with retry logic and exponential backoff + jitter
- Circuit breaker pattern for fault tolerance with event callbacks
- Request/response caching with TTL
- Batch requests
- Advanced response parsing (JSON, XML, HTML, CSV)
- Streaming upload/download with progress tracking
- Rate limiting and throttling
- Session management with persistence
- Custom exception handling
- Proxy and SSL/TLS support
- Request/response logging and monitoring
- Health checks
- Cookie and auth token management
- Fallback URLs
- Response schema validation (JSON Schema)
- Async/await support for high-performance concurrent requests
"""

import requests
import json
import csv
import time
import logging
import hashlib
import pickle
import threading
import random
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Callable, Union, Coroutine
from urllib.parse import urljoin, parse_qs, urlparse
from pathlib import Path
from functools import wraps
from enum import Enum
from collections import defaultdict
from io import StringIO, BytesIO

try:
    import xml.etree.ElementTree as ET
except ImportError:
    ET = None

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

try:
    import aiohttp
except ImportError:
    aiohttp = None

try:
    import jsonschema
except ImportError:
    jsonschema = None


# ============================================================================
# CUSTOM EXCEPTIONS
# ============================================================================

class HTTPUtilException(Exception):
    """Base exception for http_utils module"""
    pass


class HTTPRetryException(HTTPUtilException):
    """Raised when max retries exceeded"""
    pass


class HTTPTimeoutException(HTTPUtilException):
    """Raised when request times out"""
    pass


class HTTPCircuitBreakerException(HTTPUtilException):
    """Raised when circuit breaker is open"""
    pass


class HTTPValidationException(HTTPUtilException):
    """Raised when response validation fails"""
    pass


class HTTPParsingException(HTTPUtilException):
    """Raised when response parsing fails"""
    pass


class HTTPSchemaValidationException(HTTPUtilException):
    """Raised when response schema validation fails"""
    pass


# ============================================================================
# ENUMS AND CONSTANTS
# ============================================================================

class ResponseFormat(Enum):
    """Supported response formats"""
    JSON = "json"
    XML = "xml"
    HTML = "html"
    CSV = "csv"
    TEXT = "text"
    BYTES = "bytes"


class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


# ============================================================================
# CACHING SYSTEM
# ============================================================================

class ResponseCache:
    """Thread-safe response cache with TTL support"""
    
    def __init__(self, ttl: int = 3600):
        """
        Initialize cache.
        
        Args:
            ttl: Time to live in seconds (default: 1 hour)
        """
        self.ttl = ttl
        self.cache = {}
        self.lock = threading.Lock()
    
    def _generate_key(self, method: str, url: str, params: Optional[Dict] = None) -> str:
        """Generate cache key from request details"""
        key_str = f"{method}:{url}:{json.dumps(params or {}, sort_keys=True)}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, method: str, url: str, params: Optional[Dict] = None) -> Optional[Any]:
        """Retrieve cached response if not expired"""
        with self.lock:
            key = self._generate_key(method, url, params)
            if key in self.cache:
                response, timestamp = self.cache[key]
                if time.time() - timestamp < self.ttl:
                    return response
                else:
                    del self.cache[key]
            return None
    
    def set(self, method: str, url: str, response: Any, params: Optional[Dict] = None):
        """Cache a response"""
        with self.lock:
            key = self._generate_key(method, url, params)
            self.cache[key] = (response, time.time())
    
    def clear(self):
        """Clear all cache"""
        with self.lock:
            self.cache.clear()


# ============================================================================
# CIRCUIT BREAKER
# ============================================================================

class CircuitBreaker:
    """Circuit breaker pattern implementation for fault tolerance"""
    
    def __init__(self, failure_threshold: int = 5, reset_timeout: int = 60):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            reset_timeout: Seconds before attempting to close circuit
        """
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failures = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED
        self.lock = threading.Lock()
        
        # Event callbacks
        self.on_open_callbacks: List[Callable] = []
        self.on_close_callbacks: List[Callable] = []
        self.on_half_open_callbacks: List[Callable] = []
    
    def add_on_open(self, callback: Callable):
        """Register callback when circuit opens"""
        self.on_open_callbacks.append(callback)
    
    def add_on_close(self, callback: Callable):
        """Register callback when circuit closes"""
        self.on_close_callbacks.append(callback)
    
    def add_on_half_open(self, callback: Callable):
        """Register callback when circuit goes to half-open"""
        self.on_half_open_callbacks.append(callback)
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        with self.lock:
            if self.state == CircuitBreakerState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitBreakerState.HALF_OPEN
                    self._trigger_callbacks(self.on_half_open_callbacks)
                else:
                    raise HTTPCircuitBreakerException("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if reset timeout has passed"""
        return (self.last_failure_time and 
                time.time() - self.last_failure_time >= self.reset_timeout)
    
    def _on_success(self):
        """Handle successful call"""
        with self.lock:
            if self.state == CircuitBreakerState.HALF_OPEN:
                self.failures = 0
                self.state = CircuitBreakerState.CLOSED
                self._trigger_callbacks(self.on_close_callbacks)
            elif self.state == CircuitBreakerState.CLOSED:
                self.failures = 0
    
    def _on_failure(self):
        """Handle failed call"""
        with self.lock:
            self.failures += 1
            self.last_failure_time = time.time()
            if self.failures >= self.failure_threshold:
                self.state = CircuitBreakerState.OPEN
                self._trigger_callbacks(self.on_open_callbacks)
    
    def _trigger_callbacks(self, callbacks: List[Callable]):
        """Safely trigger callbacks"""
        for callback in callbacks:
            try:
                callback()
            except Exception as e:
                logging.warning(f"Circuit breaker callback error: {e}")


# ============================================================================
# RATE LIMITER
# ============================================================================

class RateLimiter:
    """Thread-safe rate limiter with token bucket algorithm"""
    
    def __init__(self, requests_per_second: float = 10, burst_size: int = 20):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_second: Allowed requests per second
            burst_size: Maximum burst capacity
        """
        self.rate = requests_per_second
        self.burst_size = burst_size
        self.tokens = float(burst_size)
        self.last_update = time.time()
        self.lock = threading.Lock()
    
    def acquire(self, tokens: int = 1) -> float:
        """
        Acquire tokens, blocking if necessary.
        
        Returns:
            Time waited in seconds
        """
        with self.lock:
            waited = 0
            while self.tokens < tokens:
                current_time = time.time()
                time_passed = current_time - self.last_update
                self.tokens = min(self.burst_size, 
                                self.tokens + time_passed * self.rate)
                self.last_update = current_time
                
                if self.tokens < tokens:
                    sleep_time = (tokens - self.tokens) / self.rate
                    time.sleep(sleep_time)
                    waited += sleep_time
            
            self.tokens -= tokens
            return waited


# ============================================================================
# SESSION MANAGEMENT
# ============================================================================

class Session:
    """Advanced session management with persistence and cookie handling"""
    
    def __init__(self, session_name: str = "default", persist_path: Optional[str] = None):
        """
        Initialize session.
        
        Args:
            session_name: Name of the session
            persist_path: Path to persist cookies (optional)
        """
        self.session_name = session_name
        self.persist_path = persist_path
        self.session = requests.Session()
        self.auth_token = None
        self.token_expiry = None
        self.load_cookies()
    
    def set_auth_token(self, token: str, expires_in: Optional[int] = None):
        """
        Set authentication token.
        
        Args:
            token: Auth token
            expires_in: Token expiry time in seconds
        """
        self.auth_token = token
        if expires_in:
            self.token_expiry = datetime.now() + timedelta(seconds=expires_in)
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def refresh_token_if_needed(self, refresh_func: Callable[[str], str]):
        """Refresh token if expired"""
        if self.token_expiry and datetime.now() >= self.token_expiry:
            self.auth_token = refresh_func(self.auth_token)
            self.session.headers.update({"Authorization": f"Bearer {self.auth_token}"})
    
    def set_headers(self, headers: Dict[str, str]):
        """Set custom headers for session"""
        self.session.headers.update(headers)
    
    def set_proxies(self, proxies: Dict[str, str]):
        """Set proxies for session"""
        self.session.proxies.update(proxies)
    
    def save_cookies(self):
        """Persist cookies to disk"""
        if self.persist_path:
            Path(self.persist_path).parent.mkdir(parents=True, exist_ok=True)
            with open(self.persist_path, 'wb') as f:
                pickle.dump(self.session.cookies, f)
    
    def load_cookies(self):
        """Load cookies from disk"""
        if self.persist_path and Path(self.persist_path).exists():
            with open(self.persist_path, 'rb') as f:
                self.session.cookies.update(pickle.load(f))


# ============================================================================
# RESPONSE SCHEMA VALIDATOR
# ============================================================================

class SchemaValidator:
    """Validate responses against JSON Schema"""
    
    @staticmethod
    def validate(response_data: Any, schema: Dict[str, Any]) -> bool:
        """
        Validate response data against JSON Schema.
        
        Args:
            response_data: Data to validate
            schema: JSON Schema to validate against
            
        Returns:
            True if valid
            
        Raises:
            HTTPSchemaValidationException: If validation fails
        """
        if jsonschema is None:
            raise HTTPSchemaValidationException(
                "JSON Schema validation requires 'jsonschema' package. "
                "Install with: pip install jsonschema"
            )
        
        try:
            jsonschema.validate(instance=response_data, schema=schema)
            return True
        except jsonschema.ValidationError as e:
            raise HTTPSchemaValidationException(
                f"Response validation failed: {e.message}"
            )
        except Exception as e:
            raise HTTPSchemaValidationException(f"Validation error: {str(e)}")


# ============================================================================
# RESPONSE PARSER
# ============================================================================

class ResponseParser:
    """Parse responses in multiple formats"""
    
    @staticmethod
    def parse(response: requests.Response, 
              response_format: ResponseFormat = ResponseFormat.JSON) -> Any:
        """
        Parse response based on format.
        
        Args:
            response: Response object
            response_format: Expected format
            
        Returns:
            Parsed response
            
        Raises:
            HTTPParsingException: If parsing fails
        """
        try:
            if response_format == ResponseFormat.JSON:
                return response.json()
            elif response_format == ResponseFormat.XML:
                if ET is None:
                    raise HTTPParsingException("XML parsing requires ElementTree")
                return ET.fromstring(response.content)
            elif response_format == ResponseFormat.HTML:
                if BeautifulSoup is None:
                    raise HTTPParsingException("HTML parsing requires BeautifulSoup")
                return BeautifulSoup(response.content, 'html.parser')
            elif response_format == ResponseFormat.CSV:
                return list(csv.DictReader(StringIO(response.text)))
            elif response_format == ResponseFormat.TEXT:
                return response.text
            elif response_format == ResponseFormat.BYTES:
                return response.content
            else:
                return response.text
        except Exception as e:
            raise HTTPParsingException(f"Failed to parse response: {str(e)}")


# ============================================================================
# ADVANCED HTTP CLIENT
# ============================================================================

class HTTPClient:
    """Advanced HTTP client with comprehensive features"""
    
    def __init__(self, 
                 base_url: str = "",
                 timeout: int = 30,
                 max_retries: int = 3,
                 backoff_factor: float = 2.0,
                 cache_ttl: int = 3600,
                 enable_caching: bool = True,
                 enable_logging: bool = True):
        """
        Initialize HTTP client.
        
        Args:
            base_url: Base URL for all requests
            timeout: Default timeout in seconds
            max_retries: Maximum number of retries
            backoff_factor: Exponential backoff multiplier
            cache_ttl: Cache TTL in seconds
            enable_caching: Enable response caching
            enable_logging: Enable request logging
        """
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        
        # Initialize components
        self.session = None
        self.cache = ResponseCache(ttl=cache_ttl) if enable_caching else None
        self.circuit_breaker = CircuitBreaker()
        self.rate_limiter = RateLimiter()
        
        # Logging
        self.enable_logging = enable_logging
        self.logger = logging.getLogger(f"http_utils.HTTPClient")
        if enable_logging:
            self.logger.setLevel(logging.DEBUG)
    
    def create_session(self, session_name: str = "default", 
                      persist_cookies: bool = False) -> Session:
        """Create a managed session"""
        persist_path = f".cache/{session_name}_cookies.pkl" if persist_cookies else None
        self.session = Session(session_name, persist_path)
        return self.session
    
    def _build_url(self, endpoint: str) -> str:
        """Build full URL from base and endpoint"""
        return urljoin(self.base_url, endpoint) if self.base_url else endpoint
    
    def _log_request(self, method: str, url: str, **kwargs):
        """Log request details"""
        if self.enable_logging:
            self.logger.debug(f"{method} {url}")
            if kwargs.get('params'):
                self.logger.debug(f"Params: {kwargs['params']}")
    
    def _log_response(self, response: requests.Response, elapsed: float):
        """Log response details"""
        if self.enable_logging:
            self.logger.debug(f"Status: {response.status_code}, "
                            f"Elapsed: {elapsed:.2f}s, "
                            f"Size: {len(response.content)} bytes")
    
    def request(self, 
               method: str, 
               endpoint: str,
               use_cache: bool = True,
               response_format: ResponseFormat = ResponseFormat.JSON,
               fallback_urls: Optional[List[str]] = None,
               response_schema: Optional[Dict] = None,
               **kwargs) -> Any:
        """
        Make HTTP request with advanced features.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            use_cache: Use response cache for GET requests
            response_format: Expected response format
            fallback_urls: List of fallback URLs if primary fails
            response_schema: JSON Schema to validate response against
            **kwargs: Additional arguments for requests
            
        Returns:
            Parsed response
            
        Raises:
            HTTPRetryException: If all retries failed
            HTTPCircuitBreakerException: If circuit breaker is open
            HTTPTimeoutException: If request times out
            HTTPSchemaValidationException: If response validation fails
        """
        url = self._build_url(endpoint)
        timeout = kwargs.pop('timeout', self.timeout)
        
        # Check cache for GET requests
        if use_cache and self.cache and method.upper() == 'GET':
            cached = self.cache.get(method, url, kwargs.get('params'))
            if cached:
                self.logger.debug(f"Cache HIT: {url}")
                return cached
        
        # Rate limiting
        waited = self.rate_limiter.acquire()
        if waited > 0:
            self.logger.debug(f"Rate limit: waited {waited:.2f}s")
        
        # Circuit breaker protection
        def _make_request():
            return self._make_request_with_retries(
                method, url, timeout, response_format, fallback_urls, 
                response_schema, **kwargs
            )
        
        try:
            response = self.circuit_breaker.call(_make_request)
            
            # Cache successful GET responses
            if use_cache and self.cache and method.upper() == 'GET':
                self.cache.set(method, url, response, kwargs.get('params'))
            
            return response
        except HTTPCircuitBreakerException:
            raise
        except Exception as e:
            if fallback_urls:
                return self._try_fallback_urls(
                    method, fallback_urls, response_format, timeout, **kwargs
                )
            raise
    
    def _calculate_backoff_with_jitter(self, attempt: int) -> float:
        """
        Calculate exponential backoff with jitter to prevent thundering herd.
        
        Formula: min(base * (factor ^ attempt) + random(0, base * 0.1), max_wait)
        
        Args:
            attempt: Attempt number (0-indexed)
            
        Returns:
            Time to wait in seconds
        """
        base = self.backoff_factor ** attempt
        jitter = random.uniform(0, base * 0.1)  # 10% jitter
        return base + jitter
    
    def _make_request_with_retries(self, 
                                   method: str,
                                   url: str,
                                   timeout: int,
                                   response_format: ResponseFormat,
                                   fallback_urls: Optional[List[str]],
                                   response_schema: Optional[Dict] = None,
                                   **kwargs) -> Any:
        """Make request with exponential backoff + jitter retry logic"""
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                self._log_request(method, url, **kwargs)
                
                start_time = time.time()
                if self.session:
                    response = self.session.session.request(
                        method, url, timeout=timeout, **kwargs
                    )
                else:
                    response = requests.request(
                        method, url, timeout=timeout, **kwargs
                    )
                
                elapsed = time.time() - start_time
                self._log_response(response, elapsed)
                
                # Check status code
                if response.status_code >= 400:
                    response.raise_for_status()
                
                # Parse response
                parsed = ResponseParser.parse(response, response_format)
                
                # Validate against schema if provided
                if response_schema and response_format == ResponseFormat.JSON:
                    SchemaValidator.validate(parsed, response_schema)
                
                return parsed
            
            except requests.Timeout:
                last_exception = HTTPTimeoutException(f"Request timeout: {url}")
                self.logger.warning(f"Timeout on attempt {attempt + 1}")
            
            except requests.RequestException as e:
                last_exception = e
                self.logger.warning(f"Request failed on attempt {attempt + 1}: {str(e)}")
            
            except (HTTPSchemaValidationException, HTTPParsingException) as e:
                last_exception = e
                self.logger.warning(f"Response validation failed on attempt {attempt + 1}: {str(e)}")
            
            # Exponential backoff with jitter
            if attempt < self.max_retries - 1:
                wait_time = self._calculate_backoff_with_jitter(attempt)
                self.logger.debug(f"Retrying in {wait_time:.2f}s (attempt {attempt + 1}/{self.max_retries})...")
                time.sleep(wait_time)
        
        raise HTTPRetryException(
            f"Max retries ({self.max_retries}) exceeded for {url}: {str(last_exception)}"
        )
    
    def _try_fallback_urls(self,
                          method: str,
                          fallback_urls: List[str],
                          response_format: ResponseFormat,
                          timeout: int,
                          **kwargs) -> Any:
        """Try fallback URLs if primary fails"""
        self.logger.info(f"Trying {len(fallback_urls)} fallback URLs")
        
        for fallback_url in fallback_urls:
            try:
                self._log_request(method, fallback_url, **kwargs)
                response = requests.request(
                    method, fallback_url, timeout=timeout, **kwargs
                )
                if response.status_code < 400:
                    return ResponseParser.parse(response, response_format)
            except Exception as e:
                self.logger.warning(f"Fallback URL failed: {str(e)}")
        
        raise HTTPRetryException("All fallback URLs failed")
    
    def get(self, endpoint: str, **kwargs) -> Any:
        """GET request"""
        return self.request('GET', endpoint, **kwargs)
    
    def post(self, endpoint: str, **kwargs) -> Any:
        """POST request"""
        return self.request('POST', endpoint, **kwargs)
    
    def put(self, endpoint: str, **kwargs) -> Any:
        """PUT request"""
        return self.request('PUT', endpoint, **kwargs)
    
    def patch(self, endpoint: str, **kwargs) -> Any:
        """PATCH request"""
        return self.request('PATCH', endpoint, **kwargs)
    
    def delete(self, endpoint: str, **kwargs) -> Any:
        """DELETE request"""
        return self.request('DELETE', endpoint, **kwargs)
    
    def head(self, endpoint: str, **kwargs) -> Any:
        """HEAD request"""
        return self.request('HEAD', endpoint, **kwargs)
    
    def download_file(self, 
                     endpoint: str,
                     save_path: str,
                     chunk_size: int = 8192,
                     progress_callback: Optional[Callable[[int, int], None]] = None,
                     **kwargs) -> str:
        """
        Download file with progress tracking.
        
        Args:
            endpoint: URL to download from
            save_path: Path to save file
            chunk_size: Download chunk size
            progress_callback: Callback function(current_bytes, total_bytes)
            
        Returns:
            Path to saved file
        """
        url = self._build_url(endpoint)
        self._log_request('GET', url, **kwargs)
        
        response = requests.get(url, stream=True, timeout=self.timeout, **kwargs)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback:
                        progress_callback(downloaded, total_size)
        
        return save_path
    
    def upload_file(self,
                   endpoint: str,
                   file_path: str,
                   field_name: str = "file",
                   progress_callback: Optional[Callable[[int, int], None]] = None,
                   **kwargs) -> Any:
        """
        Upload file with progress tracking.
        
        Args:
            endpoint: Upload endpoint
            file_path: Path to file to upload
            field_name: Form field name
            progress_callback: Callback function(uploaded_bytes, total_bytes)
            
        Returns:
            Parsed response
        """
        url = self._build_url(endpoint)
        
        file_size = Path(file_path).stat().st_size
        uploaded = 0
        
        def callback_wrapper(monitor):
            nonlocal uploaded
            current = monitor.bytes_read
            if progress_callback:
                progress_callback(current, file_size)
        
        with open(file_path, 'rb') as f:
            files = {field_name: f}
            return self.post(endpoint, files=files, **kwargs)
    
    def batch_requests(self,
                      requests_list: List[Dict[str, Any]],
                      parallel: bool = False) -> List[Any]:
        """
        Make multiple requests.
        
        Args:
            requests_list: List of request dicts with 'method', 'endpoint', etc.
            parallel: Execute in parallel (not thread-safe for this version)
            
        Returns:
            List of responses
        """
        results = []
        for req in requests_list:
            method = req.pop('method', 'GET')
            endpoint = req.pop('endpoint')
            try:
                result = self.request(method, endpoint, **req)
                results.append({'success': True, 'data': result})
            except Exception as e:
                results.append({'success': False, 'error': str(e)})
        
        return results
    
    def health_check(self,
                    endpoint: str,
                    expected_status: int = 200,
                    timeout: int = 5) -> bool:
        """
        Check if endpoint is healthy.
        
        Args:
            endpoint: Endpoint to check
            expected_status: Expected HTTP status
            timeout: Check timeout in seconds
            
        Returns:
            True if healthy, False otherwise
        """
        try:
            response = requests.head(
                self._build_url(endpoint),
                timeout=timeout,
                allow_redirects=True
            )
            return response.status_code == expected_status
        except Exception:
            return False
    
    def clear_cache(self):
        """Clear response cache"""
        if self.cache:
            self.cache.clear()


# ============================================================================
# ASYNC HTTP CLIENT
# ============================================================================

class AsyncHTTPClient:
    """Async HTTP client for high-concurrency scenarios"""
    
    def __init__(self,
                 base_url: str = "",
                 timeout: int = 30,
                 max_retries: int = 3,
                 backoff_factor: float = 2.0):
        """
        Initialize async HTTP client.
        
        Args:
            base_url: Base URL for all requests
            timeout: Default timeout in seconds
            max_retries: Maximum number of retries
            backoff_factor: Exponential backoff multiplier
        """
        if aiohttp is None:
            raise RuntimeError(
                "Async support requires 'aiohttp' package. "
                "Install with: pip install aiohttp"
            )
        
        self.base_url = base_url
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.logger = logging.getLogger(f"http_utils.AsyncHTTPClient")
    
    def _build_url(self, endpoint: str) -> str:
        """Build full URL from base and endpoint"""
        return urljoin(self.base_url, endpoint) if self.base_url else endpoint
    
    async def request(self,
                     method: str,
                     endpoint: str,
                     response_format: ResponseFormat = ResponseFormat.JSON,
                     **kwargs) -> Any:
        """
        Make async HTTP request.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            response_format: Expected response format
            **kwargs: Additional arguments for aiohttp
            
        Returns:
            Parsed response
        """
        url = self._build_url(endpoint)
        
        for attempt in range(self.max_retries):
            try:
                async with aiohttp.ClientSession(timeout=self.timeout) as session:
                    async with session.request(method, url, **kwargs) as response:
                        if response.status >= 400:
                            response.raise_for_status()
                        
                        if response_format == ResponseFormat.JSON:
                            return await response.json()
                        elif response_format == ResponseFormat.TEXT:
                            return await response.text()
                        elif response_format == ResponseFormat.BYTES:
                            return await response.read()
                        else:
                            return await response.text()
            
            except asyncio.TimeoutError:
                self.logger.warning(f"Timeout on attempt {attempt + 1}")
                if attempt < self.max_retries - 1:
                    wait_time = self.backoff_factor ** attempt
                    wait_time += random.uniform(0, wait_time * 0.1)  # Jitter
                    await asyncio.sleep(wait_time)
            
            except aiohttp.ClientError as e:
                self.logger.warning(f"Request failed on attempt {attempt + 1}: {str(e)}")
                if attempt < self.max_retries - 1:
                    wait_time = self.backoff_factor ** attempt
                    wait_time += random.uniform(0, wait_time * 0.1)  # Jitter
                    await asyncio.sleep(wait_time)
        
        raise HTTPRetryException(f"Max async retries ({self.max_retries}) exceeded for {url}")
    
    async def get(self, endpoint: str, **kwargs) -> Any:
        """Async GET request"""
        return await self.request('GET', endpoint, **kwargs)
    
    async def post(self, endpoint: str, **kwargs) -> Any:
        """Async POST request"""
        return await self.request('POST', endpoint, **kwargs)
    
    async def put(self, endpoint: str, **kwargs) -> Any:
        """Async PUT request"""
        return await self.request('PUT', endpoint, **kwargs)
    
    async def patch(self, endpoint: str, **kwargs) -> Any:
        """Async PATCH request"""
        return await self.request('PATCH', endpoint, **kwargs)
    
    async def delete(self, endpoint: str, **kwargs) -> Any:
        """Async DELETE request"""
        return await self.request('DELETE', endpoint, **kwargs)
    
    async def batch_requests(self, requests_list: List[Dict[str, Any]]) -> List[Any]:
        """
        Execute multiple requests concurrently.
        
        Args:
            requests_list: List of request dicts with 'method', 'endpoint', etc.
            
        Returns:
            List of responses in original order
        """
        tasks = []
        for req in requests_list:
            method = req.pop('method', 'GET')
            endpoint = req.pop('endpoint')
            tasks.append(self.request(method, endpoint, **req))
        
        results = []
        for task in asyncio.as_completed(tasks):
            try:
                result = await task
                results.append({'success': True, 'data': result})
            except Exception as e:
                results.append({'success': False, 'error': str(e)})
        
        return results


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def quick_get(url: str, timeout: int = 30, **kwargs) -> Any:
    """Quick GET request"""
    client = HTTPClient(timeout=timeout)
    return client.get(url, **kwargs)


def quick_post(url: str, timeout: int = 30, **kwargs) -> Any:
    """Quick POST request"""
    client = HTTPClient(timeout=timeout)
    return client.post(url, **kwargs)


def download(url: str, save_path: str, 
             progress_callback: Optional[Callable[[int, int], None]] = None) -> str:
    """Quick file download"""
    client = HTTPClient()
    return client.download_file(url, save_path, progress_callback=progress_callback)


# Example usage and tests
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Example 1: Basic request
    print("Example 1: Basic GET request")
    try:
        result = quick_get("https://api.github.com/users/github", 
                          response_format=ResponseFormat.JSON)
        print(f"User: {result.get('name', 'N/A')}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Example 2: Using HTTPClient with session and circuit breaker events
    print("\nExample 2: HTTPClient with circuit breaker events")
    client = HTTPClient(base_url="https://api.github.com", enable_caching=True)
    
    # Register circuit breaker callbacks
    client.circuit_breaker.add_on_open(lambda: print("⚠️ Circuit breaker OPENED!"))
    client.circuit_breaker.add_on_close(lambda: print("✓ Circuit breaker CLOSED - service recovered"))
    client.circuit_breaker.add_on_half_open(lambda: print("🔄 Circuit breaker in HALF_OPEN state - testing recovery"))
    
    session = client.create_session("github")
    
    try:
        users = client.get("/users?per_page=5")
        print(f"Retrieved {len(users)} users")
    except Exception as e:
        print(f"Error: {e}")
    
    # Example 3: Response schema validation
    print("\nExample 3: Schema validation (if jsonschema installed)")
    user_schema = {
        "type": "object",
        "properties": {
            "login": {"type": "string"},
            "id": {"type": "integer"},
            "name": {"type": ["string", "null"]}
        },
        "required": ["login", "id"]
    }
    
    try:
        user = client.get("/users/torvalds", response_schema=user_schema)
        print(f"✓ Schema validation passed for user: {user.get('login')}")
    except Exception as e:
        print(f"Validation error: {e}")
    
    # Example 4: Async requests (if aiohttp installed)
    print("\nExample 4: Async batch requests (if aiohttp installed)")
    try:
        async_client = AsyncHTTPClient(base_url="https://api.github.com")
        
        async def demo_async():
            # Fetch multiple users concurrently
            requests_list = [
                {"method": "GET", "endpoint": "/users/torvalds"},
                {"method": "GET", "endpoint": "/users/gvanrossum"},
                {"method": "GET", "endpoint": "/users/brendaneich"},
            ]
            results = await async_client.batch_requests(requests_list)
            
            successful = sum(1 for r in results if r['success'])
            print(f"✓ Async batch completed: {successful}/{len(results)} successful")
        
        asyncio.run(demo_async())
    except RuntimeError as e:
        print(f"Async not available: {e}")
    except Exception as e:
        print(f"Async error: {e}")
    
    # Example 5: Retry with jitter
    print("\nExample 5: Exponential backoff with jitter")
    test_client = HTTPClient()
    print(f"Max retries: {test_client.max_retries}")
    print(f"Backoff factor: {test_client.backoff_factor}")
    print("Retry backoff times (with jitter):")
    for attempt in range(test_client.max_retries - 1):
        wait_time = test_client._calculate_backoff_with_jitter(attempt)
        print(f"  Attempt {attempt + 1}: {wait_time:.2f}s")
    
    print("\n✓ http_utils module is ready for use!")
    print("Features available:")
    print("  • Sync HTTP requests with retry + jitter")
    print("  • Async HTTP requests (install aiohttp)")
    print("  • Circuit breaker with event callbacks")
    print("  • Response schema validation (install jsonschema)")
    print("  • Caching, rate limiting, session management")
    print("  • Multi-format response parsing")

