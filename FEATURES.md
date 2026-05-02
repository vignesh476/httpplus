# HTTPPlus Advanced Features Guide

Comprehensive guide to all advanced features in `httpplus`, explaining each feature's purpose and real-world applications.

## Table of Contents
1. [Smart Request Retry & Exponential Backoff](#smart-request-retry--exponential-backoff)
2. [Circuit Breaker Pattern](#circuit-breaker-pattern)
3. [Response Caching System](#response-caching-system)
4. [Rate Limiting](#rate-limiting)
5. [Session Management](#session-management)
6. [Fallback URLs](#fallback-urls)
7. [Response Format Parsing](#response-format-parsing)
8. [File Operations](#file-operations)
9. [Health Monitoring](#health-monitoring)
10. [Advanced Error Handling](#advanced-error-handling)
11. [Request/Response Logging](#requestresponse-logging)

---

## Smart Request Retry & Exponential Backoff

### Overview
Automatic retry mechanism with exponential backoff to handle transient failures in network requests.

### Why It's Needed
- Network connections are unreliable
- Transient failures (timeouts, temporary outages) are common
- Retrying immediately often fails, retrying with delay succeeds
- Exponential backoff prevents overwhelming struggling servers

### How It Works
```
Failure 1: Wait 1 second, then retry
Failure 2: Wait 2 seconds, then retry  
Failure 3: Wait 4 seconds, then retry
Failure 4: Wait 8 seconds, then retry
Failure 5: Max retries exceeded, raise exception
```

### Real-World Use Cases
1. **API Rate Limiting** - Service temporarily rejects requests
2. **Server Overload** - Brief spikes cause timeouts
3. **Network Issues** - Temporary connectivity problems
4. **Database Failover** - Switching to standby DB takes time

### Example Usage
```python
from httpplus import HTTPClient

# Configure retry behavior
client = HTTPClient(
    max_retries=5,           # Try up to 5 times
    backoff_factor=2.0,      # Double the wait each time
    timeout=30               # 30 second timeout per attempt
)

# Automatically retries with exponential backoff
data = client.get("/api/unreliable-endpoint")
```

### Configuration Options
- `max_retries` (int): Number of retry attempts (default: 3)
- `backoff_factor` (float): Exponential multiplier (default: 2.0)
- `timeout` (int): Timeout per attempt in seconds (default: 30)

### When NOT to Use Retries
- For non-idempotent operations (POST that creates resource)
- When rate limit has been hit
- For operations with state dependencies

---

## Circuit Breaker Pattern

### Overview
Fault tolerance pattern that prevents cascading failures by "breaking" the connection when service is unhealthy.

### Why It's Needed
- Prevents overwhelming a failing service
- Allows service time to recover
- Provides faster failure detection
- Improves system resilience

### States

```
CLOSED (Normal)
  ↓ (Failures accumulate)
OPEN (Failing)
  ↓ (After timeout)
HALF_OPEN (Testing)
  ↓ (Success/Failure)
CLOSED (Recovered) or OPEN (Still failing)
```

### Real-World Use Cases
1. **Microservices** - Prevent cascade of failures
2. **Database Failover** - Stop hammering broken DB
3. **API Degradation** - Graceful handling of service issues
4. **Load Shedding** - Reject requests when overwhelmed

### Example Usage
```python
from httpplus import HTTPClient, HTTPCircuitBreakerException

client = HTTPClient()  # Circuit breaker enabled by default

try:
    # After 5 failures in short time, circuit opens
    result = client.get("/endpoint")
except HTTPCircuitBreakerException:
    print("Service is temporarily unavailable")
    # Use cached data, fallback, or notify user
```

### Configuration
- `failure_threshold` (int): Failures before opening (default: 5)
- `reset_timeout` (int): Seconds before attempting recovery (default: 60)

---

## Response Caching System

### Overview
Thread-safe, TTL-based caching of HTTP responses to reduce load and improve performance.

### Why It's Needed
- Reduces server load
- Faster response times
- Reduces bandwidth usage
- Handles server unavailability gracefully

### How It Works
```
Request 1: Cache MISS → Fetch from server → Cache result
Request 2: Cache HIT → Return cached data (if not expired)
Request 3: Cache EXPIRED → Fetch from server → Update cache
```

### Real-World Use Cases
1. **Dashboard Widgets** - Cache data for 5 minutes
2. **Catalog/Inventory** - Cache product data hourly
3. **User Profiles** - Cache for 30 minutes
4. **Configuration** - Cache for session duration

### Example Usage
```python
from httpplus import HTTPClient

client = HTTPClient(
    enable_caching=True,
    cache_ttl=300  # 5 minute cache
)

# First call: Fetches from server
users = client.get("/users/1")

# Second call (within 5 min): Returns cached data
users = client.get("/users/1")  # Instant!

# Clear cache if needed
client.clear_cache()
```

### Cache Key Generation
Cache keys are based on:
- HTTP method (GET, POST, etc.)
- Full URL
- Query parameters
- Headers (when specified)

### Thread Safety
- All cache operations are thread-safe
- Safe for multi-threaded applications
- Uses locks for synchronization

---

## Rate Limiting

### Overview
Token bucket algorithm for controlling request rate and preventing API overload.

### Why It's Needed
- Respect API rate limits
- Prevent overwhelming services
- Fair resource sharing
- Comply with service ToS

### How It Works
```
Bucket capacity: 20 requests
Fill rate: 10 tokens per second

Request 1: 19 tokens left (instant)
Request 2: 18 tokens left (instant)
...
Wait time kicks in when bucket depleted
```

### Real-World Use Cases
1. **API Quotas** - Stay within API rate limits
2. **Resource Protection** - Limit load on database
3. **Fair Sharing** - Multiple consumers sharing resource
4. **Gradual Processing** - Spread work over time

### Example Usage
```python
from httpplus import HTTPClient

client = HTTPClient()
# Built-in rate limiter with defaults

# Process 100 requests at controlled rate
for i in range(100):
    result = client.get(f"/items/{i}")
    # Automatically rate-limited
```

### Configuration
- `requests_per_second` (float): Request rate
- `burst_size` (int): Maximum burst capacity

---

## Session Management

### Overview
Manage HTTP sessions with cookie persistence, authentication tokens, and custom headers.

### Why It's Needed
- Maintain session state across requests
- Handle authentication tokens
- Persist cookies between runs
- Manage custom headers per session

### Real-World Use Cases
1. **Authenticated APIs** - Maintain login session
2. **Token-Based Auth** - JWT or OAuth tokens
3. **Cookie-Based Sessions** - PHPSESSID, JSESSIONID
4. **Custom Headers** - User-Agent, API keys

### Example Usage
```python
from httpplus import HTTPClient

client = HTTPClient(base_url="https://api.example.com")
session = client.create_session("my_app", persist_cookies=True)

# Set authentication
session.set_auth_token("eyJhbGciOiJIUzI1NiIs...", expires_in=3600)

# Set custom headers
session.set_headers({
    "X-API-Version": "2.0",
    "User-Agent": "MyApp/1.0",
})

# Set proxies
session.set_proxies({
    "https": "https://proxy.company.com:8080"
})

# All requests use this session
users = client.get("/users")  # Uses token and headers
posts = client.get("/posts")
```

### Cookie Persistence
```python
session = client.create_session(
    "my_session",
    persist_cookies=True
)
# Cookies saved to disk and loaded on next run
```

### Token Refresh
```python
def refresh_token(old_token):
    # Call auth service to refresh
    response = requests.post("/auth/refresh", json={"token": old_token})
    return response.json()["new_token"]

session.refresh_token_if_needed(refresh_token)
```

---

## Fallback URLs

### Overview
Automatically try alternative endpoints when primary fails.

### Why It's Needed
- High availability
- Geographic redundancy
- Service migration
- Blue-green deployments

### How It Works
```
Try primary URL
  ↓ (Fails)
Try fallback URL 1
  ↓ (Fails)
Try fallback URL 2
  ↓ (Success)
Return result
```

### Real-World Use Cases
1. **CDN Failover** - Multiple CDN endpoints
2. **Geographic Distribution** - Regional servers
3. **Service Migration** - New URL while old works
4. **Disaster Recovery** - Backup servers

### Example Usage
```python
from httpplus import HTTPClient

client = HTTPClient()

result = client.get(
    "/api/data",
    fallback_urls=[
        "https://backup1.example.com/api/data",
        "https://backup2.example.com/api/data",
        "https://backup3.example.com/api/data",
    ]
)
```

---

## Response Format Parsing

### Overview
Automatic parsing of responses in multiple formats: JSON, XML, HTML, CSV, text, bytes.

### Why It's Needed
- Different APIs return different formats
- Automatic parsing saves boilerplate
- Error handling built-in
- Type-safe operations

### Supported Formats

#### JSON
```python
data = client.get("/api/data", response_format=ResponseFormat.JSON)
print(data['name'])  # Direct property access
```

#### XML
```python
from httpplus import ResponseFormat
root = client.get("/api/xml", response_format=ResponseFormat.XML)
title = root.find('.//title').text
```

#### HTML (requires beautifulsoup4)
```python
soup = client.get("https://example.com", response_format=ResponseFormat.HTML)
title = soup.find('h1').text
```

#### CSV
```python
rows = client.get("/data.csv", response_format=ResponseFormat.CSV)
for row in rows:
    print(row['name'], row['email'])
```

#### Plain Text
```python
text = client.get("/log.txt", response_format=ResponseFormat.TEXT)
```

#### Raw Bytes
```python
image_bytes = client.get("/image.jpg", response_format=ResponseFormat.BYTES)
with open("image.jpg", "wb") as f:
    f.write(image_bytes)
```

### Real-World Use Cases
1. **Multi-API Integration** - Different data formats
2. **Web Scraping** - Parse HTML responses
3. **Data Exports** - Download CSV/XML data
4. **File Downloads** - Raw bytes for binary files

---

## File Operations

### Overview
Upload and download files with progress tracking.

### Why It's Needed
- Large file handling
- Progress feedback to users
- Resume capability
- Memory efficiency (streaming)

### Download with Progress

```python
from httpplus import HTTPClient

client = HTTPClient()

def show_progress(current_bytes, total_bytes):
    percent = (current_bytes / total_bytes) * 100
    print(f"Downloaded: {percent:.1f}%")

client.download_file(
    "https://example.com/bigfile.zip",
    "local_bigfile.zip",
    progress_callback=show_progress
)
```

### Upload with Progress

```python
client.upload_file(
    "https://api.example.com/upload",
    "large_document.pdf",
    field_name="document",
    progress_callback=show_progress
)
```

### Real-World Use Cases
1. **Backup Systems** - Download large backups
2. **File Hosting** - Upload user files
3. **Media Processing** - Handle large videos
4. **Data Migration** - Transfer large datasets

---

## Health Monitoring

### Overview
Monitor endpoint availability with simple health checks.

### Why It's Needed
- Know when services are down
- Implement automatic failover
- Alert on issues
- Track uptime

### Example Usage

```python
from httpplus import HTTPClient

client = HTTPClient()

# Check single endpoint
is_healthy = client.health_check("https://api.example.com/health")

# Monitor multiple services
services = {
    "API": "https://api.example.com",
    "Database": "https://db.example.com",
    "Cache": "https://cache.example.com",
}

for name, url in services.items():
    status = "✓" if client.health_check(url) else "✗"
    print(f"{name}: {status}")
```

### Real-World Use Cases
1. **Monitoring Dashboard** - Service status display
2. **Automatic Failover** - Switch on unhealthy status
3. **Alerting System** - Notify ops team of issues
4. **Load Balancing** - Remove unhealthy nodes

---

## Advanced Error Handling

### Overview
Custom exception hierarchy for precise error handling.

### Exception Types

#### HTTPRetryException
When all retry attempts fail
```python
try:
    result = client.get("/endpoint")
except HTTPRetryException:
    print("Failed after 3 retry attempts")
```

#### HTTPTimeoutException
When request exceeds timeout
```python
try:
    result = client.get("/slow-endpoint", timeout=5)
except HTTPTimeoutException:
    print("Request took too long")
```

#### HTTPCircuitBreakerException
When circuit breaker is open
```python
try:
    result = client.get("/failing-endpoint")
except HTTPCircuitBreakerException:
    print("Service is down, try again later")
```

#### HTTPSchemaValidationException
When response schema validation fails
```python
try:
    result = client.get("/endpoint", response_schema=user_schema)
except HTTPSchemaValidationException:
    print("Response doesn't match expected schema")
```

#### HTTPParsingException
When response parsing fails
```python
try:
    result = client.get("/endpoint", response_format=ResponseFormat.JSON)
except HTTPParsingException:
    print("Invalid JSON response")
```

### Comprehensive Error Handling

```python
from httpplus import (
    HTTPClient,
    HTTPTimeoutException,
    HTTPRetryException,
    HTTPCircuitBreakerException,
)

client = HTTPClient()

try:
    result = client.get("/api/data")
except HTTPTimeoutException:
    print("Request timed out")
    # Use cached data
except HTTPCircuitBreakerException:
    print("Service temporarily unavailable")
    # Use cached data
except HTTPRetryException:
    print("Failed after retries")
    # Use fallback
except Exception as e:
    print(f"Unexpected error: {e}")
    # Handle gracefully
```

### Real-World Use Cases
1. **Graceful Degradation** - Fall back to cached/default data
2. **User Feedback** - Display appropriate error messages
3. **Retry Logic** - Implement custom retry strategies
4. **Monitoring** - Track error patterns

---

## Request/Response Logging

### Overview
Built-in logging for debugging and monitoring requests.

### Why It's Needed
- Debug network issues
- Monitor performance
- Track API usage
- Troubleshoot failures

### Enable Logging

```python
import logging
from httpplus import HTTPClient

# Configure logging level
logging.basicConfig(level=logging.DEBUG)

client = HTTPClient(enable_logging=True)

# Logs will show:
# - Request method, URL, params
# - Response status, timing, size
# - Retries and delays
# - Cache hits/misses
```

### Log Output Example
```
DEBUG:http_utils.HTTPClient:GET https://api.example.com/users
DEBUG:http_utils.HTTPClient:Params: {'page': 1}
DEBUG:http_utils.HTTPClient:Status: 200, Elapsed: 0.25s, Size: 2048 bytes
DEBUG:http_utils.HTTPClient:Cache HIT: https://api.example.com/users
DEBUG:http_utils.HTTPClient:Rate limit: waited 0.50s
```

### Real-World Use Cases
1. **Development** - Debug API integration
2. **Production Monitoring** - Track request patterns
3. **Performance Analysis** - Identify slow endpoints
4. **Troubleshooting** - Root cause analysis

---

## Summary: Choosing Features

| Use Case | Feature |
|----------|---------|
| Unreliable networks | Smart Retry + Exponential Backoff |
| Microservices | Circuit Breaker |
| Frequently accessed data | Response Caching |
| Rate-limited APIs | Rate Limiting |
| Authenticated APIs | Session Management |
| Multi-region services | Fallback URLs |
| Mixed API formats | Response Format Parsing |
| Large files | File Operations |
| Service monitoring | Health Monitoring |
| Debugging issues | Error Handling + Logging |

---

## Performance Tips

1. **Cache Strategy**: Cache GET requests, avoid caching POST responses
2. **Batch Processing**: Use batch_requests for multiple endpoints
3. **Connection Reuse**: Use sessions for multiple requests
4. **Rate Limiting**: Respect API limits, use rate limiter
5. **File Streaming**: Use download_file for large files instead of get()
6. **Health Checks**: Cache health check results for 30-60 seconds

---

**Start using these advanced features to build robust, production-ready applications!**
