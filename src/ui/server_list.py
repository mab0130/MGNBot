"""
Server List Component
"""

import customtkinter as ctk
from typing import List, Callable, Optional
import logging
from datetime import datetime

from src.models.server import SourceServer, ServerStatus, ServerFilter

logger = logging.getLogger(__name__)

class ServerListFrame(ctk.CTkFrame):
    """Server list with filtering and multi-select capabilities"""
    
    def __init__(self, master, on_selection_change: Callable[[List[SourceServer]], None]):
        super().__init__(master)
        
        self.on_selection_change = on_selection_change
        self.servers: List[SourceServer] = []
        self.filtered_servers: List[SourceServer] = []
        self.selected_servers: List[SourceServer] = []
        self.current_filter = ServerFilter()
        
        self._create_widgets()
        self._setup_layout()
        
    def _create_widgets(self):
        """Create UI widgets"""
        
        # Filter frame
        self.filter_frame = ctk.CTkFrame(self)
        
        # Filter controls
        self.filter_label = ctk.CTkLabel(
            self.filter_frame,
            text="Source Servers",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.filter_label.pack(side="left", padx=10, pady=5)
        
        # Status filter
        self.status_label = ctk.CTkLabel(self.filter_frame, text="Status:")
        self.status_label.pack(side="left", padx=(20, 5), pady=5)
        
        self.status_var = ctk.StringVar(value="All")
        self.status_filter = ctk.CTkOptionMenu(
            self.filter_frame,
            variable=self.status_var,
            values=["All"],  # Will be updated dynamically
            command=self._apply_filters
        )
        self.status_filter.pack(side="left", padx=5, pady=5)
        
        # Search box
        self.search_label = ctk.CTkLabel(self.filter_frame, text="Search:")
        self.search_label.pack(side="left", padx=(20, 5), pady=5)
        
        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(
            self.filter_frame,
            textvariable=self.search_var,
            placeholder_text="Search by name or ID...",
            width=200
        )
        self.search_entry.pack(side="left", padx=5, pady=5)
        self.search_entry.bind("<KeyRelease>", self._on_search_change)
        
        # Selection controls
        self.select_all_button = ctk.CTkButton(
            self.filter_frame,
            text="☑️ Select All",
            command=self._select_all,
            width=100
        )
        self.select_all_button.pack(side="right", padx=5, pady=5)
        
        self.select_none_button = ctk.CTkButton(
            self.filter_frame,
            text="☐ Select None",
            command=self._select_none,
            width=100
        )
        self.select_none_button.pack(side="right", padx=5, pady=5)
        
        # Server count label
        self.count_label = ctk.CTkLabel(self.filter_frame, text="(0 servers)")
        self.count_label.pack(side="right", padx=10, pady=5)
        
        # Server list frame
        self.list_frame = ctk.CTkFrame(self)
        
        # Create scrollable frame for server list
        self.scrollable_frame = ctk.CTkScrollableFrame(
            self.list_frame,
            width=800,
            height=400
        )
        
        # Server list (will be populated dynamically)
        self.server_widgets: List[ServerRowWidget] = []
        
    def _setup_layout(self):
        """Setup the layout"""
        self.filter_frame.pack(fill="x", padx=5, pady=5)
        self.list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.scrollable_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
    def update_servers(self, servers: List[SourceServer]):
        """Update the server list"""
        self.servers = servers
        self._update_status_filter_options()
        self._apply_filters()
        
    def _update_status_filter_options(self):
        """Update status filter options based on actual server statuses"""
        if not self.servers:
            return
            
        # Get unique statuses from current servers
        unique_statuses = set(server.status for server in self.servers)
        
        # Map server statuses to display names
        status_display_map = {
            ServerStatus.READY_FOR_TEST: "Ready for Test",
            ServerStatus.READY_FOR_TESTING: "Ready for Testing", 
            ServerStatus.READY_FOR_CUTOVER: "Ready for Cutover",
            ServerStatus.TEST_IN_PROGRESS: "Test in Progress",
            ServerStatus.CUTOVER_IN_PROGRESS: "Cutover in Progress",
            ServerStatus.TEST_COMPLETE: "Test Complete",
            ServerStatus.TEST_COMPLETED: "Test Completed",
            ServerStatus.CUTOVER_COMPLETE: "Cutover Complete",
            ServerStatus.CUTOVER_COMPLETED: "Cutover Completed",
            ServerStatus.TEST_FAILED: "Test Failed",
            ServerStatus.CUTOVER_FAILED: "Cutover Failed",
            ServerStatus.NOT_READY: "Not Ready",
            ServerStatus.DISCONNECTED: "Disconnected",
            ServerStatus.STALLED: "Stalled",
            ServerStatus.ERROR: "Error",
            ServerStatus.STOPPED: "Stopped",
            ServerStatus.UNKNOWN: "Unknown"
        }
        
        # Build list of options starting with "All"
        options = ["All"]
        
        # Add status options that actually exist in the data
        for status in sorted(unique_statuses, key=lambda x: x.value):
            display_name = status_display_map.get(status, status.value.replace('_', ' ').title())
            options.append(display_name)
        
        # Update the dropdown
        current_value = self.status_var.get()
        self.status_filter.configure(values=options)
        
        # Reset to "All" if current selection is no longer valid
        if current_value not in options:
            self.status_var.set("All")
        
    def _apply_filters(self, *args):
        """Apply current filters to server list"""
        self.filtered_servers = []
        
        for server in self.servers:
            if self._matches_filter(server):
                self.filtered_servers.append(server)
                
        self._update_server_list()
        self._update_count_label()
        
    def _matches_filter(self, server: SourceServer) -> bool:
        """Check if server matches current filter"""
        
        # Status filter
        if self.status_var.get() != "All":
            status_map = {
                "Ready for Test": ServerStatus.READY_FOR_TEST,
                "Ready for Testing": ServerStatus.READY_FOR_TESTING,
                "Ready for Cutover": ServerStatus.READY_FOR_CUTOVER,
                "Test in Progress": ServerStatus.TEST_IN_PROGRESS,
                "Test Completed": [ServerStatus.TEST_COMPLETE, ServerStatus.TEST_COMPLETED],
                "Test Failed": ServerStatus.TEST_FAILED,
                "Cutover in Progress": ServerStatus.CUTOVER_IN_PROGRESS,
                "Cutover Completed": [ServerStatus.CUTOVER_COMPLETE, ServerStatus.CUTOVER_COMPLETED],
                "Cutover Failed": ServerStatus.CUTOVER_FAILED,
                "Stalled": ServerStatus.STALLED,
                "Disconnected": ServerStatus.DISCONNECTED,
                "Not Ready": ServerStatus.NOT_READY,
                "Error": ServerStatus.ERROR
            }
            
            expected_status = status_map.get(self.status_var.get())
            if expected_status is None:
                return False
            
            if isinstance(expected_status, list):
                if server.status not in expected_status:
                    return False
            elif server.status != expected_status:
                return False
        
        # Search filter
        search_term = self.search_var.get().lower()
        if search_term:
            if (search_term not in server.name.lower() and 
                search_term not in server.source_server_id.lower()):
                return False
                
        return True
        
    def _on_search_change(self, event):
        """Handle search input changes"""
        self._apply_filters()
        
    def _update_server_list(self):
        """Update the server list display"""
        # Clear existing widgets
        for widget in self.server_widgets:
            widget.destroy()
        self.server_widgets.clear()
        
        # Create header row
        header = ServerRowWidget(
            self.scrollable_frame,
            is_header=True,
            on_checkbox_change=None
        )
        header.pack(fill="x", padx=5, pady=2)
        self.server_widgets.append(header)
        
        # Create server rows
        for server in self.filtered_servers:
            row = ServerRowWidget(
                self.scrollable_frame,
                server=server,
                is_selected=server in self.selected_servers,
                on_checkbox_change=self._on_server_selection
            )
            row.pack(fill="x", padx=5, pady=2)
            self.server_widgets.append(row)
            
    def _update_count_label(self):
        """Update the server count label"""
        total = len(self.servers)
        filtered = len(self.filtered_servers)
        selected = len(self.selected_servers)
        
        if total == filtered:
            self.count_label.configure(text=f"({total} servers, {selected} selected)")
        else:
            self.count_label.configure(text=f"({filtered}/{total} servers, {selected} selected)")
            
    def _select_all(self):
        """Select all visible servers"""
        self.selected_servers = self.filtered_servers.copy()
        self._update_selection_display()
        self.on_selection_change(self.selected_servers)
        
    def _select_none(self):
        """Deselect all servers"""
        self.selected_servers.clear()
        self._update_selection_display()
        self.on_selection_change(self.selected_servers)
        
    def _on_server_selection(self, server: SourceServer, is_selected: bool):
        """Handle individual server selection"""
        if is_selected and server not in self.selected_servers:
            self.selected_servers.append(server)
        elif not is_selected and server in self.selected_servers:
            self.selected_servers.remove(server)
            
        self._update_selection_display()
        self.on_selection_change(self.selected_servers)
        
    def _update_selection_display(self):
        """Update the visual selection state"""
        for widget in self.server_widgets[1:]:  # Skip header
            if hasattr(widget, 'server'):
                widget.update_selection(widget.server in self.selected_servers)


class ServerRowWidget(ctk.CTkFrame):
    """Individual server row widget"""
    
    def __init__(self, master, server: Optional[SourceServer] = None, 
                 is_selected: bool = False, is_header: bool = False,
                 on_checkbox_change: Optional[Callable[[SourceServer, bool], None]] = None):
        super().__init__(master)
        
        self.server = server
        self.is_header = is_header
        self.on_checkbox_change = on_checkbox_change
        self.is_selected = is_selected
        
        self._create_widgets()
        
    def _create_widgets(self):
        """Create row widgets"""
        
        if self.is_header:
            # Header row
            self.checkbox = ctk.CTkCheckBox(self, text="", width=20)
            self.checkbox.configure(state="disabled")
            
            self.name_label = ctk.CTkLabel(self, text="Server Name", font=ctk.CTkFont(weight="bold"))
            self.status_label = ctk.CTkLabel(self, text="Status", font=ctk.CTkFont(weight="bold"))
            self.last_seen_label = ctk.CTkLabel(self, text="Last Seen", font=ctk.CTkFont(weight="bold"))
            self.instance_label = ctk.CTkLabel(self, text="Test Instance", font=ctk.CTkFont(weight="bold"))
            
        else:
            # Server row
            self.checkbox = ctk.CTkCheckBox(
                self, 
                text="",
                command=self._on_checkbox_click,
                width=20
            )
            self.checkbox.select() if self.is_selected else self.checkbox.deselect()
            
            self.name_label = ctk.CTkLabel(self, text=self.server.name)
            self.status_label = ctk.CTkLabel(self, text=self._get_status_display())
            self.last_seen_label = ctk.CTkLabel(self, text=self._get_last_seen_display())
            self.instance_label = ctk.CTkLabel(self, text=self._get_instance_display())
            
        # Layout
        self.checkbox.pack(side="left", padx=5, pady=5)
        self.name_label.pack(side="left", padx=10, pady=5, anchor="w")
        self.status_label.pack(side="left", padx=10, pady=5, anchor="w")
        self.last_seen_label.pack(side="left", padx=10, pady=5, anchor="w")
        self.instance_label.pack(side="left", padx=10, pady=5, anchor="w")
        
    def _on_checkbox_click(self):
        """Handle checkbox click"""
        if self.on_checkbox_change:
            self.on_checkbox_change(self.server, self.checkbox.get())
            
    def update_selection(self, is_selected: bool):
        """Update selection state"""
        self.is_selected = is_selected
        if is_selected:
            self.checkbox.select()
        else:
            self.checkbox.deselect()
            
    def _get_status_display(self) -> str:
        """Get formatted status display"""
        if not self.server:
            return ""
            
        status_icons = {
            # Ready states - Green
            ServerStatus.READY_FOR_TEST: "🟢",
            ServerStatus.READY_FOR_TESTING: "🟢", 
            ServerStatus.READY_FOR_CUTOVER: "🟢",
            
            # In Progress states - Yellow
            ServerStatus.TEST_IN_PROGRESS: "🟡",
            ServerStatus.CUTOVER_IN_PROGRESS: "🟡",
            
            # Success states - Blue
            ServerStatus.TEST_COMPLETE: "🔵",
            ServerStatus.TEST_COMPLETED: "🔵",
            ServerStatus.CUTOVER_COMPLETE: "🔵",
            ServerStatus.CUTOVER_COMPLETED: "🔵",
            
            # Failed/Error states - Red
            ServerStatus.TEST_FAILED: "🔴",
            ServerStatus.CUTOVER_FAILED: "🔴",
            ServerStatus.STALLED: "🔴",
            ServerStatus.ERROR: "🔴",
            
            # Other states - Gray
            ServerStatus.NOT_READY: "⚫",
            ServerStatus.DISCONNECTED: "⚫",
            ServerStatus.STOPPED: "⚫",
            ServerStatus.UNKNOWN: "⚪"
        }
        
        icon = status_icons.get(self.server.status, "⚪")
        
        # Create more user-friendly status labels
        status_labels = {
            ServerStatus.READY_FOR_TEST: "Ready for Test",
            ServerStatus.READY_FOR_TESTING: "Ready for Testing", 
            ServerStatus.READY_FOR_CUTOVER: "Ready for Cutover",
            ServerStatus.TEST_IN_PROGRESS: "Test in Progress",
            ServerStatus.CUTOVER_IN_PROGRESS: "Cutover in Progress",
            ServerStatus.TEST_COMPLETE: "Test Complete",
            ServerStatus.TEST_COMPLETED: "Test Completed",
            ServerStatus.CUTOVER_COMPLETE: "Cutover Complete",
            ServerStatus.CUTOVER_COMPLETED: "Cutover Completed",
            ServerStatus.TEST_FAILED: "Test Failed",
            ServerStatus.CUTOVER_FAILED: "Cutover Failed",
            ServerStatus.NOT_READY: "Not Ready",
            ServerStatus.DISCONNECTED: "Disconnected",
            ServerStatus.STALLED: "Stalled",
            ServerStatus.ERROR: "Error",
            ServerStatus.STOPPED: "Stopped",
            ServerStatus.UNKNOWN: "Unknown"
        }
        
        status_text = status_labels.get(self.server.status, self.server.status.value.replace('_', ' ').title())
        return f"{icon} {status_text}"
        
    def _get_last_seen_display(self) -> str:
        """Get formatted last seen display"""
        if not self.server or not self.server.last_seen_date_time:
            return "Unknown"
            
        try:
            # Get current time in UTC to match AWS timestamps
            from datetime import timezone
            now = datetime.now(timezone.utc)
            
            # Ensure the server's last seen time is timezone-aware
            last_seen = self.server.last_seen_date_time
            if last_seen.tzinfo is None:
                # If it's naive, assume it's UTC
                last_seen = last_seen.replace(tzinfo=timezone.utc)
            
            diff = now - last_seen
            
            if diff.days > 0:
                return f"{diff.days} day(s) ago"
            elif diff.seconds > 3600:
                hours = diff.seconds // 3600
                return f"{hours} hour(s) ago"
            elif diff.seconds > 60:
                minutes = diff.seconds // 60
                return f"{minutes} min ago"
            else:
                return "Just now"
                
        except Exception as e:
            logger.warning(f"Error calculating time difference: {e}")
            # Fallback to showing the raw timestamp
            try:
                return self.server.last_seen_date_time.strftime("%Y-%m-%d %H:%M")
            except:
                return "Unknown"
            
    def _get_instance_display(self) -> str:
        """Get formatted instance display"""
        if not self.server:
            return ""
            
        if self.server.test_instance_id:
            return f"i-{self.server.test_instance_id[-8:]}"
        else:
            return "None" 