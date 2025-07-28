#!/usr/bin/env python3
"""
Installation script for AWS MGN Helper Bot
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"   Command: {command}")
        print(f"   Error: {e.stderr}")
        return False

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"❌ Python 3.8+ required, found {version.major}.{version.minor}")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} is compatible")
    return True

def install_dependencies():
    """Install required dependencies"""
    if not run_command("pip install -r requirements.txt", "Installing dependencies"):
        return False
    
    # Verify key dependencies
    try:
        import customtkinter
        print("✅ CustomTkinter verified")
    except ImportError:
        print("❌ CustomTkinter not found after installation")
        return False
    
    try:
        import boto3
        print("✅ Boto3 verified")
    except ImportError:
        print("❌ Boto3 not found after installation")
        return False
    
    return True

def create_env_file():
    """Create .env file if it doesn't exist"""
    env_file = Path(".env")
    if env_file.exists():
        print("✅ .env file already exists")
        return True
    
    print("📝 Creating .env file...")
    try:
        with open(env_file, "w") as f:
            f.write("# AWS Configuration\n")
            f.write("AWS_DEFAULT_REGION=us-east-1\n")
            f.write("AWS_PROFILE=default\n")
            f.write("\n")
            f.write("# Application Configuration\n")
            f.write("LOG_LEVEL=INFO\n")
            f.write("MAX_CONCURRENT_OPERATIONS=50\n")
            f.write("\n")
            f.write("# UI Configuration\n")
            f.write("THEME=dark\n")
            f.write("WINDOW_WIDTH=1200\n")
            f.write("WINDOW_HEIGHT=800\n")
        
        print("✅ .env file created successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to create .env file: {e}")
        return False

def check_aws_credentials():
    """Check if AWS credentials are configured"""
    print("🔍 Checking AWS credentials...")
    
    try:
        result = subprocess.run(
            ["aws", "sts", "get-caller-identity"], 
            capture_output=True, 
            text=True, 
            timeout=10
        )
        
        if result.returncode == 0:
            print("✅ AWS credentials are configured")
            return True
        else:
            print("⚠️  AWS credentials not found or invalid")
            print("   Please configure AWS credentials using:")
            print("   aws configure")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("⚠️  AWS CLI not found or timeout")
        print("   Please install AWS CLI and configure credentials")
        return False

def main():
    """Main installation process"""
    print("🚀 AWS MGN Helper Bot Installation")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        return 1
    
    # Install dependencies
    if not install_dependencies():
        return 1
    
    # Create .env file
    if not create_env_file():
        return 1
    
    # Check AWS credentials
    aws_configured = check_aws_credentials()
    
    print("\n" + "=" * 50)
    print("📋 Installation Summary:")
    print("✅ Dependencies installed")
    print("✅ Configuration files created")
    
    if aws_configured:
        print("✅ AWS credentials configured")
        print("\n🎉 Installation completed successfully!")
        print("\nTo run the application:")
        print("   python main.py")
    else:
        print("⚠️  AWS credentials need to be configured")
        print("\nTo complete setup:")
        print("1. Install AWS CLI: https://aws.amazon.com/cli/")
        print("2. Configure credentials: aws configure")
        print("3. Run the application: python main.py")
    
    print("\n📚 For more information, see README.md")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 