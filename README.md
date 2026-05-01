# HTTPPlus

**Professional HTTP Toolkit for Python** - Production-ready utilities for modern HTTP operations with advanced features for building reliable APIs and microservices.

[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI Version](https://img.shields.io/pypi/v/httpplus.svg)](https://pypi.org/project/httpplus/)
[![Code style: PEP 8](https://img.shields.io/badge/code%20style-pep%200088-green.svg)](https://www.python.org/dev/peps/pep-0008/)

## Overview

HTTPPlus is a battle-tested, production-ready HTTP client library designed to handle complex real-world scenarios. Beyond basic HTTP requests, it provides enterprise-grade features like circuit breakers, intelligent retry logic, caching, and validation out-of-the-box.

### Why HTTPPlus?

- **Production-Ready** - Battle-tested with comprehensive error handling
- **Async/Await Support** - High-performance concurrent requests with async-await
- **Smart Retry Logic** - Exponential backoff with jitter to prevent thundering herd
- **Circuit Breaker** - Automatic fault tolerance and graceful degradation
- **Intelligent Caching** - TTL-based response caching with thread safety
- **Schema Validation** - JSON Schema support for response validation
- **Rate Limiting** - Token bucket algorithm for controlling request rate
- **Session Management** - Persistent cookies, token refresh, and auth handling
- **Minimal Dependencies** - Only requires `requests` (with optional extras)
- **Thread-Safe** - Safe for multi-threaded and async applications

## Key Features

### Smart HTTP Client
- Exponential backoff with jitter for intelligent retries
- Automatic error handling and recovery
- Timeout management
- Custom exception hierarchy
- Request/response logging

### Advanced Patterns
- **Circuit Breaker** - Prevents cascade failures with event callbacks
- **Rate Limiting** - Token bucket algorithm for request throttling
- **Response Caching** - TTL-based caching with thread-safe operations
- **Session Management** - Cookie persistence and token lifecycle management

### Response Handling
- Multiple formats: JSON, XML, HTML, CSV, text, bytes
- Batch request processing
- Streaming upload/download with progress tracking
- Fallback URLs for high availability
- Health checks and endpoint monitoring

### Advanced Capabilities
- Async/await support for concurrent operations
- Response schema validation (JSON Schema)
- Request/response logging and debugging
- Proxy and SSL/TLS support
- Cookie and authentication token management
- Customizable error handling

## Installation

### Basic Installation
```bash
pip install httpplus
```

### With Optional Features
```bash
# HTML parsing support
pip install httpplus[html]

# Async support
pip install httpplus[async]

# Response validation support
pip install httpplus[schema]

# All features
pip install httpplus[all]

# Development tools
pip install httpplus[dev]
```

## Quick Start

### Simple Request
```python
from httpplus import quick_get

# One-liner GET request
response = quick_get("https://jsonplaceholder.typicode.com/users/1")
print(response)  # Returns parsed JSON response
```

### HTTP Client with Advanced Features
```python
from httpplus import HTTPClient

# Create client with features enabled
client = HTTPClient(
    base_url="https://jsonplaceholder.typicode.com",
    enable_caching=True,
    cache_ttl=3600,
    max_retries=3,
    backoff_factor=2.0,
)

# Automatic caching, retries, and error handling
user = client.get("/users/1")
print(user)
```

### POST Request
```python
from httpplus import quick_post

# POST with JSON body
response = quick_post(
    "https://jsonplaceholder.typicode.com/posts",
    json={"title": "My Post", "body": "Content", "userId": 1}
)
print(response)
```

### Async Operations
```python
from httpplus import AsyncHTTPClient
import asyncio

async def fetch_multiple():
    client = AsyncHTTPClient(base_url="https://jsonplaceholder.typicode.com")
    
    # Concurrent requests
    user = await client.get("/users/1")
    posts = await client.get("/posts/1")
    
    return user, posts

# Run async code
data = asyncio.run(fetch_multiple())
```

### Circuit Breaker for Resilience
```python
from httpplus import HTTPClient, CircuitBreaker, CircuitBreakerState

client = HTTPClient(base_url="https://jsonplaceholder.typicode.com")
breaker = CircuitBreaker(failure_threshold=5, reset_timeout=60)

# Add event handlers
breaker.add_on_open(lambda: print("Warning: Circuit opened - too many failures"))
breaker.add_on_close(lambda: print("Success: Circuit closed - service recovered"))

# Check circuit state
if breaker.state == CircuitBreakerState.CLOSED:
    try:
        response = client.get("/users/1")
        print(f"Response: {response}")
    except Exception as e:
        print(f"Circuit breaker failure: {e}")
```

### Response Validation
```python
from httpplus import HTTPClient, SchemaValidator

# Define JSON schema
user_schema = {
    "type": "object",
    "properties": {
        "id": {"type": "integer"},
        "name": {"type": "string"},
        "email": {"type": "string", "format": "email"}
    },
    "required": ["id", "name"]
}

validator = SchemaValidator()
client = HTTPClient(base_url="https://jsonplaceholder.typicode.com")

response = client.get("/users/1")
if validator.validate(response, user_schema):
    print("Response is valid")
else:
    print("Validation errors:", validator.get_errors())
```

### Rate Limiting
```python
from httpplus import RateLimiter

# Limit to 10 requests per second with burst of 20
limiter = RateLimiter(requests_per_second=10, burst_size=20)

for i in range(15):
    limiter.acquire()  # Waits if necessary
    print(f"Request {i+1} allowed")
```

### Session with Authentication
```python
from httpplus import HTTPClient

client = HTTPClient(base_url="https://api.example.com")
session = client.create_session("my_app", persist_cookies=False)

# Set auth token (auto-refreshes on expiry)
session.set_auth_token("your_token_here", expires_in=3600)

# Set custom headers
session.set_headers({
    "X-API-Version": "2.0",
    "Accept": "application/json"
})

# Use session for authenticated requests
response = client.get("/protected", session=session)
```

### File Download with Progress
```python
from httpplus import HTTPClient

client = HTTPClient()

def show_progress(current, total):
    percent = (current / total) * 100 if total > 0 else 0
    print(f"Downloaded {percent:.1f}%")

# Download file (requires valid URL)
client.download_file(
    "https://example.com/file.zip",
    "local_file.zip",
    progress_callback=show_progress
)
```

### Batch Requests
```python
from httpplus import HTTPClient

client = HTTPClient(base_url="https://jsonplaceholder.typicode.com")

requests_list = [
    {"method": "GET", "endpoint": "/users/1"},
    {"method": "GET", "endpoint": "/users/2"},
    {"method": "GET", "endpoint": "/users/3"},
]

results = client.batch_requests(requests_list)
successful = sum(1 for r in results if r['success'])
print(f"Successful: {successful}/{len(results)}")
```

### Health Checks
```python
from httpplus import HTTPClient

client = HTTPClient()
endpoints = [
    ("API", "https://jsonplaceholder.typicode.com"),
    ("Google", "https://google.com"),
]

for name, url in endpoints:
    status = "Healthy" if client.health_check(url) else "Unhealthy"
    print(f"{name}: {status}")
```

### Fallback URLs
```python
from httpplus import HTTPClient

client = HTTPClient()

try:
    response = client.get(
        "https://primary-api.example.com/data",
        fallback_urls=[
            "https://backup1.example.com/data",
            "https://backup2.example.com/data",
        ]
    )
except Exception as e:
    print(f"All URLs failed: {e}")
```

### Different Response Formats
```python
from httpplus import HTTPClient, ResponseFormat

client = HTTPClient()

# JSON response (default)
json_data = client.get(
    "https://jsonplaceholder.typicode.com/posts/1",
    response_format=ResponseFormat.JSON
)

# Text response
text_data = client.get(
    "https://example.com",
    response_format=ResponseFormat.TEXT
)

# Bytes response
bytes_data = client.get(
    "https://example.com",
    response_format=ResponseFormat.BYTES
)
```

## Configuration

HTTPPlus is highly configurable:

```python
HTTPClient(
    base_url="https://api.example.com",
    timeout=30,
    max_retries=3,
    backoff_factor=2.0,
    enable_caching=True,
    cache_ttl=3600,
    enable_logging=True,
)
```

### Environment Variables
```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

client = HTTPClient(
    base_url="https://api.example.com",
    enable_logging=True,
)
```

### Proxy Configuration
```python
client = HTTPClient(base_url="https://api.example.com")
session = client.create_session("proxy_session")

session.set_proxies({
    "http": "http://proxy.example.com:8080",
    "https": "https://proxy.example.com:8080",
})
```

## Error Handling

HTTPPlus provides a custom exception hierarchy:

```python
from httpplus import (
    HTTPClient,
    HTTPUtilException,
    HTTPRetryException,
    HTTPTimeoutException,
    HTTPCircuitBreakerException,
    HTTPValidationException,
)

client = HTTPClient(max_retries=3)

try:
    response = client.get("/users/1")
except HTTPRetryException as e:
    print(f"Max retries exceeded: {e}")
except HTTPTimeoutException as e:
    print(f"Request timeout: {e}")
except HTTPCircuitBreakerException as e:
    print(f"Circuit breaker open: {e}")
except HTTPValidationException as e:
    print(f"Validation error: {e}")
except HTTPUtilException as e:
    print(f"HTTP error: {e}")
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=httpplus tests/

# Run specific test
pytest tests/test_http_utils.py::TestHTTPClient
```

## Requirements

- **Python**: 3.7 or higher
- **Core Dependencies**: requests >= 2.25.0
- **Optional Dependencies**:
  - beautifulsoup4 >= 4.9.0 (for HTML parsing)
  - aiohttp >= 3.8.0 (for async support)
  - jsonschema >= 4.0.0 (for response validation)

## Documentation

- [FEATURES.md](FEATURES.md) - Complete feature documentation
- [examples/](examples/) - Code examples
- [tests/](tests/) - Test suite showing usage patterns

## Contributing

Contributions are welcome! Please ensure:
- All tests pass: `pytest`
- Code follows PEP 8
- New features include tests and documentation

## License

MIT License - See [LICENSE](LICENSE) file for details

## Support

- Documentation: [GitHub Wiki](https://github.com/vignesh476/httpplus/wiki)
- Bug Reports: [GitHub Issues](https://github.com/vignesh476/httpplus/issues)
- Discussions: [GitHub Discussions](https://github.com/vignesh476/httpplus/discussions)

---

**Made with love for developers building reliable applications**
