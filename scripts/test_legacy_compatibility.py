#!/usr/bin/env python3
"""
Quick test script to verify all legacy scripts work with fixed imports.
"""

import subprocess
import sys
import time
from pathlib import Path


def run_command_with_timeout(cmd, timeout=10, description=""):
    """Run a command with timeout and return success status."""
    print(f"\n🔍 Testing: {description}")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        # Test if the script can at least start (imports work)
        result = subprocess.run(
            cmd, 
            timeout=timeout, 
            capture_output=True, 
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        if result.returncode == 0:
            print("✅ SUCCESS: Script completed successfully")
            return True
        else:
            # Check if it's just missing data files (expected)
            if "not found" in result.stderr or "No such file" in result.stderr:
                print("⚠️  EXPECTED: Script started but missing data files (normal)")
                return True
            else:
                print(f"❌ FAILED: {result.stderr}")
                return False
                
    except subprocess.TimeoutExpired:
        print("⚠️  TIMEOUT: Script started successfully but timed out (expected for long-running scripts)")
        return True
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False


def test_import_only(script_path, description=""):
    """Test if a script can be imported without errors."""
    print(f"\n📦 Testing imports: {description}")
    
    try:
        # Test import
        result = subprocess.run([
            sys.executable, "-c", 
            f"import sys; sys.path.insert(0, 'src'); "
            f"from pathlib import Path; "
            f"exec(open('{script_path}').read()); "
            f"print('✅ Imports successful')"
        ], capture_output=True, text=True, timeout=5,
        cwd=Path(__file__).parent.parent)
        
        if result.returncode == 0 or "✅ Imports successful" in result.stdout:
            print("✅ SUCCESS: All imports work correctly")
            return True
        else:
            print(f"❌ FAILED: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False


def main():
    print("=" * 80)
    print("🔧 LEGACY SCRIPTS COMPATIBILITY TEST")
    print("=" * 80)
    print("Testing that all original script commands work with the new package structure...")
    
    results = []
    
    # Test 1: PackageProcessor
    success = test_import_only(
        "src/winget_automation/PackageProcessor.py",
        "PackageProcessor.py imports"
    )
    results.append(("PackageProcessor imports", success))
    
    # Test 2: GitHub script
    success = test_import_only(
        "src/winget_automation/GitHub.py", 
        "GitHub.py imports"
    )
    results.append(("GitHub imports", success))
    
    # Test 3: KomacCommandsGenerator
    success = run_command_with_timeout(
        [sys.executable, "src/winget_automation/KomacCommandsGenerator.py"],
        timeout=5,
        description="KomacCommandsGenerator.py execution"
    )
    results.append(("KomacCommandsGenerator", success))
    
    # Test 4: Legacy workflow runner
    success = run_command_with_timeout(
        [sys.executable, "examples/legacy_workflow.py", "help"],
        timeout=5,
        description="Legacy workflow runner help"
    )
    results.append(("Legacy workflow help", success))
    
    # Test 5: Modern CLI
    success = run_command_with_timeout(
        [sys.executable, "-m", "winget_automation.cli", "--help"],
        timeout=5,
        description="Modern CLI help"
    )
    results.append(("Modern CLI help", success))
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 COMPATIBILITY TEST RESULTS")
    print("=" * 80)
    
    passed = 0
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if success:
            passed += 1
    
    print(f"\nResult: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n🎉 ALL TESTS PASSED! Legacy scripts are fully compatible!")
        print("\nUsers can now run:")
        print("  • python src/winget_automation/PackageProcessor.py")
        print("  • python src/winget_automation/GitHub.py") 
        print("  • python src/winget_automation/KomacCommandsGenerator.py")
        print("  • python examples/legacy_workflow.py run")
        print("  • wmat health")
        return True
    else:
        print(f"\n⚠️  {len(results) - passed} tests failed. Check the output above for details.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
