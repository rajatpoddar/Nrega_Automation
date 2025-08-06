# tabs/feedback_tab.py
import tkinter
from tkinter import messagebox
import customtkinter as ctk
import requests
import config

class FeedbackTab(ctk.CTkFrame):
    """A tab for users to submit feedback, bug reports, or feature requests."""
    def __init__(self, parent, app_instance):
        super().__init__(parent, fg_color="transparent")
        self.app = app_instance

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.main_frame, text="Submit Feedback", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        ctk.CTkLabel(self.main_frame, text="We value your input! Let us know how we can improve.", text_color="gray50").grid(row=1, column=0, padx=20, pady=(0, 20), sticky="w")

        ctk.CTkLabel(self.main_frame, text="Your Name:").grid(row=2, column=0, padx=20, pady=(10, 2), sticky="w")
        self.name_entry = ctk.CTkEntry(self.main_frame, placeholder_text="Enter your name")
        self.name_entry.grid(row=3, column=0, padx=20, pady=(0, 10), sticky="ew")

        ctk.CTkLabel(self.main_frame, text="Your Email (Optional):").grid(row=4, column=0, padx=20, pady=(10, 2), sticky="w")
        self.email_entry = ctk.CTkEntry(self.main_frame, placeholder_text="Enter your email for follow-up")
        self.email_entry.grid(row=5, column=0, padx=20, pady=(0, 10), sticky="ew")

        ctk.CTkLabel(self.main_frame, text="Feedback Type:").grid(row=6, column=0, padx=20, pady=(10, 2), sticky="w")
        self.feedback_type_var = ctk.StringVar(value="General Feedback")
        self.feedback_type_menu = ctk.CTkOptionMenu(self.main_frame, variable=self.feedback_type_var, values=["General Feedback", "Bug Report", "Feature Request"])
        self.feedback_type_menu.grid(row=7, column=0, padx=20, pady=(0, 10), sticky="ew")

        ctk.CTkLabel(self.main_frame, text="Message:").grid(row=8, column=0, padx=20, pady=(10, 2), sticky="w")
        self.message_textbox = ctk.CTkTextbox(self.main_frame, height=150)
        self.message_textbox.grid(row=9, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.main_frame.grid_rowconfigure(9, weight=1)

        self.submit_button = ctk.CTkButton(self.main_frame, text="Submit Feedback", command=self.submit_feedback)
        self.submit_button.grid(row=10, column=0, padx=20, pady=(0, 20), ipady=5)
        
        # Pre-fill user info if available
        self.load_user_info()

    def load_user_info(self):
        """Pre-fills the name and email from the license information if available."""
        if self.app.license_info:
            name = self.app.license_info.get('user_name')
            email = self.app.license_info.get('user_email')
            if name:
                self.name_entry.insert(0, name)
            if email:
                self.email_entry.insert(0, email)

    def submit_feedback(self):
        """Gathers the form data and sends it to the server."""
        name = self.name_entry.get().strip()
        email = self.email_entry.get().strip()
        feedback_type = self.feedback_type_var.get()
        message = self.message_textbox.get("1.0", "end").strip()

        if not name or not message:
            messagebox.showwarning("Input Required", "Please enter your name and a message.")
            return

        feedback_data = {
            "name": name,
            "email": email,
            "feedback_type": feedback_type,
            "message": message,
            "app_version": config.APP_VERSION,
            "license_key": self.app.license_info.get('key', 'N/A'),
            "machine_id": self.app.machine_id
        }

        self.submit_button.configure(state="disabled", text="Submitting...")
        try:
            response = requests.post(f"{config.LICENSE_SERVER_URL}/api/feedback", json=feedback_data, timeout=15)
            if response.status_code == 201:
                messagebox.showinfo("Feedback Submitted", "Thank you! Your feedback has been received.")
                self.message_textbox.delete("1.0", "end")
            else:
                messagebox.showerror("Submission Failed", f"Could not submit feedback. Server responded with: {response.json().get('reason', 'Unknown error')}")
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Connection Error", f"Could not connect to the server. Please check your internet connection and try again.\n\nError: {e}")
        finally:
            self.submit_button.configure(state="normal", text="Submit Feedback")

