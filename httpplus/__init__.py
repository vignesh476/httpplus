"""
HTTPPlus - Professional HTTP Toolkit for Python

A production-ready HTTP client library with advanced features including:
- Async/await support for high-performance concurrent requests
- Circuit breaker pattern for fault tolerance
- Smart retry logic with exponential backoff and jitter
- Request/response caching with TTL
- Response schema validation (JSON Schema)
- Rate limiting and throttling
- Session management with persistent cookies
- Multiple response formats (JSON, XML, HTML, CSV)
- File operations with progress tracking
- Health monitoring and status checks

Perfect for building reliable APIs, microservices, and data pipelines.
"""

__version__ = "1.0.0"
__author__ = "Vignesh Buggaram"
__license__ = "MIT"

# Import main modules for convenience
from . import http_utils

# Expose key classes and functions
from .http_utils import (
    HTTPClient,
    AsyncHTTPClient,
    ResponseFormat,
    Session,
    ResponseCache,
    CircuitBreaker,
    RateLimiter,
    SchemaValidator,
    ResponseParser,
    quick_get,
    quick_post,
    download,
)

__all__ = [
    'http_utils',
    'HTTPClient',
    'AsyncHTTPClient',
    'ResponseFormat',
    'Session',
    'ResponseCache',
    'CircuitBreaker',
    'RateLimiter',
    'SchemaValidator',
    'ResponseParser',
    'quick_get',
    'quick_post',
    'download',
]
