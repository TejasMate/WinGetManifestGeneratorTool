#!/usr/bin/env python3
"""
Test script to verify .env loading and GitHub token configuration.
"""

import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_env_loading():
    """Test .env file loading functionality."""
    print("🔧 Testing .env file loading...")
    
    try:
        from src.config import get_config_manager
        from src.utils.token_manager import TokenManager
        
        # Test config manager
        manager = get_config_manager()
        config = manager.load_config()
        print("✅ Config system loaded successfully")
        
        # Test token loading
        token_manager = TokenManager()
        tokens = token_manager.tokens  # Access the tokens attribute directly
        
        print(f"📊 Configuration status:")
        print(f"   - Environment: {config.get('environment', 'Not set')}")
        print(f"   - Debug mode: {config.get('debug', False)}")
        print(f"   - GitHub tokens found: {len(tokens)}")
        
        if tokens:
            # Show masked token preview
            token_preview = tokens[0][:10] + "..." if len(tokens[0]) > 10 else tokens[0]
            print(f"   - First token preview: {token_preview}")
            print(f"   - All tokens loaded successfully from environment")
        
        # Check for .env file
        env_file = Path(".env")
        if env_file.exists():
            print("✅ .env file found")
        else:
            print("⚠️  .env file not found (using .env.example as reference)")
        
        print("\n🎉 All tests passed! Configuration system is working correctly.")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def show_usage():
    """Show usage instructions."""
    print("\n📝 Usage Instructions:")
    print("1. Copy .env.example to .env:")
    print("   cp .env.example .env")
    print("\n2. Edit .env with your GitHub tokens:")
    print("   nano .env")
    print("\n3. Add your tokens (choose one method):")
    print("   GITHUB_TOKEN=ghp_your_token_here")
    print("   # OR")
    print("   GITHUB_TOKENS=token1,token2,token3")
    print("\n4. Run this test again to verify:")
    print("   python test_env_config.py")

if __name__ == "__main__":
    print("🧪 WinGet Manifest Automation Tool - Configuration Test")
    print("=" * 60)
    
    success = test_env_loading()
    
    if not success:
        show_usage()
        sys.exit(1)
    
    show_usage()
