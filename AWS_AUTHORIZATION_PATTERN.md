# AWS Authorization Pattern Integration

This document explains how the AWS MGN Helper Bot integrates the advanced AWS authorization pattern from the `ssmtunnel.ps1` script.

## Overview

The SSM tunnel script implements a sophisticated AWS authorization pattern that handles:
- **Multi-profile management** with SSO and standard profiles
- **Interactive profile selection** with grouping by SSO URLs
- **Automatic credential validation** and error handling
- **SSO login integration** with AWS CLI
- **Profile management** (create, delete, rename)

## Key Components

### 1. AWS Profile Manager (`src/aws/config.py`)

The `AWSProfileManager` class provides comprehensive profile management:

```python
class AWSProfileManager:
    def get_profiles(self) -> List[str]
    def get_profile_sso_url(self, profile_name: str) -> Optional[str]
    def group_profiles_by_sso(self) -> Dict[str, Any]
    def validate_profile(self, profile_name: str) -> bool
    def attempt_sso_login(self, profile_name: str) -> bool
```

**Features:**
- Reads AWS config file (`~/.aws/config`)
- Groups profiles by SSO URLs
- Validates profile existence
- Handles SSO login via AWS CLI

### 2. Enhanced AWS Configuration (`src/aws/config.py`)

The `AWSConfig` class provides robust AWS session management:

```python
class AWSConfig:
    def __init__(self, profile: Optional[str] = None, region: Optional[str] = None)
    def _test_credentials(self)
    def _handle_missing_profile(self)
    def _handle_credential_error(self)
    def _handle_expired_token(self)
    def refresh_credentials(self) -> bool
    def test_connection(self) -> bool
```

**Features:**
- Automatic credential validation
- Detailed error handling with helpful messages
- SSO token refresh capabilities
- Connection testing

### 3. Interactive Profile Selection (`src/ui/profile_dialog.py`)

The `ProfileSelectionDialog` provides a user-friendly interface:

```python
class ProfileSelectionDialog(ctk.CTkToplevel):
    def _load_profiles(self)
    def _create_profile_widget(self, profile_name: str, is_sso: bool, sso_url: str = None)
    def _sso_login(self, profile_name: str)
    def _configure_new_profile(self)
```

**Features:**
- Visual profile grouping (SSO vs Standard)
- One-click SSO login
- Profile configuration integration
- Real-time status updates

## Authorization Flow

### 1. Application Startup

```python
# main.py
try:
    aws_config = AWSConfig()
except Exception as e:
    # Show interactive options
    print("1. Run in demo mode: python demo.py")
    print("2. Configure AWS credentials and try again")
    print("3. Use interactive configuration")
```

### 2. Profile Selection

```python
# Interactive profile selection
def create_aws_config_interactive() -> AWSConfig:
    profile_manager = AWSProfileManager()
    profile_groups = profile_manager.group_profiles_by_sso()
    
    # Show SSO groups
    for sso_url, profiles in profile_groups['sso_groups'].items():
        print(f"  SSO: {sso_url}")
        for profile in profiles:
            print(f"    - {profile}")
    
    # Let user select profile
    profile_name = input("Enter profile name: ")
    
    # Handle SSO login if needed
    sso_url = profile_manager.get_profile_sso_url(profile_name)
    if sso_url:
        profile_manager.attempt_sso_login(profile_name)
    
    return AWSConfig(profile=profile_name)
```

### 3. Credential Validation

```python
def _test_credentials(self):
    try:
        sts = self.session.client('sts')
        identity = sts.get_caller_identity()
        logger.info(f"Authenticated as: {identity['Arn']}")
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code in ['ExpiredToken', 'InvalidToken']:
            self._handle_expired_token()
```

### 4. Error Handling

The system provides specific error handling for different scenarios:

- **Missing Profile**: Shows available profiles and suggests configuration
- **Expired Token**: Offers SSO login or credential refresh
- **Invalid Credentials**: Provides setup instructions
- **Network Issues**: Suggests connectivity checks

## Integration with UI

### Profile Management in Main Window

```python
# src/ui/main_window.py
def _change_profile(self):
    def on_profile_selected(profile_name: str):
        new_config = AWSConfig(profile=profile_name, region=self.aws_config.region)
        self.aws_config = new_config
        
        # Update UI
        profile_info = self.aws_config.get_profile_info()
        self.profile_label.configure(
            text=f"Profile: {profile_info['profile_name']} ({'SSO' if profile_info['is_sso'] else 'Standard'})"
        )
    
    dialog = ProfileSelectionDialog(self, on_profile_selected)
```

### Connection Testing

```python
def _refresh_servers(self):
    # Test AWS connection first
    if not self.aws_config.test_connection():
        self._show_error("AWS connection failed. Please check your credentials.")
        return
```

## Benefits of This Pattern

### 1. **User-Friendly Experience**
- Clear error messages with actionable solutions
- Interactive profile selection
- Visual feedback for SSO vs standard profiles

### 2. **Robust Error Handling**
- Specific handling for different error types
- Automatic credential refresh for SSO
- Graceful fallback to demo mode

### 3. **Multi-Account Support**
- Easy switching between AWS profiles
- Support for both SSO and standard authentication
- Profile grouping by SSO organization

### 4. **Security Best Practices**
- No hardcoded credentials
- Integration with AWS CLI credential management
- Proper token handling and refresh

## Usage Examples

### Basic Usage
```bash
# Run with default profile
python main.py

# Run in demo mode (no credentials needed)
python demo.py
```

### Profile Management
```python
# Interactive profile selection
aws_config = create_aws_config_interactive()

# Manual profile selection
aws_config = AWSConfig(profile="my-sso-profile", region="us-west-2")

# Test connection
if aws_config.test_connection():
    print("✅ Connected successfully")
else:
    print("❌ Connection failed")
```

### SSO Integration
```python
# Attempt SSO login
profile_manager = AWSProfileManager()
if profile_manager.attempt_sso_login("my-sso-profile"):
    print("✅ SSO login successful")
else:
    print("❌ SSO login failed")
```

## Configuration

### Environment Variables
```bash
AWS_PROFILE=my-profile
AWS_DEFAULT_REGION=us-east-1
```

### AWS CLI Configuration
```bash
# Configure SSO profile
aws configure sso

# Configure standard profile
aws configure
```

## Troubleshooting

### Common Issues

1. **"No AWS profiles found"**
   - Run `aws configure` or `aws configure sso`
   - Check `~/.aws/config` file exists

2. **"SSO login failed"**
   - Verify SSO URL is correct
   - Check network connectivity
   - Ensure AWS CLI v2 is installed

3. **"Expired token"**
   - Run `aws sso login --profile <profile-name>`
   - Or use the UI "Login" button for SSO profiles

4. **"Connection failed"**
   - Verify AWS credentials are valid
   - Check network connectivity
   - Ensure proper IAM permissions

### Debug Mode
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

This authorization pattern provides a robust, user-friendly way to handle AWS authentication in desktop applications, making it easy for users to work with multiple AWS accounts and authentication methods. 