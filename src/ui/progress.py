"""
Progress Tracking Component
"""

import customtkinter as ctk
from typing import List, Callable, Optional
import logging
import threading
import time

from src.models.server import BulkOperationProgress, BulkOperationResult

logger = logging.getLogger(__name__)

class ProgressDialog(ctk.CTkToplevel):
    """Progress dialog for bulk operations"""
    
    def __init__(self, master, title: str, total_servers: int):
        super().__init__(master)
        
        self.title = title
        self.total_servers = total_servers
        self.progress = BulkOperationProgress(total_servers=total_servers)
        self.is_cancelled = False
        
        self._setup_window()
        self._create_widgets()
        self._setup_layout()
        
    def _setup_window(self):
        """Configure dialog window"""
        self.title(f"{self.title}... (0/{self.total_servers} completed)")
        self.geometry("600x400")
        self.resizable(False, False)
        
        # Center the dialog
        self.transient(self.master)
        self.grab_set()
        
    def _create_widgets(self):
        """Create dialog widgets"""
        
        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.set(0)
        
        # Progress text
        self.progress_text = ctk.CTkLabel(
            self,
            text=f"Progress: 0%",
            font=ctk.CTkFont(size=14)
        )
        
        # Status summary
        self.status_frame = ctk.CTkFrame(self)
        
        self.completed_label = ctk.CTkLabel(
            self.status_frame,
            text="Completed: 0",
            font=ctk.CTkFont(size=12)
        )
        
        self.successful_label = ctk.CTkLabel(
            self.status_frame,
            text="Successful: 0",
            font=ctk.CTkFont(size=12)
        )
        
        self.failed_label = ctk.CTkLabel(
            self.status_frame,
            text="Failed: 0",
            font=ctk.CTkFont(size=12)
        )
        
        self.in_progress_label = ctk.CTkLabel(
            self.status_frame,
            text="In Progress: 0",
            font=ctk.CTkFont(size=12)
        )
        
        # Results list
        self.results_label = ctk.CTkLabel(
            self,
            text="Operation Results:",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        
        self.results_text = ctk.CTkTextbox(
            self,
            height=200,
            state="disabled"
        )
        
        # Buttons
        self.cancel_button = ctk.CTkButton(
            self,
            text="Cancel",
            command=self._cancel_operation,
            width=100
        )
        
        self.hide_button = ctk.CTkButton(
            self,
            text="Hide",
            command=self._hide_dialog,
            width=100
        )
        
    def _setup_layout(self):
        """Setup dialog layout"""
        # Progress section
        self.progress_bar.pack(fill="x", padx=20, pady=(20, 5))
        self.progress_text.pack(pady=(0, 20))
        
        # Status summary
        self.status_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        self.completed_label.pack(side="left", padx=10, pady=5)
        self.successful_label.pack(side="left", padx=10, pady=5)
        self.failed_label.pack(side="left", padx=10, pady=5)
        self.in_progress_label.pack(side="left", padx=10, pady=5)
        
        # Results section
        self.results_label.pack(anchor="w", padx=20, pady=(0, 5))
        self.results_text.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Buttons
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        self.cancel_button.pack(side="right", padx=10, pady=10)
        self.hide_button.pack(side="right", padx=10, pady=10)
        
    def update_progress(self, progress: BulkOperationProgress):
        """Update progress display"""
        self.progress = progress
        
        # Update progress bar
        self.progress_bar.set(progress.progress_percentage / 100)
        
        # Update progress text
        self.progress_text.configure(
            text=f"Progress: {progress.progress_percentage:.1f}%"
        )
        
        # Update status labels
        self.completed_label.configure(text=f"Completed: {progress.completed}")
        self.successful_label.configure(text=f"Successful: {progress.successful}")
        self.failed_label.configure(text=f"Failed: {progress.failed}")
        self.in_progress_label.configure(text=f"In Progress: {progress.in_progress}")
        
        # Update results text
        self._update_results_display()
        
        # Update window title
        self.title(f"{self.title}... ({progress.completed}/{self.total_servers} completed)")
        
        # Check if operation is complete
        if progress.is_complete:
            self._on_operation_complete()
            
    def _update_results_display(self):
        """Update the results text display"""
        self.results_text.configure(state="normal")
        self.results_text.delete("1.0", "end")
        
        for result in self.progress.results:
            status_icon = "✅" if result.success else "❌"
            instance_info = f" ({result.instance_id})" if result.instance_id else ""
            error_info = f" - {result.error_message}" if result.error_message else ""
            
            line = f"{status_icon} {result.server_name}{instance_info}{error_info}\n"
            self.results_text.insert("end", line)
            
        self.results_text.configure(state="disabled")
        
    def _on_operation_complete(self):
        """Handle operation completion"""
        # Disable cancel button
        self.cancel_button.configure(state="disabled")
        
        # Update hide button text
        self.hide_button.configure(text="Close")
        
        # Show completion message
        if self.progress.failed == 0:
            self.progress_text.configure(
                text=f"✅ Operation completed successfully! ({self.progress.successful}/{self.total_servers})",
                text_color="green"
            )
        elif self.progress.successful == 0:
            self.progress_text.configure(
                text=f"❌ Operation failed! ({self.progress.failed}/{self.total_servers})",
                text_color="red"
            )
        else:
            self.progress_text.configure(
                text=f"⚠️ Operation completed with errors ({self.progress.successful} success, {self.progress.failed} failed)",
                text_color="orange"
            )
            
    def _cancel_operation(self):
        """Cancel the operation"""
        self.is_cancelled = True
        self.cancel_button.configure(state="disabled", text="Cancelling...")
        logger.info("Operation cancellation requested")
        
    def _hide_dialog(self):
        """Hide the dialog"""
        if self.progress.is_complete:
            self.destroy()
        else:
            self.withdraw()  # Hide but keep running
            
    def is_cancelled(self) -> bool:
        """Check if operation was cancelled"""
        return self.is_cancelled


 