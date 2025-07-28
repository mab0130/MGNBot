"""
Bulk Actions Component
"""

import customtkinter as ctk
from typing import List, Callable, Optional, Dict, Any
import logging
import threading
from datetime import datetime

from src.models.server import SourceServer

logger = logging.getLogger(__name__)

class BulkActionsFrame(ctk.CTkFrame):
    """Bulk actions panel for test instance operations"""
    
    def __init__(self, master, on_launch_test: Callable[[Dict[str, Any]], None], 
                 on_terminate_test: Callable[[], None], aws_config=None):
        super().__init__(master)
        
        self.on_launch_test = on_launch_test
        self.on_terminate_test = on_terminate_test
        self.selected_count = 0
        self.selected_servers = []  # Store actual server objects
        self.aws_config = aws_config
        self.launch_config = None  # Store launch configuration
        
        self._create_widgets()
        self._setup_layout()
        
    def _create_widgets(self):
        """Create UI widgets"""
        
        # Selection info
        self.selection_label = ctk.CTkLabel(
            self,
            text="Selected: 0 server(s)",
            font=ctk.CTkFont(size=14)
        )
        
        # Action buttons
        self.launch_button = ctk.CTkButton(
            self,
            text="🚀 Launch Bulk Test",
            command=self._launch_bulk_test,
            fg_color="green",
            hover_color="darkgreen",
            width=150
        )
        
        self.terminate_button = ctk.CTkButton(
            self,
            text="🛑 Terminate Test",
            command=self._terminate_bulk_test,
            fg_color="red",
            hover_color="darkred",
            width=150
        )
        
        self.view_selected_button = ctk.CTkButton(
            self,
            text="👁️ View Selected",
            command=self._view_selected,
            width=120
        )
        
        self.clear_button = ctk.CTkButton(
            self,
            text="🗑️ Clear Selection",
            command=self._clear_selection,
            width=120
        )
        
    def _setup_layout(self):
        """Setup the layout"""
        # Top row - selection info and main actions
        top_frame = ctk.CTkFrame(self)
        top_frame.pack(fill="x", padx=5, pady=5)
        
        self.selection_label.pack(side="left", padx=10, pady=5)
        
        # Button group
        button_frame = ctk.CTkFrame(top_frame)
        button_frame.pack(side="right", padx=10, pady=5)
        
        self.launch_button.pack(side="left", padx=5, pady=5)
        self.terminate_button.pack(side="left", padx=5, pady=5)
        self.view_selected_button.pack(side="left", padx=5, pady=5)
        self.clear_button.pack(side="left", padx=5, pady=5)
        
    def update_selection_count(self, count: int, selected_servers: List[SourceServer] = None):
        """Update the selection count display"""
        self.selected_count = count
        self.selected_servers = selected_servers or []
        self.selection_label.configure(text=f"Selected: {count} server(s)")
        
        # Enable/disable buttons based on selection
        has_selection = count > 0
        self.launch_button.configure(state="normal" if has_selection else "disabled")
        self.terminate_button.configure(state="normal" if has_selection else "disabled")
        self.view_selected_button.configure(state="normal" if has_selection else "disabled")
        self.clear_button.configure(state="normal" if has_selection else "disabled")
        
    def _launch_bulk_test(self):
        """Launch bulk test instances"""
        if self.selected_count == 0:
            self._show_warning("No servers selected")
            return
        
        def on_launch_confirmed():
            """Handle launch confirmation from dialog"""
            config = dialog.get_launch_configuration()
            self.launch_config = config
            self.on_launch_test(config)
            
        dialog = BulkTestLaunchDialog(
            self,
            server_count=self.selected_count,
            on_confirm=on_launch_confirmed,
            aws_config=self.aws_config
        )
        dialog.grab_set()
        
    def _terminate_bulk_test(self):
        """Terminate bulk test instances"""
        if self.selected_count == 0:
            self._show_warning("No servers selected")
            return
            
        dialog = BulkTestTerminateDialog(
            self,
            server_count=self.selected_count,
            on_confirm=self.on_terminate_test
        )
        dialog.grab_set()
        
    def _view_selected(self):
        logger.info("View selected servers - not implemented yet")
        
    def _clear_selection(self):
        logger.info("Clear selection requested")
        
    def _show_warning(self, message: str):
        logger.warning(message)


class BulkTestLaunchDialog(ctk.CTkToplevel):
    """A simple dialog for bulk test instance launch configuration."""
    
    def __init__(self, master, server_count: int, on_confirm: Callable[[], None], aws_config=None):
        super().__init__(master)
        
        self.server_count = server_count
        self.on_confirm = on_confirm
        self.aws_config = aws_config
        
        self.subnets = []

        self._setup_window()
        self._create_widgets()
        
        if self.aws_config and getattr(self.aws_config, 'get_client', None):
            self._load_aws_resources()
        else:
            self._populate_mock_data()
        
    def _setup_window(self):
        self.title(f"Launch Test for {self.server_count} Servers")
        self.geometry("500x300")
        self.resizable(False, False)
        self.transient(self.master)
        self.grab_set()

    def _create_widgets(self):
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(padx=20, pady=20, fill="both", expand=True)

        header = ctk.CTkLabel(main_frame, text="Bulk Launch Configuration", font=ctk.CTkFont(size=16, weight="bold"))
        header.pack(pady=(0, 20))

        # Subnet Dropdown
        self.subnet_label = ctk.CTkLabel(main_frame, text="Subnet (Applied to all servers):")
        self.subnet_label.pack(anchor="w")
        self.subnet_var = ctk.StringVar(value="Loading...")
        self.subnet_selector = ctk.CTkOptionMenu(main_frame, variable=self.subnet_var, values=["Loading..."], state="disabled")
        self.subnet_selector.pack(fill="x", pady=(0, 15))

        # Instance Type Dropdown
        self.instance_type_label = ctk.CTkLabel(main_frame, text="Instance Type Override (Optional):")
        self.instance_type_label.pack(anchor="w")
        self.instance_type_var = ctk.StringVar(value="Use recommended")
        self.instance_type_selector = ctk.CTkOptionMenu(main_frame, variable=self.instance_type_var, values=["Use recommended", "t3.micro", "t3.small", "t3.medium", "t3.large"])
        self.instance_type_selector.pack(fill="x", pady=(0, 25))

        # Buttons
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x", side="bottom")

        self.cancel_button = ctk.CTkButton(button_frame, text="Cancel", command=self.destroy)
        self.cancel_button.pack(side="right", padx=(10, 0))
        
        self.launch_button = ctk.CTkButton(button_frame, text=f"Launch {self.server_count} Tests", command=self._launch, fg_color="green", hover_color="darkgreen")
        self.launch_button.pack(side="right")

    def _load_aws_resources(self):
        threading.Thread(target=self._get_resources, daemon=True).start()

    def _get_resources(self):
        try:
            ec2 = self.aws_config.get_client('ec2')
            self.subnets = ec2.describe_subnets().get('Subnets', [])
            self.after(0, self._populate_dropdowns)
        except Exception as e:
            logger.error(f"Failed to load AWS resources: {e}")
            self.after(0, self._show_load_error)

    def _populate_dropdowns(self):
        if self.subnets:
            subnet_options = [f"{s['SubnetId']} ({s.get('CidrBlock', 'N/A')})" for s in self.subnets]
            self.subnet_selector.configure(values=subnet_options, state="normal")
            self.subnet_var.set(subnet_options[0])
        else:
            self.subnet_var.set("No subnets found")

    def _populate_mock_data(self):
        self.subnet_selector.configure(values=["subnet-mock1", "subnet-mock2"], state="normal")
        self.subnet_var.set("subnet-mock1")

    def _show_load_error(self):
        self.subnet_var.set("Error loading subnets")

    def get_launch_configuration(self) -> Dict[str, Any]:
        config = {
            'subnet_id': self.subnet_var.get().split(" ")[0],
        }
        instance_type = self.instance_type_var.get()
        if instance_type != "Use recommended":
            config['instance_type'] = instance_type
        return config

    def _launch(self):
        self.on_confirm()
        self.destroy()


class BulkTestTerminateDialog(ctk.CTkToplevel):
    """Dialog for bulk test instance termination confirmation"""
    
    def __init__(self, master, server_count: int, on_confirm: Callable[[], None]):
        super().__init__(master)
        
        self.server_count = server_count
        self.on_confirm = on_confirm
        
        self._setup_window()
        self._create_widgets()
        
    def _setup_window(self):
        self.title(f"Terminate Test Instances: {self.server_count} servers selected")
        self.geometry("500x400")
        self.resizable(False, False)
        self.transient(self.master)
        self.grab_set()
        
    def _create_widgets(self):
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(padx=20, pady=20, fill="both", expand=True)

        self.warning_label = ctk.CTkLabel(main_frame, text="⚠️ WARNING", font=ctk.CTkFont(size=18, weight="bold"), text_color="red")
        self.warning_label.pack(pady=(0, 10))
        
        warning_text_content = (
            "This will terminate the test for the selected servers, "
            "delete the associated EC2 instances, and reset the servers "
            "to the 'Ready for Testing' status. This action cannot be undone."
        )
        self.warning_text = ctk.CTkLabel(main_frame, text=warning_text_content, wraplength=450)
        self.warning_text.pack(pady=(0, 20))
        
        self.confirm_label = ctk.CTkLabel(main_frame, text="Type 'TERMINATE' to confirm:", font=ctk.CTkFont(size=12, weight="bold"))
        self.confirm_label.pack()
        
        self.confirm_entry = ctk.CTkEntry(main_frame, placeholder_text="TERMINATE", width=300)
        self.confirm_entry.pack(pady=(0, 20))
        self.confirm_entry.bind("<KeyRelease>", self._on_confirm_change)
        
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x", side="bottom")
        
        self.cancel_button = ctk.CTkButton(button_frame, text="Cancel", command=self.destroy)
        self.cancel_button.pack(side="right", padx=(10, 0))
        
        self.terminate_button = ctk.CTkButton(button_frame, text=f"Terminate {self.server_count} Tests", command=self._terminate, fg_color="red", hover_color="darkred", state="disabled")
        self.terminate_button.pack(side="right")
        
    def _on_confirm_change(self, event):
        if self.confirm_entry.get() == "TERMINATE":
            self.terminate_button.configure(state="normal")
        else:
            self.terminate_button.configure(state="disabled")
            
    def _terminate(self):
        if self.confirm_entry.get() == "TERMINATE":
            self.on_confirm()
            self.destroy()
 