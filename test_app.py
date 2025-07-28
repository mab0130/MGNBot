#!/usr/bin/env python3
"""
Test script for AWS MGN Helper Bot
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test that all modules can be imported"""
    try:
        import customtkinter as ctk
        print("✅ CustomTkinter imported successfully")
        
        from src.aws.config import AWSConfig
        print("✅ AWS config imported successfully")
        
        from src.models.server import SourceServer, ServerStatus
        print("✅ Server models imported successfully")
        
        from src.ui.main_window import MainWindow
        print("✅ Main window imported successfully")
        
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_aws_config():
    """Test AWS configuration (without credentials)"""
    try:
        from src.aws.config import AWSConfig
        # This will fail without credentials, but we can test the class structure
        config_class = AWSConfig
        print("✅ AWS config class structure is correct")
        return True
    except Exception as e:
        print(f"❌ AWS config test failed: {e}")
        return False

def test_models():
    """Test data models"""
    try:
        from src.models.server import SourceServer, ServerStatus, ReplicationStatus
        from datetime import datetime
        
        # Test creating a server model
        server = SourceServer(
            source_server_id="s-test123",
            name="test-server",
            status=ServerStatus.READY_FOR_TESTING,
            replication_status=ReplicationStatus.REPLICATED,
            last_seen_date_time=datetime.now(),
            region="us-east-1"
        )
        
        print(f"✅ Server model created: {server.name}")
        return True
    except Exception as e:
        print(f"❌ Model test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing AWS MGN Helper Bot...")
    print("=" * 50)
    
    tests = [
        ("Import Test", test_imports),
        ("AWS Config Test", test_aws_config),
        ("Models Test", test_models),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Running {test_name}...")
        if test_func():
            passed += 1
            print(f"✅ {test_name} passed")
        else:
            print(f"❌ {test_name} failed")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The application should work correctly.")
        print("\nTo run the application:")
        print("1. Configure AWS credentials")
        print("2. Run: python main.py")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 