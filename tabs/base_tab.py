# tabs/base_tab.py
import tkinter
from tkinter import ttk, messagebox, filedialog # Add filedialog
import customtkinter as ctk
import csv # Add csv import
import os, sys, subprocess

class BaseAutomationTab(ctk.CTkFrame):
    """A base template for tabs that run automation tasks."""
    def __init__(self, parent, app_instance, automation_key: str):
        super().__init__(parent, fg_color="transparent")
        self.app = app_instance
        self.automation_key = automation_key

    def export_treeview_to_csv(self, treeview_widget: ttk.Treeview, default_filename: str):
        """Exports the contents of a ttk.Treeview to a CSV file."""
        if not treeview_widget.get_children():
            messagebox.showinfo("No Data", "There are no results to export.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialdir=self.app.get_user_downloads_path(),
            initialfile=default_filename,
            title="Save Results As"
        )
        
        if not file_path:
            return

        try:
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                headers = treeview_widget['columns']
                writer.writerow(headers)
                for item_id in treeview_widget.get_children():
                    row = treeview_widget.item(item_id)['values']
                    writer.writerow(row)
            
            if messagebox.askyesno("Export Successful", f"Results successfully exported to:\n{file_path}\n\nDo you want to open the file?"):
                if sys.platform == "win32":
                    os.startfile(file_path)
                elif sys.platform == "darwin":
                    subprocess.call(["open", file_path])
                else:
                    subprocess.call(["xdg-open", file_path])

        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export data to CSV.\n\nError: {e}")

    def _create_action_buttons(self, parent_frame) -> ctk.CTkFrame:
        action_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
        action_frame.grid_columnconfigure((0, 1, 2), weight=1)
        self.start_button = ctk.CTkButton(action_frame, text="▶ Start Automation", command=self.start_automation)
        self.stop_button = ctk.CTkButton(action_frame, text="Stop", command=lambda: self.app.stop_events[self.automation_key].set(), state="disabled", fg_color="gray50")
        self.reset_button = ctk.CTkButton(action_frame, text="Reset", fg_color="transparent", border_width=2, command=self.reset_ui, text_color=("gray10", "#DCE4EE"))
        self.start_button.grid(row=0, column=0, sticky="ew", padx=(0,5))
        self.stop_button.grid(row=0, column=1, sticky="ew", padx=5)
        self.reset_button.grid(row=0, column=2, sticky='ew', padx=(5,0))
        return action_frame

    def _create_log_and_status_area(self, parent_notebook) -> ctk.CTkFrame:
        log_frame = parent_notebook.add("Logs & Status")
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(2, weight=1)
        
        status_bar_frame = ctk.CTkFrame(log_frame, fg_color="transparent")
        status_bar_frame.grid(row=0, column=0, sticky='ew')
        status_bar_frame.grid_columnconfigure(0, weight=1)
        
        self.status_label = ctk.CTkLabel(status_bar_frame, text="Status: Ready")
        self.status_label.grid(row=0, column=0, sticky='ew', pady=(5,0))
        
        self.copy_logs_button = ctk.CTkButton(status_bar_frame, text="Copy Log", width=100, command=self.copy_logs_to_clipboard)
        self.copy_logs_button.grid(row=0, column=1, sticky='e', padx=5)
        
        self.progress_bar = ctk.CTkProgressBar(log_frame)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=1, column=0, sticky='ew', pady=(10, 5))
        
        self.log_display = ctk.CTkTextbox(log_frame, state="disabled", wrap=tkinter.WORD)
        self.log_display.grid(row=2, column=0, sticky='nsew', pady=(5, 0))

        return log_frame
    
    def copy_logs_to_clipboard(self):
        log_content = self.log_display.get('1.0', tkinter.END).strip()
        if log_content:
            self.app.clipboard_clear()
            self.app.clipboard_append(log_content)
            messagebox.showinfo("Copied", "Logs have been copied to the clipboard.")

    # --- MODIFIED: style_treeview ---
    def style_treeview(self, treeview_widget: ttk.Treeview):
        style = ttk.Style()
        style.theme_use("clam")
        
        current_appearance = ctk.get_appearance_mode().lower()
        theme_data = ctk.ThemeManager.theme
        
        bg_color = theme_data["CTkFrame"]["fg_color"][0] if current_appearance == "light" else theme_data["CTkFrame"]["fg_color"][1]
        text_color = theme_data["CTkLabel"]["text_color"][0] if current_appearance == "light" else theme_data["CTkLabel"]["text_color"][1]
        header_bg = theme_data["CTkButton"]["fg_color"][0] if current_appearance == "light" else theme_data["CTkButton"]["fg_color"][1]
        selected_color = theme_data["CTkButton"]["hover_color"][0] if current_appearance == "light" else theme_data["CTkButton"]["hover_color"][1]
        
        style.configure("Treeview", background=bg_color, foreground=text_color, fieldbackground=bg_color, borderwidth=0)
        style.map('Treeview', background=[('selected', selected_color)])
        style.configure("Treeview.Heading", background=header_bg, foreground=text_color, relief="flat")
        style.map("Treeview.Heading", background=[('active', selected_color)])

    def set_common_ui_state(self, running: bool):
        state = "disabled" if running else "normal"
        self.start_button.configure(state=state)
        self.reset_button.configure(state=state)
        self.stop_button.configure(state="normal" if running else "disabled")
        if hasattr(self, 'copy_logs_button'):
            self.copy_logs_button.configure(state=state)
        if hasattr(self, 'export_pdf_button'):
            self.export_pdf_button.configure(state=state)
        if hasattr(self, 'export_csv_button'):
            self.export_csv_button.configure(state=state)

        if running:
            self.progress_bar.configure(mode="indeterminate"); self.progress_bar.start()
        else:
            self.progress_bar.stop(); self.progress_bar.configure(mode="determinate"); self.progress_bar.set(0)

    def update_status(self, text: str, progress: float = None):
        self.status_label.configure(text=f"Status: {text}")
        if progress is not None:
            self.progress_bar.configure(mode="determinate"); self.progress_bar.set(progress)

    def start_automation(self):
        raise NotImplementedError("Child classes must implement the start_automation method.")

    def reset_ui(self):
        raise NotImplementedError("Child classes must implement the reset_ui method.")