# tabs/reports_tab.py
import customtkinter as ctk

class ReportsTab(ctk.CTkFrame):
    def __init__(self, parent, app_instance):
        """
        Initializes the Reports Tab, which serves as a placeholder for a future feature.
        """
        super().__init__(parent, fg_color="transparent")
        self.app = app_instance

        # Configure the grid to expand and fill the available space
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Main container to center the content
        container = ctk.CTkFrame(self)
        container.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=1)
        
        # Main title label
        label = ctk.CTkLabel(
            container,
            text="🚀 Upcoming in the next update!",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=("gray20", "gray80")
        )
        label.pack(expand=True, padx=20, pady=20)

        # Subtitle label with more details
        sub_label = ctk.CTkLabel(
            container,
            text="This section will feature advanced reporting and data analysis tools.",
            font=ctk.CTkFont(size=14),
            text_color="gray50"
        )
        sub_label.pack(expand=True, padx=20, pady=(0, 20))
