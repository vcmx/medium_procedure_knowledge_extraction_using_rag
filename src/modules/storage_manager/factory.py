from typing import Type

from .base import BaseStorageManager
from .chroma_manager import ChromaStorageManager
from .falkor_manager import FalkorStorageManager


class StorageManagerFactory:
    """Factory for creating storage manager instances."""

    _implementations = {"chroma": ChromaStorageManager, "falkor": FalkorStorageManager}

    @classmethod
    def create(cls, implementation: str = "chroma", **kwargs) -> BaseStorageManager:
        """
        Create a storage manager instance.

        Args:
            implementation: Name of the implementation to use ("chroma" or "falkor")
            **kwargs: Additional arguments to pass to the storage manager constructor

        Returns:
            An instance of the requested storage manager

        Raises:
            ValueError: If the requested implementation is not supported
        """
        if implementation not in cls._implementations:
            raise ValueError(
                f"Unsupported implementation: {implementation}. "
                f"Supported implementations: {list(cls._implementations.keys())}"
            )

        return cls._implementations[implementation](**kwargs)

    @classmethod
    def register_implementation(
        cls, name: str, implementation: Type[BaseStorageManager]
    ) -> None:
        """
        Register a new storage manager implementation.

        Args:
            name: Name to register the implementation under
            implementation: Storage manager class to register
        """
        if not issubclass(implementation, BaseStorageManager):
            raise ValueError("Implementation must be a subclass of BaseStorageManager")

        cls._implementations[name] = implementation


def create_storage_manager(config: dict) -> BaseStorageManager:
    """
    Create a storage manager from configuration.
    
    Args:
        config: Configuration dictionary with at least a 'type' field
        
    Returns:
        An instance of the requested storage manager
    """
    implementation = config.get("type", "chroma")
    # Remove 'type' from config before passing to create
    config_copy = config.copy()
    config_copy.pop("type", None)
    return StorageManagerFactory.create(implementation, **config_copy)
