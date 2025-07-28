"""
AWS Profile Selection Dialog
"""

import customtkinter as ctk
from typing import Optional, Callable
import logging

from src.aws.config import AWSProfileManager

logger = logging.getLogger(__name__)

class ProfileSelectionDialog(ctk.CTkToplevel):
    """Dialog for selecting AWS profile with SSO support"""
    
    def __init__(self, master, on_profile_selected: Callable[[str], None]):
        super().__init__(master)
        
        self.on_profile_selected = on_profile_selected
        self.profile_manager = AWSProfileManager()
        self.selected_profile = None
        self.profile_var = ctk.StringVar()  # Shared variable for all radio buttons
        
        self._setup_window()
        self._create_widgets()
        self._setup_layout()
        self._load_profiles()
        
    def _setup_window(self):
        """Configure dialog window"""
        self.title("Select AWS Profile")
        self.geometry("600x400")  # Reduced height from 500 to 400
        self.resizable(False, False)
        
        # Center the dialog properly
        self.transient(self.master)
        self.grab_set()
        
        # Center on screen
        self.update_idletasks()
        width = 600
        height = 400
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        
    def _create_widgets(self):
        """Create dialog widgets"""
        
        # Title
        self.title_label = ctk.CTkLabel(
            self,
            text="Select AWS Profile",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        
        # Profile list frame
        self.profile_frame = ctk.CTkFrame(self)
        
        # Create scrollable frame for profiles (reduced height to leave room for buttons)
        self.scrollable_frame = ctk.CTkScrollableFrame(
            self.profile_frame,
            width=550,
            height=200  # Reduced from 300 to 200 to ensure buttons fit
        )
        
        # Profile widgets (will be populated dynamically)
        self.profile_widgets = []
        
        # Button references (will be created in _setup_layout)
        self.refresh_button = None
        self.configure_button = None
        self.manage_button = None
        self.cancel_button = None
        self.select_button = None
        
    def _setup_layout(self):
        """Setup dialog layout"""
        # Title
        self.title_label.pack(pady=(10, 5))
        
        # Profile list (fixed height, no expand)
        self.profile_frame.pack(fill="x", padx=20, pady=(5, 10))
        self.scrollable_frame.pack(fill="both", padx=10, pady=10)
        
        # Buttons frame (always at bottom)
        self.button_frame = ctk.CTkFrame(self)
        self.button_frame.pack(fill="x", side="bottom", padx=20, pady=20)
        
        # IMPORTANT: Select Profile button first (most important)
        self.select_button = ctk.CTkButton(
            self.button_frame,
            text="Select Profile",
            command=self._select_profile,
            fg_color="green",
            hover_color="darkgreen",
            width=140,
            height=35,
            font=ctk.CTkFont(size=12, weight="bold"),
            state="disabled"
        )
        self.select_button.pack(side="right", padx=5, pady=5)
        
        # Cancel button (also important)
        self.cancel_button = ctk.CTkButton(
            self.button_frame,
            text="Cancel",
            command=self.destroy,
            width=100
        )
        self.cancel_button.pack(side="right", padx=5, pady=5)
        
        # Left side utility buttons
        self.refresh_button = ctk.CTkButton(
            self.button_frame,
            text="Refresh Profiles",
            command=self._refresh_profiles,
            width=120
        )
        self.refresh_button.pack(side="left", padx=5, pady=5)
        
        self.configure_button = ctk.CTkButton(
            self.button_frame,
            text="Configure New Profile",
            command=self._configure_new_profile,
            width=150
        )
        self.configure_button.pack(side="left", padx=5, pady=5)
        
        self.manage_button = ctk.CTkButton(
            self.button_frame,
            text="Manage Profiles",
            command=self._manage_profiles,
            width=130
        )
        self.manage_button.pack(side="left", padx=5, pady=5)
        
    def _load_profiles(self):
        """Load and display available profiles"""
        # Clear existing widgets
        for widget in self.profile_widgets:
            widget.destroy()
        self.profile_widgets.clear()
        
        # Get profile groups
        profile_groups = self.profile_manager.group_profiles_by_sso()
        
        # Show SSO groups
        for sso_url, profiles in profile_groups['sso_groups'].items():
            # SSO group header
            sso_header = ctk.CTkLabel(
                self.scrollable_frame,
                text=f"SSO: {sso_url}",
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color="cyan"
            )
            sso_header.pack(anchor="w", padx=10, pady=(10, 5))
            self.profile_widgets.append(sso_header)
            
            # SSO profiles
            for profile in profiles:
                profile_widget = self._create_profile_widget(profile, is_sso=True, sso_url=sso_url)
                self.profile_widgets.append(profile_widget)
        
        # Show non-SSO profiles
        if profile_groups['non_sso_profiles']:
            # Non-SSO header
            nonsso_header = ctk.CTkLabel(
                self.scrollable_frame,
                text="Non-SSO Profiles:",
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color="orange"
            )
            nonsso_header.pack(anchor="w", padx=10, pady=(10, 5))
            self.profile_widgets.append(nonsso_header)
            
            # Non-SSO profiles
            for profile in profile_groups['non_sso_profiles']:
                profile_widget = self._create_profile_widget(profile, is_sso=False)
                self.profile_widgets.append(profile_widget)
        
        # Show message if no profiles found
        if not profile_groups['sso_groups'] and not profile_groups['non_sso_profiles']:
            no_profiles_label = ctk.CTkLabel(
                self.scrollable_frame,
                text="No AWS profiles found.\nPlease configure a profile first.",
                font=ctk.CTkFont(size=12),
                text_color="gray"
            )
            no_profiles_label.pack(pady=20)
            self.profile_widgets.append(no_profiles_label)
            
    def _create_profile_widget(self, profile_name: str, is_sso: bool, sso_url: str = None):
        """Create a profile selection widget"""
        profile_frame = ctk.CTkFrame(self.scrollable_frame)
        profile_frame.pack(fill="x", padx=10, pady=2)
        
        # Profile selection radio button
        radio_button = ctk.CTkRadioButton(
            profile_frame,
            text=profile_name,
            variable=self.profile_var,
            value=profile_name,
            command=lambda: self._on_profile_selection(profile_name)
        )
        radio_button.pack(side="left", padx=10, pady=10)
        
        # Profile type indicator
        type_label = ctk.CTkLabel(
            profile_frame,
            text="SSO" if is_sso else "Standard",
            font=ctk.CTkFont(size=10),
            text_color="cyan" if is_sso else "orange"
        )
        type_label.pack(side="left", padx=10, pady=10)
        
        # SSO login button for SSO profiles
        if is_sso:
            login_button = ctk.CTkButton(
                profile_frame,
                text="Login",
                command=lambda: self._sso_login(profile_name),
                width=60,
                height=25
            )
            login_button.pack(side="right", padx=10, pady=10)
        
        return profile_frame
        
    def _on_profile_selection(self, profile_name: str):
        """Handle profile selection"""
        self.selected_profile = profile_name
        if self.select_button:
            self.select_button.configure(
                state="normal",
                text=f"Select '{profile_name}'"
            )
        
        # Also update window title to show selection
        self.title(f"Select AWS Profile - {profile_name} selected")
        
    def _sso_login(self, profile_name: str):
        """Attempt SSO login for a profile"""
        try:
            if self.select_button:
                self.select_button.configure(state="disabled", text="Logging in...")
            self.update()
            
            success = self.profile_manager.attempt_sso_login(profile_name)
            
            if success:
                # Show success message and auto-select profile
                success_frame = ctk.CTkFrame(self)
                success_frame.pack(pady=5, padx=20, fill="x")
                
                success_label = ctk.CTkLabel(
                    success_frame,
                    text=f"SSO login successful for '{profile_name}'",
                    text_color="green",
                    font=ctk.CTkFont(size=12, weight="bold")
                )
                success_label.pack(pady=10, padx=10)
                
                # Auto-select this profile
                self.profile_var.set(profile_name)
                self.selected_profile = profile_name
                if self.select_button:
                    self.select_button.configure(
                        state="normal",
                        text=f"Select '{profile_name}'"
                    )
                
                # Show auto-use option
                auto_use_frame = ctk.CTkFrame(self)
                auto_use_frame.pack(pady=5)
                
                auto_use_label = ctk.CTkLabel(
                    auto_use_frame,
                    text=f"Profile '{profile_name}' is now ready to use.",
                    font=ctk.CTkFont(size=12)
                )
                auto_use_label.pack(side="left", padx=10, pady=5)
                
                use_now_button = ctk.CTkButton(
                    auto_use_frame,
                    text="Use Now",
                    command=lambda: self._use_profile_now(profile_name, success_frame, auto_use_frame),
                    width=80,
                    height=25,
                    fg_color="green",
                    hover_color="darkgreen"
                )
                use_now_button.pack(side="right", padx=10, pady=5)
                
                # Clean up after 10 seconds if not used
                self.after(10000, lambda: self._cleanup_success_widgets(success_frame, auto_use_frame))
            else:
                # Show error message
                error_label = ctk.CTkLabel(
                    self,
                    text=f"[ERROR] SSO login failed for {profile_name}",
                    text_color="red"
                )
                error_label.pack(pady=5)
                self.after(3000, error_label.destroy)
                
        except Exception as e:
            logger.error(f"SSO login error: {e}")
            error_label = ctk.CTkLabel(
                self,
                text=f"❌ Login error: {str(e)}",
                text_color="red"
            )
            error_label.pack(pady=5)
            self.after(3000, error_label.destroy)
        finally:
            if self.select_button:
                self.select_button.configure(state="normal", text="Select Profile")
            
    def _refresh_profiles(self):
        """Refresh the profile list"""
        # Reset selection state
        self.selected_profile = None
        self.profile_var.set("")
        if self.select_button:
            self.select_button.configure(
                state="disabled", 
                text="Select Profile"
            )
        self.title("Select AWS Profile")
        self._load_profiles()
        
    def _configure_new_profile(self):
        """Open AWS CLI configuration with options"""
        # Create configuration choice dialog
        config_dialog = ctk.CTkToplevel(self)
        config_dialog.title("Configure New Profile")
        config_dialog.geometry("400x300")
        config_dialog.transient(self)
        config_dialog.grab_set()
        
        # Center the dialog
        config_dialog.update_idletasks()
        x = (config_dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (config_dialog.winfo_screenheight() // 2) - (300 // 2)
        config_dialog.geometry(f"400x300+{x}+{y}")
        
        # Title
        title_label = ctk.CTkLabel(
            config_dialog,
            text="Configure New AWS Profile",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=20)
        
        # Instructions
        instructions = ctk.CTkLabel(
            config_dialog,
            text="Choose the type of AWS profile to configure:",
            font=ctk.CTkFont(size=12)
        )
        instructions.pack(pady=10)
        
        # SSO Button
        sso_button = ctk.CTkButton(
            config_dialog,
            text="🔐 Configure SSO Profile",
            command=lambda: self._launch_aws_config(config_dialog, "sso"),
            width=250,
            height=40
        )
        sso_button.pack(pady=10)
        
        # Standard Button
        standard_button = ctk.CTkButton(
            config_dialog,
            text="🔑 Configure Standard Profile",
            command=lambda: self._launch_aws_config(config_dialog, "standard"),
            width=250,
            height=40
        )
        standard_button.pack(pady=10)
        
        # Cancel Button
        cancel_button = ctk.CTkButton(
            config_dialog,
            text="Cancel",
            command=config_dialog.destroy,
            width=100
        )
        cancel_button.pack(pady=20)
        
    def _launch_aws_config(self, dialog, config_type):
        """Launch AWS CLI configuration"""
        try:
            import subprocess
            
            if config_type == "sso":
                subprocess.Popen(["aws", "configure", "sso"])
                msg_text = "AWS SSO configuration opened.\nFollow the prompts to configure your SSO profile."
            else:
                subprocess.Popen(["aws", "configure"])
                msg_text = "AWS CLI configuration opened.\nEnter your access key and secret key."
            
            dialog.destroy()
            
            # Show success message
            msg_label = ctk.CTkLabel(
                self,
                text=msg_text,
                text_color="blue"
            )
            msg_label.pack(pady=5)
            self.after(5000, msg_label.destroy)
            
        except FileNotFoundError:
            dialog.destroy()
            error_label = ctk.CTkLabel(
                self,
                text="❌ AWS CLI not found. Please install AWS CLI v2.",
                text_color="red"
            )
            error_label.pack(pady=5)
            self.after(3000, error_label.destroy)
            
    def _select_profile(self):
        """Select the chosen profile"""
        if self.selected_profile:
            self.on_profile_selected(self.selected_profile)
            self.destroy()
        else:
            # Show error
            error_label = ctk.CTkLabel(
                self,
                text="Please select a profile first",
                text_color="red"
            )
            error_label.pack(pady=5)
            self.after(2000, error_label.destroy)
            
    def _manage_profiles(self):
        """Open profile management dialog"""
        # Create management dialog
        mgmt_dialog = ctk.CTkToplevel(self)
        mgmt_dialog.title("Manage AWS Profiles")
        mgmt_dialog.geometry("500x400")
        mgmt_dialog.transient(self)
        mgmt_dialog.grab_set()
        
        # Center the dialog
        mgmt_dialog.update_idletasks()
        x = (mgmt_dialog.winfo_screenwidth() // 2) - (500 // 2)
        y = (mgmt_dialog.winfo_screenheight() // 2) - (400 // 2)
        mgmt_dialog.geometry(f"500x400+{x}+{y}")
        
        # Title
        title_label = ctk.CTkLabel(
            mgmt_dialog,
            text="Manage AWS Profiles",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=20)
        
        # Profile list for management
        profiles_frame = ctk.CTkScrollableFrame(mgmt_dialog, width=450, height=200)
        profiles_frame.pack(pady=10, padx=20, fill="both", expand=True)
        
        # Get all profiles
        all_profiles = self.profile_manager.get_profiles()
        selected_profile_var = ctk.StringVar()
        
        if all_profiles:
            for profile in all_profiles:
                profile_frame = ctk.CTkFrame(profiles_frame)
                profile_frame.pack(fill="x", padx=5, pady=2)
                
                # Radio button for selection
                radio = ctk.CTkRadioButton(
                    profile_frame,
                    text=profile,
                    variable=selected_profile_var,
                    value=profile
                )
                radio.pack(side="left", padx=10, pady=5)
                
                # Profile type
                sso_url = self.profile_manager.get_profile_sso_url(profile)
                type_text = "SSO" if sso_url else "Standard"
                type_label = ctk.CTkLabel(
                    profile_frame,
                    text=type_text,
                    text_color="cyan" if sso_url else "orange",
                    font=ctk.CTkFont(size=10)
                )
                type_label.pack(side="right", padx=10, pady=5)
        else:
            no_profiles_label = ctk.CTkLabel(
                profiles_frame,
                text="No profiles found",
                text_color="gray"
            )
            no_profiles_label.pack(pady=20)
        
        # Management buttons
        button_frame = ctk.CTkFrame(mgmt_dialog)
        button_frame.pack(fill="x", padx=20, pady=10)
        
        rename_button = ctk.CTkButton(
            button_frame,
            text="✏️ Rename Profile",
            command=lambda: self._rename_profile(selected_profile_var.get(), mgmt_dialog),
            width=120
        )
        rename_button.pack(side="left", padx=5)
        
        delete_button = ctk.CTkButton(
            button_frame,
            text="🗑️ Delete Profile",
            command=lambda: self._delete_profile(selected_profile_var.get(), mgmt_dialog),
            width=120,
            fg_color="red",
            hover_color="darkred"
        )
        delete_button.pack(side="left", padx=5)
        
        close_button = ctk.CTkButton(
            button_frame,
            text="Close",
            command=mgmt_dialog.destroy,
            width=80
        )
        close_button.pack(side="right", padx=5)
        
    def _rename_profile(self, profile_name, parent_dialog):
        """Rename a profile"""
        if not profile_name:
            self._show_temp_message(parent_dialog, "Please select a profile to rename", "red")
            return
        
        # Create rename dialog
        rename_dialog = ctk.CTkInputDialog(
            text=f"Enter new name for profile '{profile_name}':",
            title="Rename Profile"
        )
        new_name = rename_dialog.get_input()
        
        if new_name and new_name != profile_name:
            try:
                self._rename_aws_profile(profile_name, new_name)
                self._show_temp_message(parent_dialog, f"Profile '{profile_name}' renamed to '{new_name}'", "green")
                parent_dialog.destroy()
                self._refresh_profiles()
            except Exception as e:
                self._show_temp_message(parent_dialog, f"Failed to rename profile: {e}", "red")
        
    def _delete_profile(self, profile_name, parent_dialog):
        """Delete a profile with confirmation"""
        if not profile_name:
            self._show_temp_message(parent_dialog, "Please select a profile to delete", "red")
            return
        
        # Create confirmation dialog
        confirm_dialog = ctk.CTkToplevel(parent_dialog)
        confirm_dialog.title("Confirm Deletion")
        confirm_dialog.geometry("400x200")
        confirm_dialog.transient(parent_dialog)
        confirm_dialog.grab_set()
        
        # Center the dialog
        confirm_dialog.update_idletasks()
        x = (confirm_dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (confirm_dialog.winfo_screenheight() // 2) - (200 // 2)
        confirm_dialog.geometry(f"400x200+{x}+{y}")
        
        # Confirmation message
        msg_label = ctk.CTkLabel(
            confirm_dialog,
            text=f"Are you sure you want to delete profile '{profile_name}'?\n\nThis action cannot be undone.",
            font=ctk.CTkFont(size=12)
        )
        msg_label.pack(pady=30)
        
        # Buttons
        button_frame = ctk.CTkFrame(confirm_dialog)
        button_frame.pack(pady=20)
        
        yes_button = ctk.CTkButton(
            button_frame,
            text="Yes, Delete",
            command=lambda: self._confirm_delete(profile_name, confirm_dialog, parent_dialog),
            fg_color="red",
            hover_color="darkred",
            width=100
        )
        yes_button.pack(side="left", padx=10)
        
        no_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=confirm_dialog.destroy,
            width=100
        )
        no_button.pack(side="left", padx=10)
        
    def _confirm_delete(self, profile_name, confirm_dialog, parent_dialog):
        """Confirm and execute profile deletion"""
        try:
            self._delete_aws_profile(profile_name)
            confirm_dialog.destroy()
            parent_dialog.destroy()
            self._show_temp_message(self, f"Profile '{profile_name}' deleted successfully", "green")
            self._refresh_profiles()
        except Exception as e:
            confirm_dialog.destroy()
            self._show_temp_message(parent_dialog, f"Failed to delete profile: {e}", "red")
    
    def _show_temp_message(self, parent, message, color):
        """Show a temporary message"""
        msg_label = ctk.CTkLabel(
            parent,
            text=message,
            text_color=color
        )
        msg_label.pack(pady=5)
        parent.after(3000, msg_label.destroy)
        
    def _rename_aws_profile(self, old_name, new_name):
        """Rename AWS profile in config files"""
        import os
        from pathlib import Path
        
        config_file = Path.home() / ".aws" / "config"
        cred_file = Path.home() / ".aws" / "credentials"
        
        # Update config file
        if config_file.exists():
            content = config_file.read_text()
            updated_content = content.replace(f"[profile {old_name}]", f"[profile {new_name}]")
            config_file.write_text(updated_content)
        
        # Update credentials file
        if cred_file.exists():
            content = cred_file.read_text()
            updated_content = content.replace(f"[{old_name}]", f"[{new_name}]")
            cred_file.write_text(updated_content)
    
    def _delete_aws_profile(self, profile_name):
        """Delete AWS profile from config files"""
        import os
        import re
        from pathlib import Path
        
        config_file = Path.home() / ".aws" / "config"
        cred_file = Path.home() / ".aws" / "credentials"
        
        # Remove from config file
        if config_file.exists():
            content = config_file.read_text()
            # Remove the profile section
            pattern = rf"\[profile {re.escape(profile_name)}\][^\[]*"
            updated_content = re.sub(pattern, "", content, flags=re.MULTILINE)
            config_file.write_text(updated_content.strip())
        
        # Remove from credentials file
        if cred_file.exists():
            content = cred_file.read_text()
            # Remove the profile section
            pattern = rf"\[{re.escape(profile_name)}\][^\[]*"
            updated_content = re.sub(pattern, "", content, flags=re.MULTILINE)
            cred_file.write_text(updated_content.strip())
    
    def _use_profile_now(self, profile_name: str, success_frame, auto_use_frame):
        """Immediately use the selected profile after SSO login"""
        try:
            # Clean up the success widgets
            self._cleanup_success_widgets(success_frame, auto_use_frame)
            
            # Trigger the profile selection
            self.on_profile_selected(profile_name)
            self.destroy()
            
        except Exception as e:
            logger.error(f"Failed to use profile {profile_name}: {e}")
            self._show_temp_message(self, f"Failed to use profile: {e}", "red")
    
    def _cleanup_success_widgets(self, success_frame, auto_use_frame):
        """Clean up success message widgets"""
        try:
            if success_frame and success_frame.winfo_exists():
                success_frame.destroy()
        except:
            pass
        try:
            if auto_use_frame and auto_use_frame.winfo_exists():
                auto_use_frame.destroy()
        except:
            pass 