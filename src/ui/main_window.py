"""
Main Application Window
"""

import customtkinter as ctk
from typing import List, Optional, Dict, Any
import logging
import threading

from src.aws.config import AWSConfig, create_aws_config_interactive
from src.aws.mgn_client import MGNClient
from src.models.server import SourceServer, ServerFilter, BulkOperationProgress, BulkOperationResult
from src.ui.server_list import ServerListFrame
from src.ui.bulk_actions import BulkActionsFrame
from src.ui.progress import ProgressDialog
from src.ui.profile_dialog import ProfileSelectionDialog

logger = logging.getLogger(__name__)

class MainWindow(ctk.CTk):
    """Main application window"""
    
    def __init__(self, aws_config: AWSConfig):
        super().__init__()
        
        self.aws_config = aws_config
        self.mgn_client = None
        self.servers: List[SourceServer] = []
        self.selected_servers: List[SourceServer] = []
        self.current_filter = ServerFilter()
        
        self._setup_window()
        self._create_widgets()
        self._setup_layout()
        self._initialize_mgn_client()
        
    def _setup_window(self):
        """Configure main window properties"""
        self.title("AWS MGN Helper Bot")
        self.geometry("1200x800")
        self.minsize(800, 600)
        
        # Configure grid weights
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
    def _create_widgets(self):
        """Create and initialize UI widgets"""
        
        # Header frame
        self.header_frame = ctk.CTkFrame(self)
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        self.header_frame.grid_columnconfigure(1, weight=1)
        
        # Title and controls
        self.title_label = ctk.CTkLabel(
            self.header_frame, 
            text="AWS MGN Helper Bot", 
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.title_label.grid(row=0, column=0, padx=10, pady=10)
        
        # Profile info
        profile_info = self.aws_config.get_profile_info()
        self.profile_label = ctk.CTkLabel(
            self.header_frame,
            text=f"Profile: {profile_info['profile_name']} ({'SSO' if profile_info['is_sso'] else 'Standard'})",
            font=ctk.CTkFont(size=12)
        )
        self.profile_label.grid(row=0, column=1, padx=10, pady=10, sticky="w")
        
        # Region selector
        self.region_label = ctk.CTkLabel(self.header_frame, text="Region:")
        self.region_label.grid(row=0, column=2, padx=(20, 5), pady=10)
        
        self.region_var = ctk.StringVar(value=self.aws_config.region)
        self.region_selector = ctk.CTkOptionMenu(
            self.header_frame,
            variable=self.region_var,
            values=["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"],
            command=self._on_region_change
        )
        self.region_selector.grid(row=0, column=3, padx=5, pady=10)
        
        # Profile management button
        self.profile_button = ctk.CTkButton(
            self.header_frame,
            text="👤 Change Profile",
            command=self._change_profile,
            width=120
        )
        self.profile_button.grid(row=0, column=4, padx=10, pady=10)
        
        # Refresh button
        self.refresh_button = ctk.CTkButton(
            self.header_frame,
            text="🔄 Refresh",
            command=self._refresh_servers,
            width=100
        )
        self.refresh_button.grid(row=0, column=5, padx=10, pady=10)
        
        # Settings button
        self.settings_button = ctk.CTkButton(
            self.header_frame,
            text="⚙️ Settings",
            command=self._open_settings,
            width=100
        )
        self.settings_button.grid(row=0, column=6, padx=10, pady=10)
        
        # Main content frame
        self.content_frame = ctk.CTkFrame(self)
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)
        
        # Server list frame
        self.server_list_frame = ServerListFrame(
            self.content_frame,
            on_selection_change=self._on_server_selection_change
        )
        self.server_list_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Bulk actions frame
        self.bulk_actions_frame = BulkActionsFrame(
            self.content_frame,
            on_launch_test=self._launch_bulk_test,
            on_terminate_test=self._terminate_bulk_test,
            aws_config=self.aws_config
        )
        self.bulk_actions_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        
        # Status bar
        self.status_bar = ctk.CTkLabel(
            self,
            text="Ready",
            font=ctk.CTkFont(size=12)
        )
        self.status_bar.grid(row=2, column=0, sticky="ew", padx=10, pady=(5, 10))
        
    def _setup_layout(self):
        """Setup the layout and initial data loading"""
        self._update_status("Initializing...")
        
    def _initialize_mgn_client(self):
        """Initialize the MGN client"""
        try:
            self._update_status("Initializing MGN client...")
            
            # Test AWS connection first
            if not self.aws_config.test_connection():
                self._show_error("AWS connection failed. Please check your credentials.")
                return
            
            # Create MGN client
            self.mgn_client = MGNClient(self.aws_config)
            
            # Test MGN connection
            if not self.mgn_client.test_connection():
                self._show_error("MGN service connection failed. Please check your permissions.")
                return
            
            # Load servers
            self._refresh_servers()
            
        except Exception as e:
            logger.error(f"Failed to initialize MGN client: {e}")
            self._show_error(f"Failed to initialize MGN client: {e}")
    
        
    def _on_region_change(self, region: str):
        """Handle region change"""
        self.aws_config.region = region
        self._update_status(f"Region changed to {region}")
        
        # Reinitialize MGN client with new region
        self._initialize_mgn_client()
        
    def _change_profile(self):
        """Open profile selection dialog"""
        def on_profile_selected(profile_name: str):
            try:
                self._update_status(f"Switching to profile '{profile_name}'...")
                
                # Create new AWS config with selected profile
                new_config = AWSConfig(profile=profile_name, region=self.aws_config.region)
                self.aws_config = new_config
                
                # Update UI
                profile_info = self.aws_config.get_profile_info()
                self.profile_label.configure(
                    text=f"Profile: {profile_info['profile_name']} ({'SSO' if profile_info['is_sso'] else 'Standard'})"
                )
                
                self._update_status(f"Profile changed to {profile_name}, connecting to AWS...")
                
                # Reinitialize with new profile
                self.title("AWS MGN Helper Bot")
                self._initialize_mgn_client()
                
            except Exception as e:
                logger.error(f"Failed to change profile: {e}")
                self._show_error(f"Failed to change profile: {e}")
        
        # Show profile selection dialog
        dialog = ProfileSelectionDialog(self, on_profile_selected)
        dialog.grab_set()
        
    def _refresh_servers(self):
        """Refresh the server list"""
        try:
            self._update_status("Refreshing servers from AWS MGN...")
            
            # Test AWS connection first
            if not self.aws_config.test_connection():
                self._show_error("AWS connection failed. Please check your credentials.")
                return
            
            # Test MGN connection
            if not self.mgn_client.test_connection():
                self._show_error("MGN service connection failed. Please check your permissions.")
                return
            
            # Get servers from AWS MGN
            self.servers = self.mgn_client.get_source_servers()
            self.server_list_frame.update_servers(self.servers)
            self._update_status(f"Loaded {len(self.servers)} servers from AWS MGN")
            
        except Exception as e:
            logger.error(f"Failed to refresh servers: {e}")
            self._show_error(f"Error loading servers: {e}")
            
        
    def _on_server_selection_change(self, selected_servers: List[SourceServer]):
        """Handle server selection changes"""
        self.selected_servers = selected_servers
        self.bulk_actions_frame.update_selection_count(len(selected_servers), selected_servers)
        self._update_status(f"Selected {len(selected_servers)} server(s)")
        
    def _launch_bulk_test(self, config: Dict[str, Any] = None):
        """Launch bulk test instances with configuration"""
        if not self.selected_servers:
            self._show_error("No servers selected")
            return
        
        try:
            server_ids = [server.source_server_id for server in self.selected_servers]
            
            if config:
                logger.info(f"Launch configuration: {config}")
                self._update_status(f"Launching {len(server_ids)} test instances with custom configuration...")
            else:
                self._update_status(f"Launching test instances for {len(server_ids)} servers...")
            
            progress_dialog = ProgressDialog(
                self,
                "Launching Test Instances",
                len(server_ids)
            )
            
            self._launch_test_instances_async(server_ids, progress_dialog, config or {})
            
        except Exception as e:
            logger.error(f"Failed to launch bulk test: {e}")
            self._show_error(f"Failed to launch bulk test: {e}")
            
    def _terminate_bulk_test(self):
        """Terminate bulk test instances"""
        if not self.selected_servers:
            self._show_error("No servers selected")
            return
        
            
        try:
            server_ids = [server.source_server_id for server in self.selected_servers]
            self._update_status(f"Terminating test instances for {len(server_ids)} servers...")
            
            # Show progress dialog
            progress_dialog = ProgressDialog(
                self,
                "Terminating Test Instances",
                len(server_ids)
            )
            
            # Terminate test instances asynchronously
            self._terminate_test_instances_async(server_ids, progress_dialog)
            
        except Exception as e:
            logger.error(f"Failed to terminate bulk test: {e}")
            self._show_error(f"Failed to terminate bulk test: {e}")
            
    def _open_settings(self):
        """Open settings dialog"""
        # TODO: Implement settings dialog
        self._update_status("Settings dialog not implemented yet")
        
    def _update_status(self, message: str):
        """Update status bar message"""
        self.status_bar.configure(text=message)
        logger.info(f"Status: {message}")
        
    def _show_error(self, message: str):
        """Show error message"""
        # TODO: Implement proper error dialog
        self._update_status(f"Error: {message}")
        logger.error(message)
        
    def _launch_test_instances_async(self, server_ids: List[str], progress_dialog: ProgressDialog, config: Dict[str, Any]):
        """Launch test instances asynchronously with proper progress tracking"""
        def launch_operation():
            try:
                progress = BulkOperationProgress(total_servers=len(server_ids))
                
                results = self.mgn_client.launch_test_instances(
                    server_ids,
                    instance_type=config.get('instance_type'),
                    subnet_id=config.get('subnet_id'),
                    auto_terminate=config.get('auto_terminate', False),
                    custom_tags=config.get('custom_tags')
                )
                
                for success_item in results.get('successful', []):
                    server_id = success_item.get('server_id', '')
                    server_name = self._get_server_name_by_id(server_id)
                    
                    result = BulkOperationResult(
                        server_id=server_id,
                        server_name=server_name,
                        success=True,
                        operation_type="launch_test",
                        instance_id=success_item.get('job_id', '')
                    )
                    progress.results.append(result)
                    progress.successful += 1
                    progress.completed += 1
                
                for failed_item in results.get('failed', []):
                    server_id = failed_item.get('server_id', '')
                    server_name = self._get_server_name_by_id(server_id)
                    
                    result = BulkOperationResult(
                        server_id=server_id,
                        server_name=server_name,
                        success=False,
                        operation_type="launch_test",
                        error_message=failed_item.get('error', 'Unknown error')
                    )
                    progress.results.append(result)
                    progress.failed += 1
                    progress.completed += 1
                
                progress_dialog.update_progress(progress)
                
                def update_ui():
                    if results['failed']:
                        error_msg = f"Launch completed with {len(results['failed'])} failures"
                        self._show_error(error_msg)
                    else:
                        self._update_status(f"Successfully launched {len(results['successful'])} test instances")
                    
                    self._refresh_servers()
                
                self.after(100, update_ui)
                
            except Exception as e:
                logger.error(f"Async launch operation failed: {e}")
                
                progress = BulkOperationProgress(total_servers=len(server_ids))
                for server_id in server_ids:
                    server_name = self._get_server_name_by_id(server_id)
                    result = BulkOperationResult(
                        server_id=server_id,
                        server_name=server_name,
                        success=False,
                        operation_type="launch_test",
                        error_message=str(e)
                    )
                    progress.results.append(result)
                    progress.failed += 1
                    progress.completed += 1
                
                progress_dialog.update_progress(progress)
                
                self.after(100, lambda: self._show_error(f"Failed to launch bulk test: {e}"))
        
        thread = threading.Thread(target=launch_operation)
        thread.daemon = True
        thread.start()
        
    def _terminate_test_instances_async(self, server_ids: List[str], progress_dialog: ProgressDialog):
        """Terminate test instances asynchronously with proper progress tracking"""
        def terminate_operation():
            try:
                progress = BulkOperationProgress(total_servers=len(server_ids))
                
                # Terminate test instances
                results = self.mgn_client.terminate_test_instances(server_ids)
                
                # Convert MGN results to BulkOperationResult objects
                for success_item in results.get('successful', []):
                    server_id = success_item.get('server_id', '')
                    server_name = self._get_server_name_by_id(server_id)
                    
                    result = BulkOperationResult(
                        server_id=server_id,
                        server_name=server_name,
                        success=True,
                        operation_type="terminate_test",
                        instance_id=success_item.get('job_id', '')
                    )
                    progress.results.append(result)
                    progress.successful += 1
                    progress.completed += 1
                
                for failed_item in results.get('failed', []):
                    server_id = failed_item.get('server_id', '')
                    server_name = self._get_server_name_by_id(server_id)
                    
                    result = BulkOperationResult(
                        server_id=server_id,
                        server_name=server_name,
                        success=False,
                        operation_type="terminate_test",
                        error_message=failed_item.get('error', 'Unknown error')
                    )
                    progress.results.append(result)
                    progress.failed += 1
                    progress.completed += 1
                
                # Update progress dialog
                progress_dialog.update_progress(progress)
                
                # Update status and refresh server list on main thread
                def update_ui():
                    if results['failed']:
                        error_msg = f"Termination completed with {len(results['failed'])} failures"
                        self._show_error(error_msg)
                    else:
                        self._update_status(f"Successfully terminated {len(results['successful'])} test instances")
                    
                    # Refresh server list
                    self._refresh_servers()
                
                # Schedule UI update on main thread
                self.after(100, update_ui)
                
            except Exception as e:
                logger.error(f"Async terminate operation failed: {e}")
                
                # Create error result for all servers
                progress = BulkOperationProgress(total_servers=len(server_ids))
                for server_id in server_ids:
                    server_name = self._get_server_name_by_id(server_id)
                    result = BulkOperationResult(
                        server_id=server_id,
                        server_name=server_name,
                        success=False,
                        operation_type="terminate_test",
                        error_message=str(e)
                    )
                    progress.results.append(result)
                    progress.failed += 1
                    progress.completed += 1
                
                progress_dialog.update_progress(progress)
                
                # Show error on main thread
                self.after(100, lambda: self._show_error(f"Failed to terminate bulk test: {e}"))
        
        # Start operation in background thread
        thread = threading.Thread(target=terminate_operation)
        thread.daemon = True
        thread.start()
        
    def _get_server_name_by_id(self, server_id: str) -> str:
        """Get server name by ID from current server list"""
        for server in self.servers:
            if server.source_server_id == server_id:
                return server.name
        return f"Server-{server_id[:8]}" 