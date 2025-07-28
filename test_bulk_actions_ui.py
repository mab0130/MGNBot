
import customtkinter as ctk
from src.ui.bulk_actions import BulkTestLaunchDialog

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Test Bulk Actions UI")
        self.geometry("400x200")

        self.button = ctk.CTkButton(self, text="Open Dialog", command=self.open_dialog)
        self.button.pack(pady=20)

    def open_dialog(self):
        dialog = BulkTestLaunchDialog(
            self,
            server_count=5,
            on_confirm=lambda: print("Confirmed!"),
            aws_config=None  # Explicitly set to None
        )
        dialog.grab_set()

if __name__ == "__main__":
    app = App()
    app.mainloop()
