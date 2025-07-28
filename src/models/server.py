"""
Server Data Models
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from dataclasses import dataclass, field

class ServerStatus(str, Enum):
    """MGN source server status enumeration"""
    UNKNOWN = "UNKNOWN"
    NOT_READY = "NOT_READY"
    READY_FOR_TEST = "READY_FOR_TEST"
    READY_FOR_TESTING = "READY_FOR_TESTING"
    READY_FOR_CUTOVER = "READY_FOR_CUTOVER"
    CUTOVER_IN_PROGRESS = "CUTOVER_IN_PROGRESS"
    CUTOVER_COMPLETE = "CUTOVER_COMPLETE"
    CUTOVER_COMPLETED = "CUTOVER_COMPLETED"
    CUTOVER_FAILED = "CUTOVER_FAILED"
    TEST_IN_PROGRESS = "TEST_IN_PROGRESS"
    TEST_COMPLETE = "TEST_COMPLETE"
    TEST_COMPLETED = "TEST_COMPLETED"
    TEST_FAILED = "TEST_FAILED"
    STALLED = "STALLED"
    DISCONNECTED = "DISCONNECTED"
    ERROR = "ERROR"
    STOPPED = "STOPPED"

class ReplicationStatus(str, Enum):
    """Replication status enumeration"""
    UNKNOWN = "UNKNOWN"
    REPLICATING = "REPLICATING"
    REPLICATED = "REPLICATED"
    FAILED = "FAILED"
    STOPPED = "STOPPED"
    INITIAL_SYNC = "INITIAL_SYNC"
    BACKLOG = "BACKLOG"
    CONTINUOUS = "CONTINUOUS"

@dataclass
class SourceServer:
    """MGN source server model"""
    source_server_id: str
    name: str
    status: ServerStatus
    replication_status: ReplicationStatus
    region: str
    last_seen_date_time: Optional[datetime] = None
    target_instance_id: Optional[str] = None
    target_instance_type: Optional[str] = None
    test_instance_id: Optional[str] = None
    test_instance_state: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)
    description: Optional[str] = None

@dataclass
class ServerFilter:
    """Server filtering criteria"""
    status_filter: Optional[List[ServerStatus]] = None
    region_filter: Optional[str] = None
    search_term: Optional[str] = None
    has_test_instance: Optional[bool] = None

@dataclass
class BulkOperationResult:
    """Result of a bulk operation"""
    server_id: str
    server_name: str
    success: bool
    operation_type: str
    timestamp: datetime = field(default_factory=datetime.now)
    error_message: Optional[str] = None
    instance_id: Optional[str] = None

@dataclass
class BulkOperationProgress:
    """Progress tracking for bulk operations"""
    total_servers: int
    completed: int = 0
    successful: int = 0
    failed: int = 0
    in_progress: int = 0
    results: List[BulkOperationResult] = field(default_factory=list)
    
    @property
    def progress_percentage(self) -> float:
        """Calculate progress percentage"""
        if self.total_servers == 0:
            return 0.0
        return (self.completed / self.total_servers) * 100
    
    @property
    def is_complete(self) -> bool:
        """Check if operation is complete"""
        return self.completed >= self.total_servers 