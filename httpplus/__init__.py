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

__version__ = "1.0.2"
__author__ = "Vignesh Buggaram"
__license__ = "MIT"

# Import main modules for convenience
from . import http_utils

# Expose key classes, functions, and exceptions
from .http_utils import (
    # Main Clients
    HTTPClient,
    AsyncHTTPClient,
    
    # Enums
    ResponseFormat,
    CircuitBreakerState,
    
    # Core Components
    Session,
    ResponseCache,
    CircuitBreaker,
    RateLimiter,
    SchemaValidator,
    ResponseParser,
    
    # Convenience Functions
    quick_get,
    quick_post,
    download,
    
    # Exceptions
    HTTPUtilException,
    HTTPRetryException,
    HTTPTimeoutException,
    HTTPCircuitBreakerException,
    HTTPValidationException,
    HTTPParsingException,
    HTTPSchemaValidationException,
)

__all__ = [
    # Metadata
    '__version__',
    '__author__',
    '__license__',
    
    # Main Clients
    'HTTPClient',
    'AsyncHTTPClient',
    
    # Enums
    'ResponseFormat',
    'CircuitBreakerState',
    
    # Core Components
    'Session',
    'ResponseCache',
    'CircuitBreaker',
    'RateLimiter',
    'SchemaValidator',
    'ResponseParser',
    
    # Convenience Functions
    'quick_get',
    'quick_post',
    'download',
    
    # Exceptions
    'HTTPUtilException',
    'HTTPRetryException',
    'HTTPTimeoutException',
    'HTTPCircuitBreakerException',
    'HTTPValidationException',
    'HTTPParsingException',
    'HTTPSchemaValidationException',
]
