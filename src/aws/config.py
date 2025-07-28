"""
AWS Configuration Management with Enhanced Authorization Pattern
"""

import os
import boto3
import logging
import json
import subprocess
import sys
from typing import Optional, List, Dict, Any
from pathlib import Path
from botocore.exceptions import NoCredentialsError, ProfileNotFound, ClientError

logger = logging.getLogger(__name__)

class AWSProfileManager:
    """AWS Profile Management with SSO support"""
    
    def __init__(self):
        self.config_file = Path.home() / ".aws" / "config"
        self.credentials_file = Path.home() / ".aws" / "credentials"
        
    def get_profiles(self) -> List[str]:
        """Get all AWS profiles from config file"""
        if not self.config_file.exists():
            logger.warning(f"AWS config file not found at {self.config_file}")
            return []
            
        profiles = []
        try:
            with open(self.config_file, 'r') as f:
                for line in f:
                    if line.strip().startswith('[profile '):
                        profile_name = line.strip()[9:-1]  # Remove '[profile ' and ']'
                        profiles.append(profile_name)
        except Exception as e:
            logger.error(f"Error reading AWS config file: {e}")
            
        return profiles
    
    def get_profile_sso_url(self, profile_name: str) -> Optional[str]:
        """Get SSO start URL for a profile"""
        if not self.config_file.exists():
            return None
            
        try:
            with open(self.config_file, 'r') as f:
                lines = f.readlines()
                
            in_profile = False
            for line in lines:
                line = line.strip()
                if line == f'[profile {profile_name}]':
                    in_profile = True
                    continue
                elif line.startswith('[profile '):
                    in_profile = False
                elif in_profile and line.startswith('sso_start_url'):
                    return line.split('=', 1)[1].strip()
                    
        except Exception as e:
            logger.error(f"Error reading SSO URL for profile {profile_name}: {e}")
            
        return None
    
    def group_profiles_by_sso(self) -> Dict[str, Any]:
        """Group profiles by SSO URL"""
        profiles = self.get_profiles()
        sso_groups = {}
        non_sso_profiles = []
        
        for profile in profiles:
            sso_url = self.get_profile_sso_url(profile)
            if sso_url:
                if sso_url not in sso_groups:
                    sso_groups[sso_url] = []
                sso_groups[sso_url].append(profile)
            else:
                non_sso_profiles.append(profile)
                
        return {
            'sso_groups': sso_groups,
            'non_sso_profiles': non_sso_profiles
        }
    
    def validate_profile(self, profile_name: str) -> bool:
        """Validate if a profile exists and has valid configuration"""
        profiles = self.get_profiles()
        return profile_name in profiles
    
    def attempt_sso_login(self, profile_name: str) -> bool:
        """Attempt SSO login for a profile"""
        try:
            logger.info(f"Attempting SSO login for profile '{profile_name}'...")
            result = subprocess.run(
                ['aws', 'sso', 'login', '--profile', profile_name],
                capture_output=True,
                text=True,
                check=True
            )
            logger.info(f"SSO login successful for profile '{profile_name}'")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"SSO login failed for profile '{profile_name}': {e.stderr}")
            return False
        except FileNotFoundError:
            logger.error("AWS CLI not found. Please install AWS CLI v2.")
            return False

class AWSConfig:
    """Enhanced AWS configuration and client management"""
    
    def __init__(self, profile: Optional[str] = None, region: Optional[str] = None):
        self.profile_manager = AWSProfileManager()
        self.profile = profile or os.getenv("AWS_PROFILE", "default")
        self.region = region or os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        self.session = None
        self._initialize_session()
        
    def _initialize_session(self):
        """Initialize AWS session with enhanced error handling"""
        try:
            # Validate profile exists
            if not self.profile_manager.validate_profile(self.profile):
                logger.warning(f"Profile '{self.profile}' not found in AWS config")
                self._handle_missing_profile()
                return
                
            # Create session
            if self.profile != "default":
                self.session = boto3.Session(profile_name=self.profile, region_name=self.region)
            else:
                self.session = boto3.Session(region_name=self.region)
            
            # Test credentials with a simple API call
            self._test_credentials()
            logger.info(f"AWS session initialized successfully for profile: {self.profile}, region: {self.region}")
            
        except (NoCredentialsError, ProfileNotFound) as e:
            logger.error(f"AWS credentials not found: {e}")
            self._handle_credential_error()
        except Exception as e:
            logger.error(f"Failed to initialize AWS session: {e}")
            self._handle_session_error(e)
    
    def _test_credentials(self):
        """Test AWS credentials with a simple API call"""
        try:
            sts = self.session.client('sts')
            identity = sts.get_caller_identity()
            logger.info(f"Authenticated as: {identity['Arn']}")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code in ['ExpiredToken', 'InvalidToken']:
                logger.error("AWS token is expired or invalid")
                self._handle_expired_token()
            else:
                raise
    
    def _handle_missing_profile(self):
        """Handle missing profile scenario"""
        logger.error(f"Profile '{self.profile}' not found in AWS configuration")
        logger.info("Available profiles:")
        
        profile_groups = self.profile_manager.group_profiles_by_sso()
        
        # Show SSO groups
        for sso_url, profiles in profile_groups['sso_groups'].items():
            logger.info(f"  SSO: {sso_url}")
            for profile in profiles:
                logger.info(f"    - {profile}")
        
        # Show non-SSO profiles
        if profile_groups['non_sso_profiles']:
            logger.info("  Non-SSO Profiles:")
            for profile in profile_groups['non_sso_profiles']:
                logger.info(f"    - {profile}")
        
        raise ProfileNotFound(profile=self.profile)
    
    def _handle_credential_error(self):
        """Handle credential error scenario"""
        logger.error("AWS credentials are missing or invalid")
        logger.info("To resolve this issue:")
        
        # Check if it's an SSO profile
        sso_url = self.profile_manager.get_profile_sso_url(self.profile)
        if sso_url:
            logger.info(f"  - This appears to be an SSO profile. Run: aws sso login --profile {self.profile}")
        else:
            logger.info("  - Run 'aws configure' to set up credentials")
            logger.info("  - Or set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables")
        
        raise NoCredentialsError()
    
    def _handle_expired_token(self):
        """Handle expired token scenario"""
        logger.error("AWS token is expired")
        logger.info("To refresh your credentials:")
        
        sso_url = self.profile_manager.get_profile_sso_url(self.profile)
        if sso_url:
            logger.info(f"  - Run: aws sso login --profile {self.profile}")
        else:
            logger.info("  - Run 'aws configure' to refresh credentials")
            logger.info("  - Or refresh your session token")
        
        raise NoCredentialsError()
    
    def _handle_session_error(self, error: Exception):
        """Handle general session error"""
        logger.error(f"AWS session initialization failed: {error}")
        logger.info("Please check:")
        logger.info("  - AWS CLI is installed and in PATH")
        logger.info("  - AWS credentials are properly configured")
        logger.info("  - Network connectivity to AWS")
        raise error
    
    def get_client(self, service_name: str):
        """Get AWS service client"""
        if not self.session:
            raise RuntimeError("AWS session not initialized")
        return self.session.client(service_name)
    
    def get_resource(self, service_name: str):
        """Get AWS service resource"""
        if not self.session:
            raise RuntimeError("AWS session not initialized")
        return self.session.resource(service_name)
    
    def get_available_regions(self, service_name: str) -> List[str]:
        """Get available regions for a service"""
        try:
            return boto3.Session().get_available_regions(service_name)
        except Exception as e:
            logger.error(f"Failed to get available regions for {service_name}: {e}")
            return []
    
    def refresh_credentials(self) -> bool:
        """Attempt to refresh credentials"""
        try:
            # For SSO profiles, attempt login
            sso_url = self.profile_manager.get_profile_sso_url(self.profile)
            if sso_url:
                return self.profile_manager.attempt_sso_login(self.profile)
            else:
                logger.info("Non-SSO profile detected. Please refresh credentials manually.")
                return False
        except Exception as e:
            logger.error(f"Failed to refresh credentials: {e}")
            return False
    
    def test_connection(self) -> bool:
        """Test AWS connection and permissions"""
        try:
            sts = self.get_client('sts')
            identity = sts.get_caller_identity()
            logger.info(f"Connection test successful: {identity['Arn']}")
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def get_profile_info(self) -> Dict[str, Any]:
        """Get information about the current profile"""
        sso_url = self.profile_manager.get_profile_sso_url(self.profile)
        return {
            'profile_name': self.profile,
            'region': self.region,
            'is_sso': sso_url is not None,
            'sso_url': sso_url,
            'session_active': self.session is not None
        }

def create_aws_config_interactive() -> AWSConfig:
    """Create AWS config interactively with enhanced user experience"""
    profile_manager = AWSProfileManager()
    
    print("\n" + "="*60)
    print("AWS MGN Helper Bot - Interactive Configuration")
    print("="*60)
    
    while True:
        # Get available profiles
        profile_groups = profile_manager.group_profiles_by_sso()
        all_profiles = []
        profile_index = 1
        
        print("\nAvailable AWS Profiles:")
        
        # Show SSO groups with numbers
        for sso_url, profiles in profile_groups['sso_groups'].items():
            print(f"\n  SSO: {sso_url}")
            for profile in profiles:
                print(f"    {profile_index:2}. {profile}")
                all_profiles.append(profile)
                profile_index += 1
        
        # Show non-SSO profiles with numbers
        if profile_groups['non_sso_profiles']:
            print(f"\n  Non-SSO Profiles:")
            for profile in profile_groups['non_sso_profiles']:
                print(f"    {profile_index:2}. {profile}")
                all_profiles.append(profile)
                profile_index += 1
        
        # Show additional options
        config_option = profile_index
        refresh_option = profile_index + 1
        
        print(f"\n  Additional Options:")
        print(f"    {config_option:2}. Configure a new profile")
        print(f"    {refresh_option:2}. Refresh profile list")
        
        if not all_profiles:
            print("\n  WARNING: No AWS profiles found.")
            print("      Please configure a profile first.")
        
        # Get user selection
        selection = input(f"\nSelect a profile number, enter profile name, or choose an option: ").strip()
        
        # Handle numeric selection
        if selection.isdigit():
            selected_index = int(selection) - 1
            
            if 0 <= selected_index < len(all_profiles):
                # Selected a profile
                profile_name = all_profiles[selected_index]
                break
            elif selected_index == (config_option - 1):
                # Configure new profile
                print("\n[CONFIG] Launching AWS configuration...")
                config_type = input("Configure SSO (s) or Standard (t) profile? [s/t]: ").strip().lower()
                
                try:
                    import subprocess
                    if config_type == 't':
                        subprocess.run(["aws", "configure"])
                    else:
                        subprocess.run(["aws", "configure", "sso"])
                    print("\n[SUCCESS] Configuration completed. Refreshing profiles...")
                    continue
                except FileNotFoundError:
                    print("\n[ERROR] AWS CLI not found. Please install AWS CLI v2.")
                    continue
            elif selected_index == (refresh_option - 1):
                # Refresh profiles
                print("\n[REFRESH] Refreshing profile list...")
                continue
            else:
                print("\n[ERROR] Invalid selection. Please try again.")
                continue
        else:
            # Handle profile name input
            profile_name = selection
            if profile_name in all_profiles or profile_name == "default":
                break
            else:
                print(f"\n[ERROR] Profile '{profile_name}' not found. Please choose from the list above.")
                continue
    
    # Handle SSO login if needed (outside the main loop)
    sso_url = profile_manager.get_profile_sso_url(profile_name)
    if sso_url:
        print(f"\n[SSO] Profile '{profile_name}' uses SSO authentication")
        print(f"    SSO URL: {sso_url}")
        
        login_choice = input(f"\nAttempt SSO login now? [Y/n]: ").strip().lower()
        if login_choice != 'n':
            print(f"\n[LOGIN] Attempting SSO login for profile '{profile_name}'...")
            if not profile_manager.attempt_sso_login(profile_name):
                print("\n[ERROR] SSO login failed. You can:")
                print("   1. Try again later")
                print("   2. Check your network connection")  
                print("   3. Verify the SSO URL is correct")
                
                retry_choice = input("\nContinue anyway? [y/N]: ").strip().lower()
                if retry_choice != 'y':
                    print("\n[EXIT] Exiting due to SSO login failure.")
                    sys.exit(1)
            else:
                print("\n[SUCCESS] SSO login successful!")
    
    # Create and test config (outside the main loop)
    try:
        print(f"\n[CONFIG] Creating AWS configuration...")
        config = AWSConfig(profile=profile_name)
        
        # Test the connection
        print(f"[TEST] Testing AWS connection...")
        if config.test_connection():
            print(f"\n[SUCCESS] AWS configuration successful!")
            print(f"   Profile: {profile_name}")
            print(f"   Region: {config.region}")
            
            # Show identity information
            try:
                sts = config.get_client('sts')
                identity = sts.get_caller_identity()
                print(f"   Identity: {identity.get('Arn', 'Unknown')}")
            except:
                pass
            
            return config
        else:
            print(f"\n[WARNING] Configuration created but connection test failed.")
            print(f"    The application may not work properly.")
            
            continue_choice = input(f"\nContinue anyway? [y/N]: ").strip().lower()
            if continue_choice == 'y':
                return config
            else:
                print("\n[EXIT] Exiting due to connection test failure.")
                sys.exit(1)
                
    except Exception as e:
        print(f"\n[ERROR] AWS configuration failed: {e}")
        print(f"\n[TROUBLESHOOTING] Suggestions:")
        print(f"   1. Check if profile '{profile_name}' exists: aws configure list-profiles")
        print(f"   2. Test AWS CLI: aws sts get-caller-identity --profile {profile_name}")
        print(f"   3. For SSO profiles, try: aws sso login --profile {profile_name}")
        
        retry_choice = input(f"\nTry again? [Y/n]: ").strip().lower()
        if retry_choice == 'n':
            sys.exit(1)
        else:
            # If they want to try again, we should restart the whole function
            print("\n[RETRY] Restarting interactive configuration...")
            return create_aws_config_interactive() 