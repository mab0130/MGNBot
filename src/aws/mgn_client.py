"""
AWS MGN Client for managing Application Migration Service
"""

import boto3
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from botocore.exceptions import ClientError, NoCredentialsError

from src.models.server import SourceServer, ServerStatus, ReplicationStatus

logger = logging.getLogger(__name__)

class MGNClient:
    """AWS MGN (Application Migration Service) client"""
    
    def __init__(self, aws_config):
        self.aws_config = aws_config
        self.mgn_client = aws_config.get_client('mgn')
        self.ec2_client = aws_config.get_client('ec2')
        
    def get_source_servers(self, filters: Optional[Dict[str, Any]] = None) -> List[SourceServer]:
        """Get all source servers from AWS MGN"""
        try:
            logger.info("Fetching source servers from AWS MGN...")
            
            # Build request parameters
            request_params = {}
            if filters:
                if 'status' in filters:
                    request_params['filters'] = {
                        'name': 'lifeCycle.state',
                        'values': [filters['status']]
                    }
            
            # Get source servers
            response = self.mgn_client.describe_source_servers(**request_params)
            
            # Debug: Log the response structure
            logger.debug(f"MGN API response keys: {list(response.keys()) if isinstance(response, dict) else 'Not a dict'}")
            logger.debug(f"Response type: {type(response)}")
            
            source_servers = []
            
            # Handle different response formats
            if isinstance(response, dict):
                items = response.get('items', [])
            elif isinstance(response, list):
                items = response
            else:
                logger.error(f"Unexpected response type: {type(response)}")
                logger.error(f"Response content: {response}")
                return []
            
            logger.info(f"Found {len(items)} source servers in response")
            
            for i, server_data in enumerate(items):
                try:
                    logger.debug(f"Processing server {i+1}/{len(items)}: {type(server_data)}")
                    
                    # Ensure server_data is a dictionary
                    if isinstance(server_data, str):
                        logger.warning(f"Server data is string, skipping: {server_data[:100]}...")
                        continue
                    elif not isinstance(server_data, dict):
                        logger.warning(f"Server data is not dict, type: {type(server_data)}, skipping")
                        continue
                    
                    source_server = self._parse_source_server(server_data)
                    source_servers.append(source_server)
                    
                except Exception as e:
                    server_id = server_data.get('sourceServerID', f'unknown-{i}') if isinstance(server_data, dict) else f'unknown-{i}'
                    logger.warning(f"Failed to parse source server {server_id}: {e}")
                    continue
            
            logger.info(f"Successfully parsed {len(source_servers)} source servers")
            return source_servers
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'UnauthorizedOperation':
                logger.error("Insufficient permissions to access MGN service")
                raise Exception("Insufficient permissions. Ensure your AWS credentials have MGN access.")
            elif error_code == 'InvalidParameterValue':
                logger.error(f"Invalid parameter in MGN request: {e}")
                raise Exception(f"Invalid request parameters: {e}")
            else:
                logger.error(f"AWS MGN API error: {e}")
                raise Exception(f"AWS MGN error: {e}")
        except Exception as e:
            logger.error(f"Failed to fetch source servers: {e}")
            raise
    
    def _parse_source_server(self, server_data: Dict[str, Any]) -> SourceServer:
        """Parse AWS MGN source server data into our model"""
        try:
            # Debug: Log the server data structure
            logger.debug(f"Parsing server data keys: {list(server_data.keys())}")
            
            # Extract basic information
            source_server_id = server_data.get('sourceServerID', '')
            if not source_server_id:
                raise ValueError("Missing sourceServerID")
            
            name = self._extract_server_name(server_data)
            
            # Parse status - handle nested structure
            life_cycle = server_data.get('lifeCycle', {})
            if isinstance(life_cycle, dict):
                status = self._parse_server_status(life_cycle.get('state', ''))
                logger.debug(f"Server {source_server_id} status: {life_cycle.get('state', '')} -> {status}")
            else:
                status = ServerStatus.UNKNOWN
            
            # Parse replication status - handle nested structure
            replication_data = server_data.get('dataReplicationInfo', {})
            if isinstance(replication_data, dict):
                replication_status = self._parse_replication_status(replication_data)
                logger.debug(f"Server {source_server_id} replication: {replication_data.get('dataReplicationState', '')} -> {replication_status}")
            else:
                replication_status = ReplicationStatus.UNKNOWN
            
            # Extract additional information
            last_seen = None
            last_launch_result = server_data.get('lastLaunchResult', {})
            if isinstance(last_launch_result, dict):
                last_seen_str = last_launch_result.get('lastLaunchTime')
                if last_seen_str:
                    try:
                        last_seen = datetime.fromisoformat(last_seen_str.replace('Z', '+00:00'))
                        logger.debug(f"Server {source_server_id} lastLaunchTime: {last_seen}")
                    except ValueError:
                        logger.warning(f"Could not parse lastLaunchTime: {last_seen_str}")
            
            # If no lastLaunchTime, try lastSeenByServiceDateTime from lifeCycle
            if not last_seen:
                life_cycle = server_data.get('lifeCycle', {})
                if isinstance(life_cycle, dict):
                    last_seen_str = life_cycle.get('lastSeenByServiceDateTime')
                    if last_seen_str:
                        try:
                            last_seen = datetime.fromisoformat(last_seen_str.replace('Z', '+00:00'))
                            logger.debug(f"Server {source_server_id} lastSeenByServiceDateTime: {last_seen}")
                        except ValueError:
                            logger.warning(f"Could not parse lastSeenByServiceDateTime: {last_seen_str}")
            
            # Get test instance information
            test_instance_id = None
            test_instance_state = None
            
            # Check for launched instance information
            launched_instance = server_data.get('launchedInstance', {})
            if isinstance(launched_instance, dict):
                test_instance_id = launched_instance.get('ec2InstanceID')
                test_instance_state = launched_instance.get('state')
                logger.debug(f"Server {source_server_id} launchedInstance: {test_instance_id} ({test_instance_state})")
            
            # If no launched instance, check for test instance in other fields
            if not test_instance_id:
                # Check if there's a test instance ID in the server data
                test_instance_id = server_data.get('testInstanceID')
                if test_instance_id:
                    test_instance_state = "running"  # Default state
                    logger.debug(f"Server {source_server_id} testInstanceID: {test_instance_id}")
            
            # If still no test instance, check for any instance-related fields
            if not test_instance_id:
                # Check for any field that might contain an instance ID
                for key, value in server_data.items():
                    if isinstance(value, str) and value.startswith('i-') and len(value) > 10:
                        test_instance_id = value
                        test_instance_state = "running"  # Default state
                        logger.debug(f"Server {source_server_id} found instance ID in {key}: {test_instance_id}")
                        break
            
            # Try to get test instance state from EC2 if we have an instance ID
            if test_instance_id and not test_instance_state:
                try:
                    # This would require EC2 permissions, but let's try
                    if hasattr(self, 'ec2_client') and self.ec2_client:
                        response = self.ec2_client.describe_instances(InstanceIds=[test_instance_id])
                        if response.get('Reservations'):
                            instance = response['Reservations'][0]['Instances'][0]
                            test_instance_state = instance.get('State', {}).get('Name', 'unknown')
                            logger.debug(f"Server {source_server_id} EC2 instance state: {test_instance_state}")
                except Exception as e:
                    logger.debug(f"Could not get EC2 instance state for {test_instance_id}: {e}")
                    test_instance_state = "unknown"
            
            # Get target instance information
            target_instance_id = None
            target_instance_type = None
            if 'targetInstanceIDRightSizingMethod' in server_data:
                target_instance_id = server_data.get('targetInstanceIDRightSizingMethod')
            
            # Try to get target instance type from source properties
            source_props = server_data.get('sourceProperties', {})
            if isinstance(source_props, dict):
                target_instance_type = source_props.get('recommendedInstanceType')
                logger.debug(f"Server {source_server_id} recommendedInstanceType: {target_instance_type}")
            
            # Extract tags
            tags = {}
            server_tags = server_data.get('tags', {})
            if isinstance(server_tags, dict):
                # Tags are already in key-value format
                tags = server_tags
            elif isinstance(server_tags, list):
                # Tags are in list format with 'key' and 'value' properties
                for tag in server_tags:
                    if isinstance(tag, dict) and 'key' in tag and 'value' in tag:
                        tags[tag['key']] = tag['value']
            
            logger.debug(f"Server {source_server_id} tags: {tags}")
            
            # Extract description
            description = server_data.get('description', '')
            
            return SourceServer(
                source_server_id=source_server_id,
                name=name,
                status=status,
                replication_status=replication_status,
                region=self.aws_config.region,
                last_seen_date_time=last_seen,
                target_instance_id=target_instance_id,
                target_instance_type=target_instance_type,
                test_instance_id=test_instance_id,
                test_instance_state=test_instance_state,
                tags=tags,
                description=description
            )
            
        except Exception as e:
            logger.error(f"Error parsing source server data: {e}")
            logger.error(f"Server data: {server_data}")
            raise
    
    def _extract_server_name(self, server_data: Dict[str, Any]) -> str:
        """Extract server name from various possible sources"""
        # Try to get name from tags first
        server_tags = server_data.get('tags', {})
        if isinstance(server_tags, dict):
            # Tags are in key-value format
            if 'Name' in server_tags:
                return server_tags['Name']
        elif isinstance(server_tags, list):
            # Tags are in list format with 'key' and 'value' properties
            for tag in server_tags:
                if isinstance(tag, dict) and tag.get('key', '').lower() == 'name':
                    return tag.get('value', 'Unknown')
        
        # Try to get from description
        if server_data.get('description'):
            return server_data['description']
        
        # Try to get from hostname
        if server_data.get('isArchived') is False:
            # For active servers, try to get hostname
            source_props = server_data.get('sourceProperties', {})
            if isinstance(source_props, dict):
                identification_hints = source_props.get('identificationHints', {})
                if isinstance(identification_hints, dict) and identification_hints.get('hostname'):
                    return identification_hints['hostname']
        
        # Fallback to server ID
        server_id = server_data.get('sourceServerID', 'Unknown')
        return f"Server-{server_id[:8]}" if len(server_id) >= 8 else f"Server-{server_id}"
    
    def _parse_server_status(self, aws_status: str) -> ServerStatus:
        """Parse AWS MGN status to our enum"""
        status_mapping = {
            'READY_FOR_TEST': ServerStatus.READY_FOR_TEST,
            'READY_FOR_TESTING': ServerStatus.READY_FOR_TESTING,
            'READY_FOR_CUTOVER': ServerStatus.READY_FOR_CUTOVER,
            'CUTOVER_IN_PROGRESS': ServerStatus.CUTOVER_IN_PROGRESS,
            'CUTOVER_COMPLETE': ServerStatus.CUTOVER_COMPLETE,
            'CUTOVER_COMPLETED': ServerStatus.CUTOVER_COMPLETED,
            'STOPPED': ServerStatus.STOPPED,
            'STALLED': ServerStatus.STALLED,
            'ERROR': ServerStatus.ERROR,
            'DISCONNECTED': ServerStatus.DISCONNECTED,
            'NOT_READY': ServerStatus.NOT_READY,
            'TEST_IN_PROGRESS': ServerStatus.TEST_IN_PROGRESS,
            'TEST_COMPLETE': ServerStatus.TEST_COMPLETE,
            'TEST_COMPLETED': ServerStatus.TEST_COMPLETED,
            'TEST_FAILED': ServerStatus.TEST_FAILED
        }
        
        return status_mapping.get(aws_status, ServerStatus.UNKNOWN)
    
    def _parse_replication_status(self, replication_data: Dict[str, Any]) -> ReplicationStatus:
        """Parse replication status from AWS data"""
        if not replication_data or not isinstance(replication_data, dict):
            return ReplicationStatus.UNKNOWN
        
        # Check for specific replication states
        replication_state = replication_data.get('dataReplicationState', '')
        if replication_state == 'STOPPED':
            return ReplicationStatus.STOPPED
        elif replication_state == 'FAILED':
            return ReplicationStatus.FAILED
        elif replication_state == 'INITIAL_SYNC':
            return ReplicationStatus.INITIAL_SYNC
        elif replication_state == 'INITIAL_SYNC_COMPLETE':
            return ReplicationStatus.REPLICATED
        elif replication_state == 'BACKLOG':
            return ReplicationStatus.BACKLOG
        elif replication_state == 'CONTINUOUS':
            return ReplicationStatus.CONTINUOUS
        
        # Check for lag duration (indicates active replication)
        lag_duration = replication_data.get('lagDuration', '')
        if lag_duration and lag_duration != 'P0D':  # P0D means no lag
            return ReplicationStatus.REPLICATING
        
        # If we have replication data but no specific state, assume replicated
        if replication_data.get('lastSnapshotDateTime'):
            return ReplicationStatus.REPLICATED
        
        return ReplicationStatus.UNKNOWN
    
    def launch_test_instances(self, source_server_ids: List[str], instance_type: str = None, 
                             subnet_id: str = None, auto_terminate: bool = False, 
                             custom_tags: Dict[str, str] = None) -> Dict[str, Any]:
        """Launch test instances for specified source servers"""
        try:
            logger.info(f"Launching test instances for {len(source_server_ids)} servers...")
            
            results = {
                'successful': [],
                'failed': [],
                'total': len(source_server_ids)
            }
            
            for server_id in source_server_ids:
                try:
                    launch_config = {}
                    if instance_type and instance_type != "Use recommended":
                        launch_config['targetInstanceTypeRightSizingMethod'] = 'NONE'
                        launch_config['targetInstanceType'] = instance_type

                    if subnet_id:
                        launch_config['launchDisposition'] = 'STOPPED' # Required when specifying subnet
                        launch_config['subnetId'] = subnet_id.split(' ')[0]

                    if launch_config:
                        self.mgn_client.update_launch_configuration(
                            sourceServerID=server_id,
                            **launch_config
                        )
                        logger.info(f"Updated launch configuration for server {server_id}")

                    response = self.mgn_client.start_test(sourceServerIDs=[server_id])
                    
                    job_id = response.get('job', {}).get('jobID')
                    results['successful'].append({
                        'server_id': server_id,
                        'job_id': job_id,
                        'status': 'launched'
                    })
                    logger.info(f"Successfully launched test for server {server_id}")
                    
                except ClientError as e:
                    error_msg = e.response['Error']['Message']
                    results['failed'].append({
                        'server_id': server_id,
                        'error': error_msg
                    })
                    logger.error(f"Failed to launch test for server {server_id}: {error_msg}")
                    
            logger.info(f"Test launch completed: {len(results['successful'])} successful, {len(results['failed'])} failed")
            return results
            
        except Exception as e:
            logger.error(f"Failed to launch test instances: {e}")
            raise
    
    def terminate_test_instances(self, source_server_ids: List[str]) -> Dict[str, Any]:
        """Terminate test instances for specified source servers"""
        try:
            logger.info(f"Terminating test instances for {len(source_server_ids)} servers...")
            
            results = {
                'successful': [],
                'failed': [],
                'total': len(source_server_ids)
            }
            
            for server_id in source_server_ids:
                try:
                    # Terminate test instance
                    response = self.mgn_client.stop_test(
                        sourceServerIDs=[server_id]
                    )
                    
                    job_id = response.get('job', {}).get('jobID')
                    results['successful'].append({
                        'server_id': server_id,
                        'job_id': job_id,
                        'status': 'terminated'
                    })
                    
                    logger.info(f"Successfully terminated test for server {server_id}")
                    
                except ClientError as e:
                    error_msg = e.response['Error']['Message']
                    results['failed'].append({
                        'server_id': server_id,
                        'error': error_msg
                    })
                    logger.error(f"Failed to terminate test for server {server_id}: {error_msg}")
                    
            logger.info(f"Test termination completed: {len(results['successful'])} successful, {len(results['failed'])} failed")
            return results
            
        except Exception as e:
            logger.error(f"Failed to terminate test instances: {e}")
            raise
    
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get the status of a specific job"""
        try:
            response = self.mgn_client.describe_jobs(
                filters={
                    'jobIDs': [job_id]
                }
            )
            
            if response.get('items'):
                job = response['items'][0]
                return {
                    'job_id': job.get('jobID'),
                    'status': job.get('status'),
                    'progress_percentage': job.get('progressPercentage', 0),
                    'start_time': job.get('initiatedBy', {}).get('userID'),
                    'end_time': job.get('endTime')
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get job status for {job_id}: {e}")
            return None
    
    def get_available_regions(self) -> List[str]:
        """Get available regions for MGN service"""
        try:
            return boto3.Session().get_available_regions('mgn')
        except Exception as e:
            logger.error(f"Failed to get available regions: {e}")
            return []
    
    def test_connection(self) -> bool:
        """Test MGN service connection"""
        try:
            # Try to describe source servers with a limit
            response = self.mgn_client.describe_source_servers(maxResults=1)
            logger.debug(f"MGN connection test response: {type(response)}")
            return True
        except Exception as e:
            logger.error(f"MGN connection test failed: {e}")
            return False 