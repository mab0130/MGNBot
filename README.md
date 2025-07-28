# AWS MGN Helper Bot

A desktop application for managing AWS Application Migration Service (MGN) source servers and bulk operations.

## Features

- **Real AWS Integration**: Connect to actual AWS MGN service to manage source servers
- **Multi-Profile Support**: Switch between AWS profiles with SSO and standard authentication
- **Bulk Operations**: Launch and terminate test instances for multiple servers
- **Server Management**: View, filter, and manage source servers with detailed information
- **Demo Mode**: Explore the interface without AWS credentials
- **Modern UI**: Built with CustomTkinter for a modern desktop experience

## Quick Start

### Demo Mode (No AWS Credentials Required)

```bash
python demo.py
```

This launches the application in demo mode with mock data, perfect for exploring the interface.

### Production Mode (With AWS Credentials)

```bash
python main.py
```

The application will:
1. Check for AWS credentials
2. If credentials are missing, offer interactive setup
3. Connect to AWS MGN service
4. Load real source servers from your AWS account with detailed information

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd MGNbot
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure AWS credentials** (for production mode):
   ```bash
   # For SSO profiles
   aws configure sso
   
   # For standard profiles
   aws configure
   ```

## Usage

### Demo Mode

- **Purpose**: Explore the interface without AWS credentials
- **Data**: Uses mock server data
- **Operations**: UI interactions work, but bulk operations are disabled
- **Perfect for**: Learning the interface, demonstrations, testing

### Production Mode

- **Purpose**: Manage real AWS MGN source servers
- **Data**: Fetches actual source servers from AWS MGN with detailed information:
  - Server names and IDs
  - Current status (READY_FOR_TEST, TEST_IN_PROGRESS, etc.)
  - Replication status (CONTINUOUS, REPLICATED, etc.)
  - Last seen timestamp
  - Recommended instance type
  - Test instance information (when available)
  - Tags and metadata
- **Operations**: Full bulk operations (launch/terminate test instances)
- **Requirements**: Valid AWS credentials with MGN permissions

### AWS Profile Management

The application supports multiple AWS profiles:

1. **SSO Profiles**: Automatically handles SSO login
2. **Standard Profiles**: Uses access keys and secret keys
3. **Profile Switching**: Change profiles without restarting the application

### Bulk Operations

1. **Select Servers**: Use checkboxes to select multiple servers
2. **Launch Test Instances**: 
   - Click "Launch Bulk Test"
   - Configure instance type (optional)
   - Monitor progress in real-time
3. **Terminate Test Instances**:
   - Click "Terminate Test"
   - Confirm the operation
   - Monitor progress in real-time

## Project Structure

```
MGNbot/
├── main.py                 # Production application entry point
├── demo.py                 # Demo mode entry point
├── test_app.py            # Test script for dependencies
├── install.py             # Installation helper script
├── requirements.txt       # Python dependencies
├── env.example           # Environment variables template
├── README.md             # This file
├── PRD.md               # Product Requirements Document
├── AWS_AUTHORIZATION_PATTERN.md  # AWS auth pattern documentation
└── src/
    ├── aws/
    │   ├── config.py     # AWS configuration and profile management
    │   └── mgn_client.py # AWS MGN API client with real data parsing
    ├── models/
    │   └── server.py     # Data models for servers and operations
    ├── ui/
    │   ├── main_window.py    # Main application window
    │   ├── server_list.py    # Server list display
    │   ├── bulk_actions.py   # Bulk operation controls
    │   ├── progress.py       # Progress dialogs
    │   └── profile_dialog.py # Profile selection dialog
    └── utils/
        └── async_utils.py    # Async utilities for bulk operations
```

## Configuration

### Environment Variables

Copy `env.example` to `.env` and configure:

```bash
# AWS Configuration
AWS_DEFAULT_REGION=us-east-1
AWS_PROFILE=default

# Application Configuration
LOG_LEVEL=INFO
MAX_CONCURRENT_OPERATIONS=50

# UI Configuration
THEME=dark
WINDOW_WIDTH=1200
WINDOW_HEIGHT=800
```

### AWS Permissions

For production mode, your AWS credentials need these permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "mgn:DescribeSourceServers",
                "mgn:StartTest",
                "mgn:StopTest",
                "mgn:DescribeJobs",
                "ec2:DescribeInstances",
                "sts:GetCallerIdentity"
            ],
            "Resource": "*"
        }
    ]
}
```

## Development

### Running Tests

```bash
python test_app.py
```

### Adding New Features

1. **AWS Integration**: Add new methods to `src/aws/mgn_client.py`
2. **UI Components**: Create new widgets in `src/ui/`
3. **Data Models**: Extend models in `src/models/`

### Debug Mode

```bash
# Set debug logging
export LOG_LEVEL=DEBUG
python main.py
```

## Troubleshooting

### Common Issues

1. **"AWS credentials not found"**
   - Run `aws configure` or `aws configure sso`
   - Check `~/.aws/credentials` and `~/.aws/config`

2. **"MGN service connection failed"**
   - Verify your AWS account has MGN service enabled
   - Check IAM permissions for MGN access
   - Ensure you're in a region where MGN is available

3. **"SSO login failed"**
   - Verify SSO URL is correct in AWS config
   - Check network connectivity
   - Ensure AWS CLI v2 is installed

4. **"Bulk operations not available in demo mode"**
   - Switch to production mode with valid AWS credentials
   - Or use demo mode for UI exploration only

5. **"No additional info" or missing server details**
   - The application now properly parses AWS MGN API responses
   - Last seen timestamps are extracted from `lastSeenByServiceDateTime`
   - Target instance types are extracted from `sourceProperties.recommendedInstanceType`
   - Test instances are shown when available

### Demo Mode vs Production Mode

| Feature | Demo Mode | Production Mode |
|---------|-----------|-----------------|
| **AWS Credentials** | Not required | Required |
| **Data Source** | Mock data | Real AWS MGN |
| **Server Information** | Basic mock data | Full details with timestamps |
| **Bulk Operations** | Disabled | ✅ Enabled |
| **Profile Management** | Limited | Full |
| **Use Case** | Learning, demos | Real work |

### Getting Help

1. **Check logs**: Look for detailed error messages in the console
2. **Test AWS CLI**: Run `aws sts get-caller-identity` to verify credentials
3. **Test MGN access**: Run `aws mgn describe-source-servers` to test permissions
4. **Use demo mode**: If having issues, start with demo mode to verify the UI works

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

For issues and questions:
- Check the troubleshooting section above
- Review the AWS MGN documentation
- Open an issue in the repository 