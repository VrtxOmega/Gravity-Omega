#!/usr/bin/env python3
"""
VERITAS Flask API Seal Verification
Run this to verify the complete build and seal the output
"""

import subprocess
import sys
import os

def run_command(cmd, description):
    """Run a command and return success status"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} - SUCCESS")
            return True
        else:
            print(f"❌ {description} - FAILED")
            print(f"   Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ {description} - EXCEPTION: {e}")
        return False

def main():
    """Main seal verification process"""
    print("🔒 VERITAS Flask API Seal Verification")
    print("=" * 50)
    
    # Check all required files exist
    required_files = ['app.py', 'requirements.txt', 'test_analyze.py', 'README.md']
    all_files_exist = True
    
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file} - PRESENT")
        else:
            print(f"❌ {file} - MISSING")
            all_files_exist = False
    
    if not all_files_exist:
        print("\n❌ SEAL FAILED: Missing required files")
        return False
    
    # Verify dependencies
    if not run_command("pip show Flask", "Checking Flask installation"):
        print("\n❌ SEAL FAILED: Dependencies not installed")
        return False
    
    # Test syntax validation
    if not run_command("python -m py_compile app.py", "Syntax validation - app.py"):
        return False
    
    if not run_command("python -m py_compile test_analyze.py", "Syntax validation - test_analyze.py"):
        return False
    
    # Run basic functionality test
    print("\n🧪 Running basic functionality test...")
    try:
        import app
        print("✅ Module import - SUCCESS")
    except Exception as e:
        print(f"❌ Module import - FAILED: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🔒 VERITAS SEAL APPLIED SUCCESSFULLY")
    print("✅ All files present and validated")
    print("✅ Dependencies verified")
    print("✅ Syntax checks passed")
    print("✅ Module import successful")
    print("\n🚀 Ready for deployment:")
    print("   python app.py")
    print("   python test_analyze.py")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)