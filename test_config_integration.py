#!/usr/bin/env python3
"""Test script to verify config integration works."""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def test_config_integration():
    """Test that configuration integration works."""
    print("🧪 Testing Configuration Integration...")
    
    try:
        # Test 1: Config loading
        print("\n1. Testing config loading...")
        from config import get_config
        config = get_config()
        print(f"✅ Configuration loaded successfully!")
        print(f"   Environment: {config.get('environment')}")
        print(f"   GitHub API URL: {config.get('github', {}).get('api_url')}")
        print(f"   Output directory: {config.get('package_processing', {}).get('output_directory')}")
        print(f"   Batch size: {config.get('package_processing', {}).get('batch_size')}")
        
        # Test 2: TokenManager with config
        print("\n2. Testing TokenManager integration...")
        import os
        os.environ['TOKEN_1'] = 'test_token_123'
        os.environ['GITHUB_TOKENS'] = 'token1,token2,token3'
        
        from utils.token_manager import TokenManager
        token_manager = TokenManager(config)
        print(f"✅ TokenManager initialized with config!")
        print(f"   Available tokens: {len(token_manager.tokens)}")
        
        # Test 3: ProcessingConfig from config
        print("\n3. Testing ProcessingConfig integration...")
        from PackageProcessor import ProcessingConfig
        proc_config = ProcessingConfig.from_config(config)
        print(f"✅ ProcessingConfig created from config!")
        print(f"   Output directory: {proc_config.output_directory}")
        print(f"   Batch size: {proc_config.batch_size}")
        print(f"   Max workers: {proc_config.max_workers}")
        
        print("\n🎉 All configuration integration tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Configuration integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_config_integration()
    sys.exit(0 if success else 1)
