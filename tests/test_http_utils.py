"""
Tests for http_utils module
Run with: python -m pytest tests/ -v
"""

import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock
import requests

from httpkit.http_utils import (
    HTTPClient,
    ResponseFormat,
    ResponseCache,
    CircuitBreaker,
    RateLimiter,
    Session,
    ResponseParser,
    HTTPRetryException,
    HTTPCircuitBreakerException,
    HTTPTimeoutException,
)


class TestResponseCache:
    """Tests for ResponseCache"""
    
    def test_cache_set_and_get(self):
        cache = ResponseCache(ttl=10)
        data = {"key": "value"}
        cache.set("GET", "http://example.com", data)
        
        result = cache.get("GET", "http://example.com")
        assert result == data
    
    def test_cache_ttl_expiry(self):
        cache = ResponseCache(ttl=1)
        data = {"key": "value"}
        cache.set("GET", "http://example.com", data)
        
        time.sleep(1.1)
        result = cache.get("GET", "http://example.com")
        assert result is None
    
    def test_cache_clear(self):
        cache = ResponseCache()
        cache.set("GET", "http://example.com", {"data": "test"})
        cache.clear()
        
        result = cache.get("GET", "http://example.com")
        assert result is None


class TestCircuitBreaker:
    """Tests for CircuitBreaker"""
    
    def test_circuit_breaker_closed_state(self):
        cb = CircuitBreaker(failure_threshold=3)
        
        def success_func():
            return "success"
        
        result = cb.call(success_func)
        assert result == "success"
    
    def test_circuit_breaker_opens_on_failures(self):
        cb = CircuitBreaker(failure_threshold=2)
        
        def failing_func():
            raise Exception("Test error")
        
        # First failure
        with pytest.raises(Exception):
            cb.call(failing_func)
        
        # Second failure - circuit opens
        with pytest.raises(Exception):
            cb.call(failing_func)
        
        # Third call - circuit is open
        with pytest.raises(HTTPCircuitBreakerException):
            cb.call(failing_func)
    
    def test_circuit_breaker_recovery(self):
        cb = CircuitBreaker(failure_threshold=2, reset_timeout=1)
        
        def failing_func():
            raise Exception("Test error")
        
        # Open circuit
        with pytest.raises(Exception):
            cb.call(failing_func)
        with pytest.raises(Exception):
            cb.call(failing_func)
        
        # Circuit is open
        with pytest.raises(HTTPCircuitBreakerException):
            cb.call(failing_func)
        
        # Wait and try again
        time.sleep(1.1)
        
        def success_func():
            return "recovered"
        
        result = cb.call(success_func)
        assert result == "recovered"


class TestRateLimiter:
    """Tests for RateLimiter"""
    
    def test_rate_limiter_basic(self):
        limiter = RateLimiter(requests_per_second=10)
        
        start = time.time()
        for _ in range(5):
            limiter.acquire()
        elapsed = time.time() - start
        
        # Should complete quickly with burst
        assert elapsed < 1.0
    
    def test_rate_limiter_throttles(self):
        limiter = RateLimiter(requests_per_second=2, burst_size=1)
        
        start = time.time()
        limiter.acquire()
        limiter.acquire()
        elapsed = time.time() - start
        
        # Should take about 0.5 seconds
        assert elapsed > 0.4


class TestSession:
    """Tests for Session"""
    
    def test_session_creation(self):
        session = Session("test_session")
        assert session.session_name == "test_session"
        assert session.session is not None
    
    def test_set_auth_token(self):
        session = Session("test")
        session.set_auth_token("test_token", expires_in=3600)
        
        assert session.auth_token == "test_token"
        assert session.token_expiry is not None
        assert "Authorization" in session.session.headers
    
    def test_set_custom_headers(self):
        session = Session("test")
        headers = {"X-Custom": "value"}
        session.set_headers(headers)
        
        assert session.session.headers.get("X-Custom") == "value"


class TestResponseParser:
    """Tests for ResponseParser"""
    
    def test_parse_json(self):
        response = Mock()
        response.json.return_value = {"key": "value"}
        
        result = ResponseParser.parse(response, ResponseFormat.JSON)
        assert result == {"key": "value"}
    
    def test_parse_text(self):
        response = Mock()
        response.text = "Plain text"
        
        result = ResponseParser.parse(response, ResponseFormat.TEXT)
        assert result == "Plain text"
    
    def test_parse_bytes(self):
        response = Mock()
        response.content = b"bytes content"
        
        result = ResponseParser.parse(response, ResponseFormat.BYTES)
        assert result == b"bytes content"


class TestHTTPClient:
    """Tests for HTTPClient"""
    
    def test_client_initialization(self):
        client = HTTPClient(base_url="https://api.example.com")
        assert client.base_url == "https://api.example.com"
        assert client.timeout == 30
        assert client.max_retries == 3
    
    def test_build_url(self):
        client = HTTPClient(base_url="https://api.example.com")
        url = client._build_url("/users")
        assert url == "https://api.example.com/users"
    
    @patch('requests.request')
    def test_get_request(self, mock_request):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 1, "name": "Test"}
        mock_request.return_value = mock_response
        
        client = HTTPClient(enable_caching=False, enable_logging=False)
        result = client.get("/test")
        
        assert result == {"id": 1, "name": "Test"}
        mock_request.assert_called_once()
    
    @patch('requests.request')
    def test_retry_on_failure(self, mock_request):
        # First two calls fail, third succeeds
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        
        mock_request.side_effect = [
            requests.ConnectionError("Connection failed"),
            requests.ConnectionError("Connection failed"),
            mock_response,
        ]
        
        client = HTTPClient(max_retries=3, enable_logging=False)
        result = client.get("/test")
        
        assert result == {"success": True}
        assert mock_request.call_count == 3
    
    @patch('requests.request')
    def test_cache_get_request(self, mock_request):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"cached": True}
        mock_request.return_value = mock_response
        
        client = HTTPClient(enable_caching=True, enable_logging=False)
        
        # First call
        result1 = client.get("/test")
        # Second call (should be cached)
        result2 = client.get("/test")
        
        assert result1 == result2
        # Should only be called once due to cache
        assert mock_request.call_count == 1
    
    @patch('requests.head')
    def test_health_check(self, mock_head):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_head.return_value = mock_response
        
        client = HTTPClient()
        result = client.health_check("/health")
        
        assert result is True
        mock_head.assert_called_once()


class TestQuickFunctions:
    """Tests for quick convenience functions"""
    
    @patch('requests.request')
    def test_quick_get(self, mock_request):
        from httpkit.http_utils import quick_get
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"quick": "test"}
        mock_response.content = b'{"quick": "test"}'
        mock_response.text = '{"quick": "test"}'
        mock_request.return_value = mock_response
        
        result = quick_get("https://api.example.com/test")
        assert result == {"quick": "test"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
