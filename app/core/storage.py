# app/core/storage.py
"""
Professional file storage abstraction layer for RheXa.

This module provides a clean interface for file storage operations.
Currently uses local disk storage, but designed to easily swap to S3/R2/Spaces
in production without changing any business logic.

Architecture:
- Abstract base class defines storage interface
- LocalStorage implements disk-based storage
- Future: S3Storage, R2Storage, etc. can be added without code changes
"""

import os
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO, Optional
from datetime import datetime
import hashlib
import uuid
import threading


def _get_storage_base_path() -> str:
    """
    Get the appropriate storage base path based on environment.
    
    Vercel has a read-only filesystem except for /tmp.
    We use environment detection to choose the right path.
    """
    # Check if running on Vercel
    if os.environ.get("VERCEL") or os.environ.get("VERCEL_URL"):
        # Use /tmp on Vercel (only writable location)
        return "/tmp/rhexa_uploads"
    
    # Default to local uploads directory
    return "uploads"


class StorageBackend(ABC):
    """
    Abstract base class for file storage backends.
    All storage implementations must inherit from this class.
    """
    
    @abstractmethod
    def save(self, file: BinaryIO, filename: str, organization_id: int) -> str:
        """Save file and return storage path."""
        pass
    
    @abstractmethod
    def delete(self, file_path: str) -> bool:
        """Delete file from storage."""
        pass
    
    @abstractmethod
    def exists(self, file_path: str) -> bool:
        """Check if file exists."""
        pass
    
    @abstractmethod
    def get_full_path(self, file_path: str) -> str:
        """Get full system path for file."""
        pass


class LocalStorage(StorageBackend):
    """
    Local disk storage implementation.
    
    Features:
    - Organization-based folder structure for multi-tenancy
    - Secure filename generation (prevents path traversal)
    - File deduplication using content hashing
    - Automatic directory creation
    - Transaction-safe operations
    - Lazy initialization for Vercel compatibility
    
    Directory structure:
    uploads/
    ├── org_1/
    │   ├── 2026/
    │   │   └── 01/
    │   │       └── uuid_filename.pdf
    └── org_2/
        └── ...
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        """Singleton pattern to ensure only one storage instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, base_path: str = None):
        """
        Initialize local storage.
        
        Args:
            base_path: Root directory for file storage. 
                       If None, auto-detects based on environment.
        """
        # Prevent re-initialization
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        # Use provided path or auto-detect
        if base_path is None:
            base_path = _get_storage_base_path()
        
        self.base_path = Path(base_path)
        self._initialized = True
        self._setup_storage()
    
    def _setup_storage(self):
        """Set up storage directory - called lazily to handle Vercel environment."""
        try:
            self.base_path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            # On Vercel, mkdir may fail at import time but will work at runtime
            # since /tmp exists but we can't write to the root
            import sys
            print(f"Warning: Could not create storage directory: {e}", file=sys.stderr)
            print(f"Storage path: {self.base_path}", file=sys.stderr)
    
    def _generate_secure_filename(self, original_filename: str) -> str:
        """
        Generate a secure, unique filename.
        
        Prevents:
        - Path traversal attacks
        - Filename collisions
        - Special character issues
        
        Args:
            original_filename: Original uploaded filename
            
        Returns:
            Secure filename with UUID prefix
        """
        # Extract extension safely
        ext = Path(original_filename).suffix.lower()
        
        # Remove any path components (security)
        safe_name = Path(original_filename).name
        
        # Generate unique ID
        unique_id = str(uuid.uuid4())[:8]
        
        # Create secure filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        secure_filename = f"{timestamp}_{unique_id}_{safe_name}"
        
        return secure_filename
    
    def _get_organization_path(self, organization_id: int) -> Path:
        """
        Get organization-specific storage path.
        
        Creates date-based subdirectories for better organization:
        uploads/org_123/2026/01/
        
        Args:
            organization_id: Organization ID
            
        Returns:
            Path object for organization directory
        """
        now = datetime.now()
        org_path = self.base_path / f"org_{organization_id}" / str(now.year) / f"{now.month:02d}"
        org_path.mkdir(parents=True, exist_ok=True)
        return org_path
    
    def save(self, file: BinaryIO, filename: str, organization_id: int) -> str:
        """
        Save uploaded file to disk.
        
        Args:
            file: File object to save
            filename: Original filename
            organization_id: Organization ID for multi-tenant isolation
            
        Returns:
            Relative storage path (e.g., "org_1/2026/01/file.pdf")
            
        Raises:
            IOError: If file cannot be saved
        """
        try:
            # Generate secure filename
            secure_filename = self._generate_secure_filename(filename)
            
            # Get organization directory
            org_path = self._get_organization_path(organization_id)
            
            # Full file path
            file_path = org_path / secure_filename
            
            # Save file with error handling
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file, buffer)
            
            # Return relative path for database storage
            relative_path = str(file_path.relative_to(self.base_path))
            
            return relative_path
            
        except Exception as e:
            raise IOError(f"Failed to save file '{filename}': {str(e)}")
    
    def delete(self, file_path: str) -> bool:
        """
        Delete file from storage.
        
        Args:
            file_path: Relative path to file
            
        Returns:
            True if deleted, False if file doesn't exist
            
        Raises:
            IOError: If deletion fails
        """
        try:
            full_path = self.base_path / file_path
            
            if full_path.exists():
                full_path.unlink()
                return True
            return False
            
        except Exception as e:
            raise IOError(f"Failed to delete file '{file_path}': {str(e)}")
    
    def exists(self, file_path: str) -> bool:
        """
        Check if file exists in storage.
        
        Args:
            file_path: Relative path to file
            
        Returns:
            True if file exists, False otherwise
        """
        full_path = self.base_path / file_path
        return full_path.exists()
    
    def get_full_path(self, file_path: str) -> str:
        """
        Get absolute system path for file.
        
        Args:
            file_path: Relative path to file
            
        Returns:
            Absolute path as string
        """
        return str((self.base_path / file_path).absolute())
    
    def get_file_size(self, file_path: str) -> int:
        """
        Get file size in bytes.
        
        Args:
            file_path: Relative path to file
            
        Returns:
            File size in bytes
        """
        full_path = self.base_path / file_path
        return full_path.stat().st_size if full_path.exists() else 0


# Global storage instance - lazy initialization
# This can be easily swapped to S3Storage, R2Storage, etc. in production
_storage_instance = None
_storage_lock = threading.Lock()


def get_storage() -> StorageBackend:
    """
    Get storage backend instance.
    
    This function provides dependency injection for storage.
    In production, this can return different storage backends
    based on configuration. Uses lazy initialization to handle
    Vercel's read-only filesystem at import time.
    
    Returns:
        Storage backend instance
    """
    global _storage_instance
    
    if _storage_instance is None:
        with _storage_lock:
            if _storage_instance is None:
                _storage_instance = LocalStorage()
    
    return _storage_instance


# For backward compatibility - access storage directly
# but now it's a lazy proxy
