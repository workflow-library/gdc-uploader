"""Retry logic module for GDC uploader.

This module provides configurable retry mechanisms with:
- Exponential backoff with jitter
- Different retry strategies (immediate, exponential, linear)
- Retry statistics and logging
- Conditional retry based on error types
"""

import time
import random
import logging
import functools
from typing import Callable, Optional, Tuple, Type, Union, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
import requests
from datetime import datetime

# Import from local modules
from .exceptions import GDCUploaderError, UploadError, UploadTimeoutError

logger = logging.getLogger(__name__)


class RetryStrategy(Enum):
    """Available retry strategies."""
    
    IMMEDIATE = "immediate"      # No delay between retries
    LINEAR = "linear"            # Linear backoff (delay * attempt)
    EXPONENTIAL = "exponential"  # Exponential backoff (base ** attempt)
    FIBONACCI = "fibonacci"      # Fibonacci sequence delays


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    
    # Basic retry settings
    max_attempts: int = 3
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    
    # Delay configuration
    initial_delay: float = 1.0      # Base delay in seconds
    max_delay: float = 300.0        # Maximum delay between retries (5 minutes)
    jitter: bool = True             # Add randomization to delays
    jitter_factor: float = 0.1      # Jitter range (0.1 = ±10%)
    
    # Exponential backoff settings
    backoff_base: float = 2.0       # Base for exponential backoff
    backoff_multiplier: float = 1.0 # Multiplier for calculated delay
    
    # Error handling
    retry_on: Tuple[Type[Exception], ...] = field(default_factory=lambda: (Exception,))
    dont_retry_on: Tuple[Type[Exception], ...] = field(default_factory=tuple)
    
    # HTTP-specific settings
    retry_http_codes: List[int] = field(default_factory=lambda: [
        408,  # Request Timeout
        429,  # Too Many Requests
        500,  # Internal Server Error
        502,  # Bad Gateway
        503,  # Service Unavailable
        504,  # Gateway Timeout
    ])
    
    # Logging and callbacks
    log_retries: bool = True
    on_retry_callback: Optional[Callable[[Exception, int], None]] = None
    
    def should_retry(self, exception: Exception) -> bool:
        """Determine if an exception should trigger a retry.
        
        Args:
            exception: The exception to check
            
        Returns:
            True if should retry, False otherwise
        """
        # Check don't retry list first
        if isinstance(exception, self.dont_retry_on):
            return False
            
        # Check retry list
        if not isinstance(exception, self.retry_on):
            return False
            
        # Check HTTP status codes for requests exceptions
        if isinstance(exception, requests.exceptions.RequestException):
            response = getattr(exception, 'response', None)
            if response is not None:
                return response.status_code in self.retry_http_codes
                
        return True
        
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay before next retry attempt.
        
        Args:
            attempt: Attempt number (1-based)
            
        Returns:
            Delay in seconds
        """
        if self.strategy == RetryStrategy.IMMEDIATE:
            delay = 0.0
            
        elif self.strategy == RetryStrategy.LINEAR:
            delay = self.initial_delay * attempt
            
        elif self.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.initial_delay * (self.backoff_base ** (attempt - 1))
            
        elif self.strategy == RetryStrategy.FIBONACCI:
            delay = self._fibonacci_delay(attempt)
            
        else:
            delay = self.initial_delay
            
        # Apply multiplier
        delay *= self.backoff_multiplier
        
        # Apply max delay cap
        delay = min(delay, self.max_delay)
        
        # Apply jitter
        if self.jitter and delay > 0:
            jitter_range = delay * self.jitter_factor
            delay += random.uniform(-jitter_range, jitter_range)
            
        return max(0, delay)  # Ensure non-negative
        
    def _fibonacci_delay(self, n: int) -> float:
        """Calculate Fibonacci sequence delay."""
        if n <= 1:
            return self.initial_delay
        a, b = self.initial_delay, self.initial_delay
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b


@dataclass
class RetryStatistics:
    """Statistics for retry operations."""
    
    total_attempts: int = 0
    successful_attempts: int = 0
    failed_attempts: int = 0
    total_delay_time: float = 0.0
    errors_encountered: Dict[str, int] = field(default_factory=dict)
    
    def record_attempt(self, success: bool, delay: float = 0.0, error: Optional[Exception] = None) -> None:
        """Record an attempt.
        
        Args:
            success: Whether the attempt succeeded
            delay: Delay before this attempt
            error: Exception if attempt failed
        """
        self.total_attempts += 1
        self.total_delay_time += delay
        
        if success:
            self.successful_attempts += 1
        else:
            self.failed_attempts += 1
            if error:
                error_name = type(error).__name__
                self.errors_encountered[error_name] = self.errors_encountered.get(error_name, 0) + 1
                
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_attempts == 0:
            return 0.0
        return (self.successful_attempts / self.total_attempts) * 100
        
    def average_attempts_to_success(self) -> float:
        """Calculate average attempts needed for success."""
        if self.successful_attempts == 0:
            return float('inf')
        return self.total_attempts / self.successful_attempts


class RetryManager:
    """Manages retry operations with statistics tracking."""
    
    def __init__(self, config: Optional[RetryConfig] = None):
        """Initialize retry manager.
        
        Args:
            config: Retry configuration
        """
        self.config = config or RetryConfig()
        self.statistics = RetryStatistics()
        
    def execute(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        """Execute function with retry logic.
        
        Args:
            func: Function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function
            
        Returns:
            Function result
            
        Raises:
            Last exception if all retries exhausted
        """
        last_exception = None
        
        for attempt in range(1, self.config.max_attempts + 1):
            delay = 0.0
            
            # Calculate and apply delay (except for first attempt)
            if attempt > 1:
                delay = self.config.calculate_delay(attempt - 1)
                if delay > 0:
                    if self.config.log_retries:
                        logger.info(
                            f"Retry {attempt}/{self.config.max_attempts}: "
                            f"Waiting {delay:.2f}s before next attempt"
                        )
                    time.sleep(delay)
                    
            try:
                # Execute function
                result = func(*args, **kwargs)
                
                # Record success
                self.statistics.record_attempt(success=True, delay=delay)
                
                if self.config.log_retries and attempt > 1:
                    logger.info(f"Retry {attempt} succeeded")
                    
                return result
                
            except Exception as e:
                last_exception = e
                
                # Check if we should retry this exception
                if not self.config.should_retry(e):
                    self.statistics.record_attempt(success=False, delay=delay, error=e)
                    raise
                    
                # Check if we have attempts remaining
                if attempt >= self.config.max_attempts:
                    self.statistics.record_attempt(success=False, delay=delay, error=e)
                    if self.config.log_retries:
                        logger.error(
                            f"All {self.config.max_attempts} retry attempts exhausted. "
                            f"Last error: {type(e).__name__}: {str(e)}"
                        )
                    raise
                    
                # Record failed attempt
                self.statistics.record_attempt(success=False, delay=delay, error=e)
                
                # Log retry
                if self.config.log_retries:
                    logger.warning(
                        f"Attempt {attempt}/{self.config.max_attempts} failed: "
                        f"{type(e).__name__}: {str(e)}"
                    )
                    
                # Call retry callback if configured
                if self.config.on_retry_callback:
                    self.config.on_retry_callback(e, attempt)
                    
        # Should never reach here, but just in case
        if last_exception:
            raise last_exception


def retry(config: Optional[Union[RetryConfig, Dict[str, Any]]] = None, **kwargs) -> Callable:
    """Decorator for adding retry logic to functions.
    
    Args:
        config: RetryConfig instance or dict of config parameters
        **kwargs: Individual config parameters (overrides config)
        
    Returns:
        Decorated function
        
    Example:
        @retry(max_attempts=5, strategy=RetryStrategy.EXPONENTIAL)
        def upload_file(file_path):
            # Upload logic here
            pass
            
        @retry(RetryConfig(max_attempts=3, initial_delay=2.0))
        def api_call():
            # API call here
            pass
    """
    # Build configuration
    if config is None:
        retry_config = RetryConfig(**kwargs)
    elif isinstance(config, dict):
        retry_config = RetryConfig(**{**config, **kwargs})
    elif isinstance(config, RetryConfig):
        # Override specific fields if provided in kwargs
        if kwargs:
            config_dict = config.__dict__.copy()
            config_dict.update(kwargs)
            retry_config = RetryConfig(**config_dict)
        else:
            retry_config = config
    else:
        raise ValueError(f"Invalid config type: {type(config)}")
        
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            manager = RetryManager(retry_config)
            return manager.execute(func, *args, **kwargs)
            
        # Attach config and manager for inspection
        wrapper.retry_config = retry_config
        wrapper.retry_manager = None  # Will be set on first use
        
        return wrapper
        
    return decorator


class RetryableUpload:
    """Context manager for retryable upload operations."""
    
    def __init__(
        self,
        file_path: str,
        max_attempts: int = 3,
        on_progress: Optional[Callable[[int, int], None]] = None
    ):
        """Initialize retryable upload.
        
        Args:
            file_path: Path to file being uploaded
            max_attempts: Maximum retry attempts
            on_progress: Progress callback (bytes_sent, total_bytes)
        """
        self.file_path = file_path
        self.max_attempts = max_attempts
        self.on_progress = on_progress
        self.attempt = 0
        self.start_byte = 0
        
    def __enter__(self):
        """Enter context manager."""
        self.attempt += 1
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        if exc_type is not None:
            # Record where we failed for potential resume
            if hasattr(exc_val, 'bytes_sent'):
                self.start_byte = exc_val.bytes_sent
                
            # Determine if we should retry
            if self.attempt < self.max_attempts:
                if isinstance(exc_val, (UploadError, UploadTimeoutError, requests.exceptions.RequestException)):
                    logger.info(f"Upload attempt {self.attempt} failed, will retry from byte {self.start_byte}")
                    return False  # Don't propagate exception
                    
        return False  # Propagate exception
        
    def should_retry(self) -> bool:
        """Check if more retries are available."""
        return self.attempt < self.max_attempts


# Predefined retry configurations for common scenarios

RETRY_CONFIG_DEFAULT = RetryConfig()

RETRY_CONFIG_AGGRESSIVE = RetryConfig(
    max_attempts=10,
    strategy=RetryStrategy.EXPONENTIAL,
    initial_delay=0.5,
    max_delay=60.0,
    backoff_base=1.5
)

RETRY_CONFIG_CONSERVATIVE = RetryConfig(
    max_attempts=3,
    strategy=RetryStrategy.LINEAR,
    initial_delay=5.0,
    max_delay=30.0,
    jitter=False
)

RETRY_CONFIG_API_CALLS = RetryConfig(
    max_attempts=5,
    strategy=RetryStrategy.EXPONENTIAL,
    initial_delay=1.0,
    backoff_base=2.0,
    retry_on=(requests.exceptions.RequestException, ConnectionError, TimeoutError),
    retry_http_codes=[408, 429, 500, 502, 503, 504]
)

RETRY_CONFIG_FILE_OPERATIONS = RetryConfig(
    max_attempts=3,
    strategy=RetryStrategy.LINEAR,
    initial_delay=0.5,
    retry_on=(IOError, OSError, FileNotFoundError),
    dont_retry_on=(PermissionError,)
)


def with_retry_stats(func: Callable) -> Callable:
    """Decorator that adds retry statistics to a function.
    
    The decorated function will have a 'retry_stats' attribute containing
    RetryStatistics after execution.
    
    Args:
        func: Function to decorate (must already have @retry decorator)
        
    Returns:
        Decorated function
    """
    if not hasattr(func, 'retry_config'):
        raise ValueError("Function must have @retry decorator applied first")
        
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Create manager if not exists
        if func.retry_manager is None:
            func.retry_manager = RetryManager(func.retry_config)
            
        # Execute with manager
        result = func.retry_manager.execute(func.__wrapped__, *args, **kwargs)
        
        # Attach statistics
        wrapper.retry_stats = func.retry_manager.statistics
        
        return result
        
    return wrapper


class SmartRetry:
    """Smart retry logic that adapts based on error patterns."""
    
    def __init__(self, initial_config: Optional[RetryConfig] = None):
        """Initialize smart retry system.
        
        Args:
            initial_config: Initial retry configuration
        """
        self.config = initial_config or RetryConfig()
        self.error_history: List[Tuple[datetime, Exception]] = []
        self.success_history: List[datetime] = []
        
    def adapt_config(self) -> None:
        """Adapt retry configuration based on error patterns."""
        if len(self.error_history) < 3:
            return
            
        # Get recent errors (last 10 minutes)
        recent_errors = [
            (ts, err) for ts, err in self.error_history
            if (datetime.now() - ts).total_seconds() < 600
        ]
        
        # If seeing many timeout errors, increase delays
        timeout_errors = sum(1 for _, err in recent_errors if isinstance(err, TimeoutError))
        if timeout_errors > len(recent_errors) * 0.5:
            self.config.initial_delay *= 1.5
            self.config.max_delay *= 2
            logger.info("Adapting retry config: Increasing delays due to timeout errors")
            
        # If seeing rate limit errors, switch to exponential backoff
        rate_limit_errors = sum(
            1 for _, err in recent_errors 
            if isinstance(err, requests.exceptions.RequestException) and 
            getattr(err.response, 'status_code', None) == 429
        )
        if rate_limit_errors > 0:
            self.config.strategy = RetryStrategy.EXPONENTIAL
            self.config.backoff_base = 2.5
            logger.info("Adapting retry config: Using exponential backoff due to rate limits")
            
    def record_error(self, error: Exception) -> None:
        """Record an error occurrence."""
        self.error_history.append((datetime.now(), error))
        # Keep only recent history
        self.error_history = self.error_history[-100:]
        self.adapt_config()
        
    def record_success(self) -> None:
        """Record a successful operation."""
        self.success_history.append(datetime.now())
        self.success_history = self.success_history[-100:]