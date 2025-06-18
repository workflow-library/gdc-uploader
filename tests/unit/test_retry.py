"""Unit tests for retry module."""

import pytest
import time
import requests
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add path for imports
import sys
sys.path.insert(0, '/workspaces/gdc-uploader-agents/agent-2-common-utilities/src')
sys.path.append('/workspaces/gdc-uploader-agents/agent-1-core-architecture/specs/interfaces')

from gdc_uploader.core.retry import (
    RetryStrategy,
    RetryConfig,
    RetryStatistics,
    RetryManager,
    retry,
    RetryableUpload,
    SmartRetry,
    with_retry_stats,
    RETRY_CONFIG_DEFAULT,
    RETRY_CONFIG_AGGRESSIVE,
    RETRY_CONFIG_API_CALLS
)
from exceptions_interface import UploadError, UploadTimeoutError


class TestRetryConfig:
    """Test RetryConfig class."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = RetryConfig()
        
        assert config.max_attempts == 3
        assert config.strategy == RetryStrategy.EXPONENTIAL
        assert config.initial_delay == 1.0
        assert config.max_delay == 300.0
        assert config.jitter is True
        
    def test_should_retry_basic(self):
        """Test basic retry decision logic."""
        config = RetryConfig(
            retry_on=(ValueError, TypeError),
            dont_retry_on=(RuntimeError,)
        )
        
        assert config.should_retry(ValueError("test"))
        assert config.should_retry(TypeError("test"))
        assert not config.should_retry(RuntimeError("test"))
        assert not config.should_retry(Exception("test"))  # Not in retry_on
        
    def test_should_retry_http_codes(self):
        """Test HTTP status code retry logic."""
        config = RetryConfig(retry_http_codes=[500, 503])
        
        # Mock requests exception with response
        exc = requests.exceptions.RequestException()
        exc.response = Mock(status_code=500)
        assert config.should_retry(exc)
        
        exc.response.status_code = 404
        assert not config.should_retry(exc)
        
    def test_calculate_delay_immediate(self):
        """Test immediate retry strategy."""
        config = RetryConfig(strategy=RetryStrategy.IMMEDIATE)
        
        assert config.calculate_delay(1) == 0.0
        assert config.calculate_delay(5) == 0.0
        
    def test_calculate_delay_linear(self):
        """Test linear backoff strategy."""
        config = RetryConfig(
            strategy=RetryStrategy.LINEAR,
            initial_delay=2.0,
            jitter=False
        )
        
        assert config.calculate_delay(1) == 2.0
        assert config.calculate_delay(2) == 4.0
        assert config.calculate_delay(3) == 6.0
        
    def test_calculate_delay_exponential(self):
        """Test exponential backoff strategy."""
        config = RetryConfig(
            strategy=RetryStrategy.EXPONENTIAL,
            initial_delay=1.0,
            backoff_base=2.0,
            jitter=False
        )
        
        assert config.calculate_delay(1) == 1.0  # 1 * 2^0
        assert config.calculate_delay(2) == 2.0  # 1 * 2^1
        assert config.calculate_delay(3) == 4.0  # 1 * 2^2
        assert config.calculate_delay(4) == 8.0  # 1 * 2^3
        
    def test_calculate_delay_fibonacci(self):
        """Test Fibonacci backoff strategy."""
        config = RetryConfig(
            strategy=RetryStrategy.FIBONACCI,
            initial_delay=1.0,
            jitter=False
        )
        
        assert config.calculate_delay(1) == 1.0
        assert config.calculate_delay(2) == 1.0
        assert config.calculate_delay(3) == 2.0
        assert config.calculate_delay(4) == 3.0
        assert config.calculate_delay(5) == 5.0
        
    def test_max_delay_cap(self):
        """Test maximum delay capping."""
        config = RetryConfig(
            strategy=RetryStrategy.EXPONENTIAL,
            initial_delay=1.0,
            max_delay=5.0,
            jitter=False
        )
        
        assert config.calculate_delay(10) == 5.0  # Would be 512 without cap
        
    def test_jitter(self):
        """Test jitter application."""
        config = RetryConfig(
            strategy=RetryStrategy.LINEAR,
            initial_delay=10.0,
            jitter=True,
            jitter_factor=0.1
        )
        
        # Run multiple times to test randomness
        delays = [config.calculate_delay(1) for _ in range(10)]
        
        # All should be within 10% of 10.0 (9.0 to 11.0)
        assert all(9.0 <= d <= 11.0 for d in delays)
        # Should have some variation
        assert len(set(delays)) > 1


class TestRetryStatistics:
    """Test RetryStatistics class."""
    
    def test_record_attempt(self):
        """Test recording attempts."""
        stats = RetryStatistics()
        
        stats.record_attempt(success=True, delay=1.0)
        assert stats.total_attempts == 1
        assert stats.successful_attempts == 1
        assert stats.failed_attempts == 0
        assert stats.total_delay_time == 1.0
        
        stats.record_attempt(success=False, delay=2.0, error=ValueError("test"))
        assert stats.total_attempts == 2
        assert stats.successful_attempts == 1
        assert stats.failed_attempts == 1
        assert stats.total_delay_time == 3.0
        assert stats.errors_encountered["ValueError"] == 1
        
    def test_success_rate(self):
        """Test success rate calculation."""
        stats = RetryStatistics()
        
        assert stats.success_rate() == 0.0  # No attempts
        
        stats.record_attempt(success=True)
        assert stats.success_rate() == 100.0
        
        stats.record_attempt(success=False)
        assert stats.success_rate() == 50.0
        
    def test_average_attempts_to_success(self):
        """Test average attempts calculation."""
        stats = RetryStatistics()
        
        assert stats.average_attempts_to_success() == float('inf')
        
        # 3 attempts for first success
        stats.record_attempt(success=False)
        stats.record_attempt(success=False)
        stats.record_attempt(success=True)
        
        assert stats.average_attempts_to_success() == 3.0
        
        # 1 attempt for second success
        stats.record_attempt(success=True)
        
        assert stats.average_attempts_to_success() == 2.0


class TestRetryManager:
    """Test RetryManager class."""
    
    def test_successful_execution(self):
        """Test successful execution without retries."""
        manager = RetryManager()
        
        def success_func():
            return "success"
            
        result = manager.execute(success_func)
        assert result == "success"
        assert manager.statistics.total_attempts == 1
        assert manager.statistics.successful_attempts == 1
        
    def test_retry_on_failure(self):
        """Test retry on failure."""
        config = RetryConfig(
            max_attempts=3,
            strategy=RetryStrategy.IMMEDIATE
        )
        manager = RetryManager(config)
        
        call_count = 0
        
        def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Fail")
            return "success"
            
        result = manager.execute(failing_func)
        assert result == "success"
        assert call_count == 3
        assert manager.statistics.total_attempts == 3
        assert manager.statistics.successful_attempts == 1
        assert manager.statistics.failed_attempts == 2
        
    def test_max_attempts_exhausted(self):
        """Test when all retry attempts are exhausted."""
        config = RetryConfig(
            max_attempts=2,
            strategy=RetryStrategy.IMMEDIATE
        )
        manager = RetryManager(config)
        
        def always_fail():
            raise ValueError("Always fails")
            
        with pytest.raises(ValueError, match="Always fails"):
            manager.execute(always_fail)
            
        assert manager.statistics.total_attempts == 2
        assert manager.statistics.failed_attempts == 2
        
    def test_non_retryable_exception(self):
        """Test exception that should not be retried."""
        config = RetryConfig(
            retry_on=(ValueError,),
            max_attempts=3
        )
        manager = RetryManager(config)
        
        call_count = 0
        
        def runtime_error_func():
            nonlocal call_count
            call_count += 1
            raise RuntimeError("Should not retry")
            
        with pytest.raises(RuntimeError):
            manager.execute(runtime_error_func)
            
        assert call_count == 1  # Should not retry
        
    def test_retry_callback(self):
        """Test retry callback execution."""
        callback_calls = []
        
        def on_retry(exc, attempt):
            callback_calls.append((type(exc).__name__, attempt))
            
        config = RetryConfig(
            max_attempts=3,
            strategy=RetryStrategy.IMMEDIATE,
            on_retry_callback=on_retry
        )
        manager = RetryManager(config)
        
        attempt_count = 0
        
        def failing_func():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ValueError("Fail")
            return "success"
            
        manager.execute(failing_func)
        
        assert len(callback_calls) == 2
        assert callback_calls[0] == ("ValueError", 1)
        assert callback_calls[1] == ("ValueError", 2)


class TestRetryDecorator:
    """Test retry decorator."""
    
    def test_basic_decorator(self):
        """Test basic decorator usage."""
        call_count = 0
        
        @retry(max_attempts=3, strategy=RetryStrategy.IMMEDIATE)
        def decorated_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Fail once")
            return "success"
            
        result = decorated_func()
        assert result == "success"
        assert call_count == 2
        
    def test_decorator_with_config_object(self):
        """Test decorator with RetryConfig object."""
        config = RetryConfig(
            max_attempts=2,
            strategy=RetryStrategy.LINEAR,
            initial_delay=0.1
        )
        
        @retry(config)
        def decorated_func():
            raise ValueError("Always fails")
            
        with pytest.raises(ValueError):
            decorated_func()
            
    def test_decorator_preserves_function_attributes(self):
        """Test that decorator preserves function attributes."""
        @retry(max_attempts=2)
        def my_func():
            """My function docstring."""
            return "result"
            
        assert my_func.__name__ == "my_func"
        assert my_func.__doc__ == "My function docstring."
        assert hasattr(my_func, "retry_config")
        
    def test_decorator_with_arguments(self):
        """Test decorator on function with arguments."""
        @retry(max_attempts=2, strategy=RetryStrategy.IMMEDIATE)
        def add(a, b):
            if a == 0:
                raise ValueError("a cannot be zero")
            return a + b
            
        assert add(1, 2) == 3
        
        with pytest.raises(ValueError):
            add(0, 2)


class TestRetryableUpload:
    """Test RetryableUpload context manager."""
    
    def test_successful_upload(self):
        """Test successful upload context."""
        upload = RetryableUpload("test.txt", max_attempts=3)
        
        with upload:
            assert upload.attempt == 1
            assert upload.start_byte == 0
            
        assert upload.should_retry() is True
        
    def test_retry_on_upload_error(self):
        """Test retry behavior on upload error."""
        upload = RetryableUpload("test.txt", max_attempts=3)
        
        # First attempt fails
        try:
            with upload:
                raise UploadError("Upload failed")
        except UploadError:
            pass
            
        assert upload.attempt == 1
        assert upload.should_retry() is True
        
        # Second attempt
        with upload:
            assert upload.attempt == 2
            
    def test_max_attempts_reached(self):
        """Test when max attempts are reached."""
        upload = RetryableUpload("test.txt", max_attempts=2)
        
        # Use up attempts
        upload.attempt = 2
        
        assert upload.should_retry() is False


class TestSmartRetry:
    """Test SmartRetry class."""
    
    def test_adapt_config_timeout_errors(self):
        """Test adaptation for timeout errors."""
        smart = SmartRetry()
        initial_delay = smart.config.initial_delay
        initial_max_delay = smart.config.max_delay
        
        # Add several timeout errors
        for _ in range(5):
            smart.record_error(TimeoutError("Timeout"))
            
        smart.adapt_config()
        
        # Should increase delays
        assert smart.config.initial_delay > initial_delay
        assert smart.config.max_delay > initial_max_delay
        
    def test_adapt_config_rate_limit(self):
        """Test adaptation for rate limit errors."""
        smart = SmartRetry()
        
        # Add rate limit error
        exc = requests.exceptions.RequestException()
        exc.response = Mock(status_code=429)
        smart.record_error(exc)
        
        smart.adapt_config()
        
        # Should switch to exponential backoff
        assert smart.config.strategy == RetryStrategy.EXPONENTIAL
        assert smart.config.backoff_base == 2.5
        
    def test_history_limit(self):
        """Test that history is limited."""
        smart = SmartRetry()
        
        # Add many errors
        for i in range(150):
            smart.record_error(ValueError(f"Error {i}"))
            
        assert len(smart.error_history) == 100  # Limited to 100
        
        # Add many successes
        for i in range(150):
            smart.record_success()
            
        assert len(smart.success_history) == 100  # Limited to 100


class TestPredefinedConfigs:
    """Test predefined retry configurations."""
    
    def test_default_config(self):
        """Test default configuration."""
        assert RETRY_CONFIG_DEFAULT.max_attempts == 3
        assert RETRY_CONFIG_DEFAULT.strategy == RetryStrategy.EXPONENTIAL
        
    def test_aggressive_config(self):
        """Test aggressive configuration."""
        assert RETRY_CONFIG_AGGRESSIVE.max_attempts == 10
        assert RETRY_CONFIG_AGGRESSIVE.initial_delay == 0.5
        assert RETRY_CONFIG_AGGRESSIVE.backoff_base == 1.5
        
    def test_api_calls_config(self):
        """Test API calls configuration."""
        assert 429 in RETRY_CONFIG_API_CALLS.retry_http_codes
        assert requests.exceptions.RequestException in RETRY_CONFIG_API_CALLS.retry_on