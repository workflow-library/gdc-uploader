"""Authentication management for GDC API.

This module handles token management, validation, and secure storage
for GDC authentication tokens.
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Union
from datetime import datetime, timedelta
from abc import ABC, abstractmethod

from .exceptions import GDCAuthenticationError
from .models import TokenValidationResponse

logger = logging.getLogger(__name__)


class TokenProvider(ABC):
    """Abstract base class for token providers."""
    
    @abstractmethod
    def get_token(self) -> str:
        """Get the authentication token."""
        pass
    
    @abstractmethod
    def refresh_token(self) -> Optional[str]:
        """Refresh the token if possible."""
        pass
    
    @abstractmethod
    def is_valid(self) -> bool:
        """Check if the current token is valid."""
        pass


class FileTokenProvider(TokenProvider):
    """Token provider that reads from a file."""
    
    def __init__(self, token_file: Union[str, Path]):
        """Initialize with token file path.
        
        Args:
            token_file: Path to file containing the token
        """
        self.token_file = Path(token_file)
        self._token: Optional[str] = None
        self._last_read: Optional[datetime] = None
        self._cache_duration = timedelta(minutes=5)
        
        if not self.token_file.exists():
            raise GDCAuthenticationError(f"Token file not found: {self.token_file}")
        
        if not os.access(self.token_file, os.R_OK):
            raise GDCAuthenticationError(f"Token file not readable: {self.token_file}")
        
        # Check file permissions for security
        stat_info = self.token_file.stat()
        if stat_info.st_mode & 0o077:
            logger.warning(
                f"Token file {self.token_file} has overly permissive permissions. "
                "Consider setting to 600 (owner read/write only)"
            )
    
    def get_token(self) -> str:
        """Get token from file with caching."""
        now = datetime.utcnow()
        
        # Check if we need to re-read the file
        if (
            self._token is None
            or self._last_read is None
            or now - self._last_read > self._cache_duration
        ):
            self._read_token()
        
        return self._token
    
    def _read_token(self):
        """Read token from file."""
        try:
            token = self.token_file.read_text().strip()
            if not token:
                raise GDCAuthenticationError("Token file is empty")
            
            self._token = token
            self._last_read = datetime.utcnow()
            logger.debug(f"Token loaded from {self.token_file}")
            
        except IOError as e:
            raise GDCAuthenticationError(f"Failed to read token file: {e}")
    
    def refresh_token(self) -> Optional[str]:
        """Re-read token from file."""
        self._read_token()
        return self._token
    
    def is_valid(self) -> bool:
        """Check if token exists and is non-empty."""
        try:
            token = self.get_token()
            return bool(token and token.strip())
        except Exception:
            return False


class EnvironmentTokenProvider(TokenProvider):
    """Token provider that reads from environment variables."""
    
    def __init__(self, env_var: str = "GDC_TOKEN"):
        """Initialize with environment variable name.
        
        Args:
            env_var: Name of environment variable containing token
        """
        self.env_var = env_var
        self._token = os.environ.get(env_var)
        
        if not self._token:
            raise GDCAuthenticationError(
                f"Token not found in environment variable: {env_var}"
            )
    
    def get_token(self) -> str:
        """Get token from environment."""
        if not self._token:
            # Re-check environment in case it was set after initialization
            self._token = os.environ.get(self.env_var)
            if not self._token:
                raise GDCAuthenticationError(
                    f"Token not found in environment variable: {self.env_var}"
                )
        return self._token
    
    def refresh_token(self) -> Optional[str]:
        """Re-read from environment."""
        self._token = os.environ.get(self.env_var)
        return self._token
    
    def is_valid(self) -> bool:
        """Check if token exists in environment."""
        return bool(os.environ.get(self.env_var))


class StaticTokenProvider(TokenProvider):
    """Token provider with a static token value."""
    
    def __init__(self, token: str):
        """Initialize with static token.
        
        Args:
            token: The authentication token
        """
        if not token:
            raise GDCAuthenticationError("Token cannot be empty")
        self._token = token
    
    def get_token(self) -> str:
        """Get the static token."""
        return self._token
    
    def refresh_token(self) -> Optional[str]:
        """No refresh for static tokens."""
        return self._token
    
    def is_valid(self) -> bool:
        """Check if token is non-empty."""
        return bool(self._token)


class CachedTokenProvider(TokenProvider):
    """Token provider with caching and validation."""
    
    def __init__(self, base_provider: TokenProvider, validation_client: Optional[Any] = None):
        """Initialize with base provider and optional validation.
        
        Args:
            base_provider: Underlying token provider
            validation_client: Optional client for token validation
        """
        self.base_provider = base_provider
        self.validation_client = validation_client
        self._cached_token: Optional[str] = None
        self._validation_result: Optional[TokenValidationResponse] = None
        self._last_validation: Optional[datetime] = None
        self._validation_interval = timedelta(hours=1)
    
    def get_token(self) -> str:
        """Get token with validation caching."""
        if self._cached_token is None:
            self._cached_token = self.base_provider.get_token()
        
        # Validate periodically if client provided
        if self.validation_client and self._should_validate():
            self._validate_token()
        
        return self._cached_token
    
    def _should_validate(self) -> bool:
        """Check if we should validate the token."""
        if self._last_validation is None:
            return True
        
        return datetime.utcnow() - self._last_validation > self._validation_interval
    
    def _validate_token(self):
        """Validate the token using the client."""
        try:
            self._validation_result = self.validation_client.validate_token()
            self._last_validation = datetime.utcnow()
            
            if not self._validation_result.is_valid:
                # Try to refresh
                new_token = self.base_provider.refresh_token()
                if new_token:
                    self._cached_token = new_token
                    # Re-validate with new token
                    self._validation_result = self.validation_client.validate_token()
                
                if not self._validation_result.is_valid:
                    raise GDCAuthenticationError("Token validation failed")
            
            logger.debug(f"Token validated for user: {self._validation_result.username}")
            
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            raise GDCAuthenticationError(f"Token validation failed: {str(e)}")
    
    def refresh_token(self) -> Optional[str]:
        """Refresh token from base provider."""
        new_token = self.base_provider.refresh_token()
        if new_token:
            self._cached_token = new_token
            self._validation_result = None
            self._last_validation = None
        return new_token
    
    def is_valid(self) -> bool:
        """Check if token is valid."""
        if self._validation_result:
            return self._validation_result.is_valid and not self._validation_result.is_expired
        return self.base_provider.is_valid()
    
    def get_validation_result(self) -> Optional[TokenValidationResponse]:
        """Get the last validation result."""
        return self._validation_result


class TokenManager:
    """Manages authentication tokens for GDC API."""
    
    def __init__(self, provider: TokenProvider):
        """Initialize with a token provider.
        
        Args:
            provider: Token provider instance
        """
        self.provider = provider
    
    @classmethod
    def from_file(cls, token_file: Union[str, Path]) -> "TokenManager":
        """Create manager with file-based token.
        
        Args:
            token_file: Path to token file
            
        Returns:
            TokenManager instance
        """
        provider = FileTokenProvider(token_file)
        return cls(provider)
    
    @classmethod
    def from_environment(cls, env_var: str = "GDC_TOKEN") -> "TokenManager":
        """Create manager with environment-based token.
        
        Args:
            env_var: Environment variable name
            
        Returns:
            TokenManager instance
        """
        provider = EnvironmentTokenProvider(env_var)
        return cls(provider)
    
    @classmethod
    def from_token(cls, token: str) -> "TokenManager":
        """Create manager with static token.
        
        Args:
            token: Authentication token
            
        Returns:
            TokenManager instance
        """
        provider = StaticTokenProvider(token)
        return cls(provider)
    
    def get_token(self) -> str:
        """Get the current token."""
        return self.provider.get_token()
    
    def refresh(self) -> Optional[str]:
        """Refresh the token if possible."""
        return self.provider.refresh_token()
    
    def is_valid(self) -> bool:
        """Check if token is valid."""
        return self.provider.is_valid()
    
    def with_caching(self, validation_client: Optional[Any] = None) -> "TokenManager":
        """Wrap provider with caching.
        
        Args:
            validation_client: Optional client for validation
            
        Returns:
            New TokenManager with cached provider
        """
        cached_provider = CachedTokenProvider(self.provider, validation_client)
        return TokenManager(cached_provider)