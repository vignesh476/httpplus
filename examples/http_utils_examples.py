"""
Real-world examples of using http_utils

Run any example:
  python examples/example_name.py
"""

# Example 1: GitHub API Client
print("=" * 60)
print("Example 1: GitHub API Client with Caching")
print("=" * 60)

from httpplus import HTTPClient, ResponseFormat

def github_api_example():
    """Fetch GitHub user information with caching"""
    
    client = HTTPClient(
        base_url="https://jsonplaceholder.typicode.com",
        enable_caching=True,
        cache_ttl=300  # 5 minute cache
    )
    
    try:
        # These calls will be cached
        users = [
            client.get("/users/github", response_format=ResponseFormat.JSON),
            client.get("/users/google", response_format=ResponseFormat.JSON),
            client.get("/users/microsoft", response_format=ResponseFormat.JSON),
        ]
        
    
    except Exception as e:
        print(f"Error: {e}")

# Example 2: Batch API Requests
print("\n" + "=" * 60)
print("Example 2: Batch API Requests")
print("=" * 60)

def batch_requests_example():
    """Make multiple requests efficiently"""
    
    client = HTTPClient(base_url="https://jsonplaceholder.typicode.com")
    
    requests_list = [
        {"method": "GET", "endpoint": "/posts/1"},
        {"method": "GET", "endpoint": "/posts/2"},
        {"method": "GET", "endpoint": "/comments/1"},
    ]
    
    results = client.batch_requests(requests_list)
    
    for i, result in enumerate(results):
        if result['success']:
            data = result['data']
            if isinstance(data, dict):
                print(f"Request {i+1}: {data.get('title', 'Data retrieved')[:50]}")
            else:
                print(f"Request {i+1}: Success")
        else:
            print(f"Request {i+1}: Error - {result['error']}")

# Example 3: API with Fallback URLs
print("\n" + "=" * 60)
print("Example 3: Fallback URLs for High Availability")
print("=" * 60)

def fallback_urls_example():
    """Use fallback URLs if primary API is down"""
    
    client = HTTPClient()
    
    try:
        result = client.get(
            "https://jsonplaceholder.typicode.com/posts/1",
            fallback_urls=[
                "https://jsonplaceholder.typicode.com/posts/2",
                "https://jsonplaceholder.typicode.com/posts/3",
            ]
        )
        print(f"Retrieved: {result.get('title', 'Data')[:60]}")
    except Exception as e:
        print(f"Error: {e}")

# Example 4: Rate-Limited API Calls
print("\n" + "=" * 60)
print("Example 4: Rate-Limited API Calls")
print("=" * 60)

def rate_limited_example():
    """Make requests with rate limiting"""
    
    import time
    
    client = HTTPClient()
    
    start = time.time()
    
    # These will be rate-limited automatically
    for i in range(5):
        try:
            result = client.get(f"https://jsonplaceholder.typicode.com/posts/{i+1}")
            print(f"Post {i+1}: Retrieved")
        except Exception as e:
            print(f"Post {i+1}: Error")
    
    elapsed = time.time() - start
    print(f"Total time: {elapsed:.2f}s")

# Example 5: Session Management
print("\n" + "=" * 60)
print("Example 5: Session with Cookies")
print("=" * 60)

def session_example():
    """Use session with persistent cookies"""
    
    client = HTTPClient()
    session = client.create_session("my_app", persist_cookies=True)
    
    # Set custom headers
    session.set_headers({
        "User-Agent": "MyApp/1.0",
        "Accept": "application/json"
    })
    
    print(f"Session created: {session.session_name}")
    print("Custom headers set")

# Example 6: Health Checking
print("\n" + "=" * 60)
print("Example 6: Health Checking Multiple Endpoints")
print("=" * 60)

def health_check_example():
    """Monitor multiple endpoints"""
    
    endpoints = [
        ("jsonplaceholder.typicode.com", "https://jsonplaceholder.typicode.com"),
        ("google.com", "https://google.com"),
        ("github.com", "https://github.com"),
    ]
    
    client = HTTPClient()
    
    for name, url in endpoints:
        is_healthy = client.health_check(url, timeout=5)
        status = "✓ Online" if is_healthy else "✗ Offline"
        print(f"{name:30} {status}")

# Example 7: Error Handling
print("\n" + "=" * 60)
print("Example 7: Comprehensive Error Handling")
print("=" * 60)

def error_handling_example():
    """Handle different types of errors"""
    
    from httpplus import (
        HTTPClient,
        HTTPRetryException,
        HTTPTimeoutException,
        HTTPCircuitBreakerException,
    )
    
    client = HTTPClient(
        timeout=5,
        max_retries=2,
        backoff_factor=2.0
    )
    
    urls = [
        ("Valid", "https://jsonplaceholder.typicode.com/posts/1"),
        ("Timeout", "https://httpbin.org/delay/10"),  # Will timeout
        ("Not Found", "https://jsonplaceholder.typicode.com/posts/99999"),
    ]
    
    for name, url in urls:
        try:
            result = client.get(url)
            print(f"{name:15} ✓ Success")
        except HTTPTimeoutException:
            print(f"{name:15} ✗ Timeout")
        except HTTPRetryException:
            print(f"{name:15} ✗ Retry failed")
        except HTTPCircuitBreakerException:
            print(f"{name:15} ✗ Circuit open")
        except Exception as e:
            print(f"{name:15} ✗ {type(e).__name__}")

# Example 8: Different Response Formats
print("\n" + "=" * 60)
print("Example 8: Parsing Different Response Formats")
print("=" * 60)

def response_format_example():
    """Parse responses in different formats"""
    
    from httpplus import HTTPClient, ResponseFormat
    
    client = HTTPClient()
    
    # JSON response
    json_data = client.get(
        "https://jsonplaceholder.typicode.com/posts/1",
        response_format=ResponseFormat.JSON
    )
    print(f"JSON: {json_data.get('title', 'N/A')[:40]}")
    
    # Text response
    text_data = client.get(
        "https://example.com",
        response_format=ResponseFormat.TEXT
    )
    print(f"Text: First 50 chars of HTML retrieved")
    
    # Bytes response
    bytes_data = client.get(
        "https://example.com",
        response_format=ResponseFormat.BYTES
    )
    print(f"Bytes: {len(bytes_data)} bytes retrieved")

# Example 9: Circuit Breaker
print("\n" + "=" * 60)
print("Example 9: Circuit Breaker for Fault Tolerance")
print("=" * 60)

def circuit_breaker_example():
    """Demonstrate circuit breaker pattern"""
    
    from httpplus import HTTPClient, HTTPCircuitBreakerException
    
    # Simulate a failing service
    client = HTTPClient()
    
    print("Circuit breaker enabled by default")
    print("After 5 consecutive failures, circuit opens")
    print("Circuit resets after 60 seconds of inactivity")

# Example 10: File Operations
print("\n" + "=" * 60)
print("Example 10: File Download with Progress")
print("=" * 60)

def file_download_example():
    """Download file with progress tracking"""
    
    from httpplus import HTTPClient
    import os
    
    client = HTTPClient()
    
    def progress(current, total):
        percent = (current / total * 100) if total > 0 else 0
        bar_length = 30
        filled = int(bar_length * current // total) if total > 0 else 0
        bar = '█' * filled + '░' * (bar_length - filled)
        print(f"\rDownloading: |{bar}| {percent:.1f}%", end="", flush=True)
    
    try:
        # Example: Download a small file
        print("Download example (set up your own URL)")
        # client.download_file(
        #     "https://example.com/largefile.zip",
        #     "downloaded_file.zip",
        #     progress_callback=progress
        # )
        print("\nImplement with your own file URL")
    except Exception as e:
        print(f"Error: {e}")

# Example 11: API Testing
print("\n" + "=" * 60)
print("Example 11: Testing Multiple API Endpoints")
print("=" * 60)

def api_testing_example():
    """Test multiple endpoints and collect metrics"""
    
    from httpplus import HTTPClient
    import time
    
    client = HTTPClient(base_url="https://jsonplaceholder.typicode.com")
    
    endpoints = ["/posts/1", "/users/1", "/comments/1"]
    
    for endpoint in endpoints:
        start = time.time()
        try:
            result = client.get(endpoint)
            elapsed = time.time() - start
            print(f"{endpoint:20} ✓ {elapsed*1000:6.2f}ms")
        except Exception as e:
            print(f"{endpoint:20} ✗ Error")

# Example 12: Custom Headers and Authentication
print("\n" + "=" * 60)
print("Example 12: Custom Headers and Auth")
print("=" * 60)

def custom_headers_example():
    """Use custom headers and authentication"""
    
    from httpplus import HTTPClient
    
    client = HTTPClient(base_url="https://api.example.com")
    session = client.create_session("api_client")
    
    # Set auth token
    session.set_auth_token("your-secret-token-here")
    
    # Set custom headers
    session.set_headers({
        "X-API-Version": "2.0",
        "X-Client-ID": "my-app-123",
    })
    
    print("Session configured with:")
    print("  - Authorization token")
    print("  - Custom headers")
    print("  - Ready for API calls")

# Run all examples
if __name__ == "__main__":
    examples = [
        ("GitHub API Example", github_api_example),
        ("Batch Requests", batch_requests_example),
        ("Fallback URLs", fallback_urls_example),
        ("Rate Limiting", rate_limited_example),
        ("Session Management", session_example),
        ("Health Checks", health_check_example),
        ("Error Handling", error_handling_example),
        ("Response Formats", response_format_example),
        ("Circuit Breaker", circuit_breaker_example),
        ("File Download", file_download_example),
        ("API Testing", api_testing_example),
        ("Custom Headers", custom_headers_example),
    ]
    
    print("\n" + "=" * 60)
    print("HTTP_UTILS EXAMPLES - Real-world Usage Scenarios")
    print("=" * 60 + "\n")
    
    # Uncomment to run specific examples
    # github_api_example()
    # batch_requests_example()
    # health_check_example()
    # error_handling_example()
    # api_testing_example()
    
    print("\nTo run an example:")
    print("  python -c \"from examples.http_utils_examples import github_api_example; github_api_example()\"")
    print("\nOr call individual functions directly in Python")
