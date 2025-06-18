"""Plugin architecture for GDC uploader strategies.

This module implements the plugin system that allows different upload strategies
to be registered and used dynamically. It uses a strategy pattern with
automatic discovery and registration of uploaders.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, Type, Optional, Any, List
import importlib
import logging
import pkgutil

from .base_uploader import BaseUploader
from .exceptions import PluginNotFoundError, PluginLoadError


logger = logging.getLogger(__name__)


class UploaderType(Enum):
    """Types of uploaders available in the system."""
    PARALLEL_GDC_CLIENT = "parallel_gdc_client"      # GNU parallel + gdc-client
    SINGLE_FILE = "single_file"                      # Single file uploads
    API_PARALLEL = "api_parallel"                    # HTTP API-based parallel
    SPOT_RESILIENT = "spot_resilient"               # Spot instance resilient
    DIRECT = "direct"                                # Direct minimal wrapper


@dataclass
class UploaderConfig:
    """Configuration for an uploader plugin.
    
    Attributes:
        name: Human-readable name of the uploader
        uploader_type: Type identifier for the uploader
        description: Brief description of the uploader's purpose
        supported_features: List of features this uploader supports
        priority: Priority for automatic selection (higher = preferred)
        config_schema: JSON schema for additional configuration
    """
    name: str
    uploader_type: UploaderType
    description: str
    supported_features: List[str]
    priority: int = 0
    config_schema: Optional[Dict[str, Any]] = None


class UploaderPlugin(ABC):
    """Interface for uploader plugins.
    
    All uploader implementations must inherit from this class and implement
    the required methods. Plugins are automatically discovered and registered.
    """
    
    @abstractmethod
    def get_config(self) -> UploaderConfig:
        """Get the plugin configuration.
        
        Returns:
            UploaderConfig object describing this plugin
        """
        pass
    
    @abstractmethod
    def create_uploader(self, **kwargs) -> BaseUploader:
        """Create an instance of the uploader.
        
        Args:
            **kwargs: Configuration parameters for the uploader
            
        Returns:
            Instance of BaseUploader implementation
        """
        pass
    
    @abstractmethod
    def validate_environment(self) -> bool:
        """Validate that the environment supports this uploader.
        
        This method should check for required dependencies, tools,
        and system capabilities.
        
        Returns:
            True if the environment is suitable, False otherwise
        """
        pass
    
    @abstractmethod
    def get_required_dependencies(self) -> List[str]:
        """Get list of required external dependencies.
        
        Returns:
            List of dependency names (e.g., ['gdc-client', 'parallel'])
        """
        pass


class UploaderRegistry:
    """Registry for managing uploader plugins.
    
    This class handles plugin discovery, registration, and instantiation.
    It implements a singleton pattern to ensure consistent plugin management.
    """
    
    _instance: Optional['UploaderRegistry'] = None
    
    def __new__(cls) -> 'UploaderRegistry':
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._plugins: Dict[UploaderType, Type[UploaderPlugin]] = {}
        return cls._instance
    
    def register(self, plugin_class: Type[UploaderPlugin]) -> None:
        """Register an uploader plugin.
        
        Args:
            plugin_class: Class implementing UploaderPlugin interface
            
        Raises:
            ValueError: If plugin type is already registered
        """
        config = plugin_class().get_config()
        if config.uploader_type in self._plugins:
            raise ValueError(
                f"Plugin type {config.uploader_type} is already registered"
            )
        self._plugins[config.uploader_type] = plugin_class
        logger.info(f"Registered plugin: {config.name} ({config.uploader_type.value})")
    
    def unregister(self, uploader_type: UploaderType) -> None:
        """Unregister an uploader plugin.
        
        Args:
            uploader_type: Type of uploader to unregister
        """
        if uploader_type in self._plugins:
            self._plugins.pop(uploader_type)
            logger.info(f"Unregistered plugin: {uploader_type.value}")
    
    def get_plugin(self, uploader_type: UploaderType) -> Optional[Type[UploaderPlugin]]:
        """Get a registered plugin by type.
        
        Args:
            uploader_type: Type of uploader to retrieve
            
        Returns:
            Plugin class or None if not found
        """
        return self._plugins.get(uploader_type)
    
    def list_plugins(self) -> List[UploaderConfig]:
        """List all registered plugins.
        
        Returns:
            List of plugin configurations
        """
        configs = []
        for plugin_class in self._plugins.values():
            plugin = plugin_class()
            configs.append(plugin.get_config())
        return configs
    
    def create_uploader(
        self,
        uploader_type: UploaderType,
        **kwargs
    ) -> BaseUploader:
        """Create an uploader instance.
        
        Args:
            uploader_type: Type of uploader to create
            **kwargs: Configuration parameters
            
        Returns:
            Instance of the requested uploader
            
        Raises:
            PluginNotFoundError: If plugin type is not registered
            PluginLoadError: If plugin fails to create uploader
        """
        plugin_class = self._plugins.get(uploader_type)
        if not plugin_class:
            raise PluginNotFoundError(uploader_type.value)
        
        try:
            plugin = plugin_class()
            if not plugin.validate_environment():
                missing_deps = plugin.get_required_dependencies()
                raise PluginLoadError(
                    uploader_type.value,
                    f"Environment validation failed. Missing dependencies: {', '.join(missing_deps)}"
                )
            return plugin.create_uploader(**kwargs)
        except Exception as e:
            raise PluginLoadError(uploader_type.value, str(e))
    
    def auto_discover(self, package_name: str = "gdc_uploader.uploaders") -> None:
        """Automatically discover and register plugins from a package.
        
        Args:
            package_name: Package to search for plugins
        """
        try:
            package = importlib.import_module(package_name)
            
            # Iterate through all modules in the package
            for importer, modname, ispkg in pkgutil.iter_modules(
                package.__path__, package.__name__ + "."
            ):
                if not ispkg:
                    try:
                        module = importlib.import_module(modname)
                        
                        # Look for UploaderPlugin subclasses
                        for name in dir(module):
                            obj = getattr(module, name)
                            if (isinstance(obj, type) and 
                                issubclass(obj, UploaderPlugin) and 
                                obj is not UploaderPlugin):
                                # Register the plugin
                                self.register(obj)
                                
                    except Exception as e:
                        logger.warning(f"Failed to load module {modname}: {e}")
                        
        except ImportError as e:
            logger.warning(f"Failed to import package {package_name}: {e}")
    
    def get_best_uploader(
        self,
        required_features: Optional[List[str]] = None
    ) -> Optional[UploaderType]:
        """Get the best uploader based on features and environment.
        
        Args:
            required_features: List of required features
            
        Returns:
            Best uploader type or None if no suitable uploader found
        """
        required_features = required_features or []
        candidates = []
        
        for plugin_class in self._plugins.values():
            plugin = plugin_class()
            config = plugin.get_config()
            
            # Check if plugin supports required features
            if all(f in config.supported_features for f in required_features):
                # Check if environment is suitable
                if plugin.validate_environment():
                    candidates.append((config.priority, config.uploader_type))
                    logger.debug(
                        f"Plugin {config.name} is a candidate with priority {config.priority}"
                    )
        
        if candidates:
            # Sort by priority (descending) and return the best
            candidates.sort(key=lambda x: x[0], reverse=True)
            return candidates[0][1]
        
        return None


# Plugin decorator for automatic registration

def register_uploader(uploader_type: UploaderType):
    """Decorator to automatically register uploader plugins.
    
    Usage:
        @register_uploader(UploaderType.PARALLEL_GDC_CLIENT)
        class ParallelGDCClientPlugin(UploaderPlugin):
            ...
    """
    def decorator(cls: Type[UploaderPlugin]) -> Type[UploaderPlugin]:
        registry = UploaderRegistry()
        
        # Create a wrapper that ensures the config returns the correct type
        original_get_config = cls.get_config
        
        def get_config_wrapper(self) -> UploaderConfig:
            config = original_get_config(self)
            config.uploader_type = uploader_type
            return config
        
        cls.get_config = get_config_wrapper
        registry.register(cls)
        return cls
    
    return decorator


# Feature constants for standardization

class Features:
    """Standard feature identifiers for uploaders."""
    
    PARALLEL_UPLOAD = "parallel_upload"
    RETRY_LOGIC = "retry_logic"
    PROGRESS_TRACKING = "progress_tracking"
    RESUME_CAPABILITY = "resume_capability"
    SPOT_INSTANCE_RESILIENT = "spot_instance_resilient"
    API_UPLOAD = "api_upload"
    GDC_CLIENT_UPLOAD = "gdc_client_upload"
    BATCH_UPLOAD = "batch_upload"
    SINGLE_FILE_UPLOAD = "single_file_upload"
    REAL_TIME_PROGRESS = "real_time_progress"
    CHECKSUM_VALIDATION = "checksum_validation"
    BANDWIDTH_THROTTLING = "bandwidth_throttling"


# Configuration schema helpers

class ConfigSchema:
    """Helper class for creating configuration schemas."""
    
    @staticmethod
    def create_schema(**properties) -> Dict[str, Any]:
        """Create a JSON schema for configuration validation.
        
        Args:
            **properties: Property definitions
            
        Returns:
            JSON schema dictionary
        """
        return {
            "type": "object",
            "properties": properties,
            "additionalProperties": False
        }
    
    @staticmethod
    def string_property(
        description: str,
        default: Optional[str] = None,
        pattern: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a string property definition."""
        prop = {"type": "string", "description": description}
        if default is not None:
            prop["default"] = default
        if pattern is not None:
            prop["pattern"] = pattern
        return prop
    
    @staticmethod
    def integer_property(
        description: str,
        default: Optional[int] = None,
        minimum: Optional[int] = None,
        maximum: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create an integer property definition."""
        prop = {"type": "integer", "description": description}
        if default is not None:
            prop["default"] = default
        if minimum is not None:
            prop["minimum"] = minimum
        if maximum is not None:
            prop["maximum"] = maximum
        return prop
    
    @staticmethod
    def boolean_property(
        description: str,
        default: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Create a boolean property definition."""
        prop = {"type": "boolean", "description": description}
        if default is not None:
            prop["default"] = default
        return prop