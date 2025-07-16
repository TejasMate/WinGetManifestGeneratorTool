"""
File utilities for the WinGet Manifest Generator Tool.

This module provides common file operations and utilities.
"""

import os
import shutil
from pathlib import Path
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


def ensure_directory_exists(directory: Path) -> Path:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        directory: Path to the directory
        
    Returns:
        The directory path
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def safe_file_copy(src: Path, dst: Path, backup: bool = True) -> bool:
    """
    Safely copy a file with optional backup.
    
    Args:
        src: Source file path
        dst: Destination file path
        backup: Whether to create backup of existing destination
        
    Returns:
        True if successful, False otherwise
    """
    try:
        src, dst = Path(src), Path(dst)
        
        # Create destination directory if needed
        ensure_directory_exists(dst.parent)
        
        # Create backup if destination exists and backup is requested
        if dst.exists() and backup:
            backup_path = dst.with_suffix(f"{dst.suffix}.backup")
            shutil.copy2(dst, backup_path)
            logger.debug(f"Created backup: {backup_path}")
        
        # Copy file
        shutil.copy2(src, dst)
        logger.debug(f"Copied {src} to {dst}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to copy {src} to {dst}: {e}")
        return False


def safe_file_move(src: Path, dst: Path, backup: bool = True) -> bool:
    """
    Safely move a file with optional backup.
    
    Args:
        src: Source file path
        dst: Destination file path
        backup: Whether to create backup of existing destination
        
    Returns:
        True if successful, False otherwise
    """
    try:
        src, dst = Path(src), Path(dst)
        
        # Create destination directory if needed
        ensure_directory_exists(dst.parent)
        
        # Create backup if destination exists and backup is requested
        if dst.exists() and backup:
            backup_path = dst.with_suffix(f"{dst.suffix}.backup")
            shutil.move(dst, backup_path)
            logger.debug(f"Created backup: {backup_path}")
        
        # Move file
        shutil.move(src, dst)
        logger.debug(f"Moved {src} to {dst}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to move {src} to {dst}: {e}")
        return False


def find_files_by_pattern(directory: Path, pattern: str, recursive: bool = True) -> List[Path]:
    """
    Find files matching a pattern in a directory.
    
    Args:
        directory: Directory to search in
        pattern: Glob pattern to match
        recursive: Whether to search recursively
        
    Returns:
        List of matching file paths
    """
    directory = Path(directory)
    
    if not directory.exists():
        return []
    
    if recursive:
        return list(directory.rglob(pattern))
    else:
        return list(directory.glob(pattern))


def get_file_size_mb(file_path: Path) -> float:
    """
    Get file size in megabytes.
    
    Args:
        file_path: Path to the file
        
    Returns:
        File size in MB
    """
    try:
        size_bytes = Path(file_path).stat().st_size
        return size_bytes / (1024 * 1024)
    except Exception:
        return 0.0


def cleanup_temp_files(directory: Path, pattern: str = "*.tmp") -> int:
    """
    Clean up temporary files in a directory.
    
    Args:
        directory: Directory to clean
        pattern: Pattern for temp files
        
    Returns:
        Number of files cleaned up
    """
    cleaned = 0
    
    try:
        temp_files = find_files_by_pattern(directory, pattern, recursive=True)
        
        for file_path in temp_files:
            try:
                file_path.unlink()
                cleaned += 1
                logger.debug(f"Cleaned up temp file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up {file_path}: {e}")
        
        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} temporary files")
            
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
    
    return cleaned


def get_available_disk_space_mb(path: Path) -> float:
    """
    Get available disk space in megabytes.
    
    Args:
        path: Path to check (file or directory)
        
    Returns:
        Available space in MB
    """
    try:
        stat = shutil.disk_usage(path)
        return stat.free / (1024 * 1024)
    except Exception:
        return 0.0


def validate_csv_file(file_path: Path) -> tuple[bool, Optional[str]]:
    """
    Validate that a file is a readable CSV.
    
    Args:
        file_path: Path to the CSV file
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        file_path = Path(file_path)
        
        if not file_path.exists():
            return False, f"File does not exist: {file_path}"
        
        if not file_path.is_file():
            return False, f"Path is not a file: {file_path}"
        
        if file_path.suffix.lower() not in ['.csv', '.tsv']:
            return False, f"File is not a CSV/TSV: {file_path}"
        
        # Try to read first few lines
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = [f.readline() for _ in range(3)]
        
        if not lines[0].strip():
            return False, "File appears to be empty"
        
        # Check for common CSV indicators
        first_line = lines[0]
        if ',' not in first_line and '\t' not in first_line and ';' not in first_line:
            return False, "File does not appear to contain CSV data"
        
        return True, None
        
    except Exception as e:
        return False, f"Error validating file: {e}"


def create_directory_structure(base_path: Path, structure: dict) -> bool:
    """
    Create a directory structure from a nested dictionary.
    
    Args:
        base_path: Base directory path
        structure: Nested dict representing directory structure
        
    Returns:
        True if successful, False otherwise
    """
    try:
        base_path = Path(base_path)
        
        def create_recursive(current_path: Path, struct: dict):
            for name, content in struct.items():
                new_path = current_path / name
                
                if isinstance(content, dict):
                    # It's a directory
                    ensure_directory_exists(new_path)
                    create_recursive(new_path, content)
                else:
                    # It's a file (content is the file content)
                    ensure_directory_exists(new_path.parent)
                    if content is not None:
                        with open(new_path, 'w') as f:
                            f.write(str(content))
                    else:
                        new_path.touch()
        
        create_recursive(base_path, structure)
        return True
        
    except Exception as e:
        logger.error(f"Failed to create directory structure: {e}")
        return False
