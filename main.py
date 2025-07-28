#!/usr/bin/env python3
"""
AWS MGN Helper Bot - Main Application Entry Point
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

import customtkinter as ctk
from src.ui.main_window import MainWindow
from src.aws.config import AWSConfig, create_aws_config_interactive

# Load environment variables
load_dotenv()

# Configure logging with debug level for troubleshooting
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "DEBUG")),  # Changed to DEBUG
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def main():
    """Main application entry point"""
    try:
        # Configure CustomTkinter appearance
        ctk.set_appearance_mode(os.getenv("THEME", "dark"))
        ctk.set_default_color_theme("blue")
        
        # Initialize AWS configuration with enhanced error handling
        aws_config = None
        try:
            aws_config = AWSConfig()
            logger.info("AWS configuration initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize AWS configuration: {e}")
            print("\n" + "="*60)
            print("AWS MGN Helper Bot - Configuration Required")
            print("="*60)
            print("The application requires AWS credentials to function.")
            print("\nAvailable options:")
            print("  1. [CONFIG] Configure AWS credentials and try again")
            print("  2. [INTERACTIVE] Use interactive profile configuration")
            
            while True:
                choice = input("\nChoose an option (1-2): ").strip()
                
                if choice == "1":
                    print("\n[CONFIG] To configure AWS credentials, run one of:")
                    print("   For SSO: aws configure sso")
                    print("   For standard: aws configure")
                    print("\nThen restart this application.")
                    return
                elif choice == "2":
                    print("\n[INTERACTIVE] Starting interactive AWS configuration...")
                    try:
                        aws_config = create_aws_config_interactive()
                        break
                    except Exception as config_error:
                        print(f"\n[ERROR] Interactive configuration failed: {config_error}")
                        print("Please configure your credentials properly and try again.")
                        return
                else:
                    print("[ERROR] Invalid choice. Please enter 1 or 2.")
        
        # Ensure we have a valid AWS config before proceeding
        if aws_config is None:
            print("\n[ERROR] No valid AWS configuration available.")
            print("Please configure your credentials properly and try again.")
            sys.exit(1)
        
        # Create and run main window
        app = MainWindow(aws_config)
        app.mainloop()
        
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        print("\n[EXIT] Application interrupted by user. Goodbye!")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Application failed to start: {e}")
        print(f"\n[ERROR] Application failed to start: {e}")
        print("\n[TROUBLESHOOTING] Guide:")
        print("  1. Test AWS connection: aws sts get-caller-identity")
        print("  2. Configure credentials: aws configure sso")
        print("  3. Check AWS CLI installation: aws --version")
        print("  4. Check logs above for detailed error information")
        print("\n[HELP] Need help? Check the README.md for more troubleshooting tips.")
        sys.exit(1)

if __name__ == "__main__":
    main() 