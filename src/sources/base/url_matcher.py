"""
Base URL matcher implementation for package sources.

This module provides common URL matching and pattern extraction functionality
that can be used across different package sources.
"""

import re
from typing import List, Set
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


class BaseURLMatcher:
    """Base URL matcher with common functionality."""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def extract_extensions(self, urls: List[str]) -> Set[str]:
        """Extract file extensions from a list of URLs."""
        extensions = set()
        
        for url in urls:
            if not url or not isinstance(url, str):
                continue
                
            url = url.strip()
            
            # Handle URLs ending with /download (extract from previous path segment)
            if url.endswith('/download'):
                # Look for extension in the path before /download
                path_match = re.search(r'/([^/]+)\.([^./]+)/download$', url)
                if path_match:
                    ext = path_match.group(2)
                    if ext and not ext.isdigit():
                        extensions.add(ext.lower())
                continue
            
            # Standard extension extraction
            ext_match = re.search(r'\.([^./?#]+)(?:[?#]|$)', url)
            if ext_match:
                ext = ext_match.group(1)
                if ext and not ext.isdigit() and len(ext) <= 5:  # Reasonable extension length
                    extensions.add(ext.lower())
        
        return extensions
    
    def extract_architectures(self, urls: List[str]) -> Set[str]:
        """Extract architectures from URLs."""
        architectures = set()
        
        # Architecture patterns (order matters - more specific first)
        arch_patterns = [
            r'\b(x86_64|amd64)\b',
            r'\b(x64)\b',
            r'\b(x86|i386|i686)\b',
            r'\b(arm64|aarch64)\b',
            r'\b(arm)\b',
        ]
        
        arch_mapping = {
            'x86_64': 'x64',
            'amd64': 'x64',
            'i386': 'x86',
            'i686': 'x86',
            'aarch64': 'arm64',
        }
        
        for url in urls:
            if not url or not isinstance(url, str):
                continue
                
            url_lower = url.lower()
            
            for pattern in arch_patterns:
                matches = re.findall(pattern, url_lower, re.IGNORECASE)
                for match in matches:
                    # Normalize architecture names
                    arch = arch_mapping.get(match.lower(), match.lower())
                    architectures.add(arch)
        
        return architectures
    
    def extract_keywords(self, urls: List[str]) -> Set[str]:
        """Extract installer-related keywords from URLs."""
        keywords = set()
        
        keyword_patterns = [
            r'\b(setup|installer|install)\b',
            r'\b(portable|standalone)\b',
            r'\b(windows|win32|win64)\b',
            r'\b(msi|exe|zip|7z|rar)\b',
        ]
        
        for url in urls:
            if not url or not isinstance(url, str):
                continue
                
            url_lower = url.lower()
            
            for pattern in keyword_patterns:
                matches = re.findall(pattern, url_lower, re.IGNORECASE)
                for match in matches:
                    keywords.add(match.lower())
        
        return keywords
    
    def extract_url_patterns(self, urls: List[str]) -> Set[str]:
        """Extract comprehensive URL patterns combining architecture, extensions, and keywords."""
        if not urls:
            return set()
        
        architectures = self.extract_architectures(urls)
        extensions = self.extract_extensions(urls)
        keywords = self.extract_keywords(urls)
        
        patterns = set()
        
        # Create patterns by combining different elements
        for arch in architectures:
            for ext in extensions:
                patterns.add(f"{arch}-{ext}")
                
                # Add keywords to create more specific patterns
                for keyword in keywords:
                    if keyword in ['setup', 'installer', 'portable', 'windows']:
                        patterns.add(f"{keyword}-{arch}-{ext}")
        
        # Add standalone patterns if no combinations found
        if not patterns:
            patterns.update(extensions)
            patterns.update(architectures)
            patterns.update(keywords)
        
        return patterns
    
    def filter_urls_by_patterns(self, urls: List[str], patterns: Set[str]) -> List[str]:
        """Filter URLs based on extracted patterns."""
        if not patterns or not urls:
            return urls
        
        filtered_urls = []
        pattern_extensions = set()
        
        # Extract extensions from patterns
        for pattern in patterns:
            parts = pattern.split('-')
            if parts:
                last_part = parts[-1]
                if last_part and not last_part.isdigit():
                    pattern_extensions.add(last_part.lower())
        
        if not pattern_extensions:
            return urls
        
        for url in urls:
            if not url or not isinstance(url, str):
                continue
                
            url = url.strip()
            
            # Check if URL matches any of the pattern extensions
            for ext in pattern_extensions:
                if url.lower().endswith(f'.{ext}') or f'.{ext}/' in url.lower():
                    filtered_urls.append(url)
                    break
        
        return filtered_urls if filtered_urls else urls
    
    def is_valid_installer_url(self, url: str) -> bool:
        """Check if URL appears to be a valid installer URL."""
        if not url or not isinstance(url, str):
            return False
        
        url_lower = url.lower()
        
        # Check for common installer extensions
        installer_extensions = ['.exe', '.msi', '.zip', '.7z', '.tar.gz', '.dmg', '.pkg', '.deb', '.rpm']
        has_installer_ext = any(url_lower.endswith(ext) for ext in installer_extensions)
        
        # Check for installer keywords
        installer_keywords = ['setup', 'installer', 'install', 'download', 'release']
        has_installer_keyword = any(keyword in url_lower for keyword in installer_keywords)
        
        return has_installer_ext or has_installer_keyword
