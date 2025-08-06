# tabs/file_management_tab.py
import tkinter
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
import requests
import os
import threading
from datetime import datetime
import humanize  # You will need to add this library: pip install humanize

import config

class FileManagementTab(ctk.CTkFrame):
    """A tab for users to upload, download, and manage their personal files."""
    def __init__(self, parent, app_instance):
        super().__init__(parent, fg_color="transparent")
        self.app = app_instance

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._create_widgets()
        self.refresh_files()

    def _create_widgets(self):
        header_frame = ctk.CTkFrame(self)
        header_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(header_frame, text="File Manager", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, padx=15, pady=10, sticky="w")
        
        self.storage_label = ctk.CTkLabel(header_frame, text="Storage Used: Calculating...", text_color="gray50")
        self.storage_label.grid(row=0, column=1, padx=15, pady=10, sticky="e")
        
        self.storage_progress = ctk.CTkProgressBar(header_frame)
        self.storage_progress.set(0)
        self.storage_progress.grid(row=1, column=0, columnspan=2, padx=15, pady=(0, 10), sticky="ew")

        # File list and controls
        main_frame = ctk.CTkFrame(self)
        main_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)

        controls_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        controls_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.upload_button = ctk.CTkButton(controls_frame, text="Upload File(s)", command=self.upload_files)
        self.upload_button.pack(side="left", padx=(0, 5))
        
        self.download_button = ctk.CTkButton(controls_frame, text="Download", command=self.download_selected_file, state="disabled")
        self.download_button.pack(side="left", padx=5)

        self.delete_button = ctk.CTkButton(controls_frame, text="Delete", command=self.delete_selected_file, state="disabled", fg_color="#D32F2F", hover_color="#B71C1C")
        self.delete_button.pack(side="left", padx=5)

        self.refresh_button = ctk.CTkButton(controls_frame, text="Refresh", command=self.refresh_files)
        self.refresh_button.pack(side="right")

        # Treeview for file list
        tree_frame = ctk.CTkFrame(main_frame)
        tree_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)
        
        cols = ("Filename", "Size", "Upload Date")
        self.files_tree = ttk.Treeview(tree_frame, columns=cols, show='headings')
        for col in cols: self.files_tree.heading(col, text=col)
        self.files_tree.column("Filename", width=300)
        self.files_tree.column("Size", width=100, anchor="e")
        self.files_tree.column("Upload Date", width=150, anchor="center")
        self.files_tree.grid(row=0, column=0, sticky='nsew')
        
        scrollbar = ctk.CTkScrollbar(tree_frame, command=self.files_tree.yview)
        self.files_tree.configure(yscroll=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky='ns')
        
        self.style_treeview(self.files_tree)
        self.files_tree.bind("<<TreeviewSelect>>", self.on_file_select)

    def style_treeview(self, treeview_widget: ttk.Treeview):
        style = ttk.Style()
        bg_color = self.app._apply_appearance_mode(ctk.ThemeManager.theme["CTkFrame"]["fg_color"])
        text_color = self.app._apply_appearance_mode(ctk.ThemeManager.theme["CTkLabel"]["text_color"])
        header_bg = self.app._apply_appearance_mode(ctk.ThemeManager.theme["CTkButton"]["fg_color"])
        selected_color = self.app._apply_appearance_mode(ctk.ThemeManager.theme["CTkButton"]["hover_color"])
        style.theme_use("clam")
        style.configure("Treeview", background=bg_color, foreground=text_color, fieldbackground=bg_color, borderwidth=0)
        style.map('Treeview', background=[('selected', selected_color)])
        style.configure("Treeview.Heading", background=header_bg, foreground=text_color, relief="flat")
        style.map("Treeview.Heading", background=[('active', selected_color)])

    def on_file_select(self, event=None):
        selected_items = self.files_tree.selection()
        if selected_items:
            self.download_button.configure(state="normal")
            self.delete_button.configure(state="normal")
        else:
            self.download_button.configure(state="disabled")
            self.delete_button.configure(state="disabled")

    def get_auth_headers(self):
        """Returns the authentication headers required for API requests."""
        if not self.app.license_info.get('key'):
            messagebox.showerror("Authentication Error", "No active license key found. Cannot perform file operations.")
            return None
        return {'Authorization': f"Bearer {self.app.license_info['key']}"}

    def refresh_files(self):
        """Fetches the list of files from the server and updates the treeview."""
        self.files_tree.delete(*self.files_tree.get_children())
        self.on_file_select()
        
        headers = self.get_auth_headers()
        if not headers: return

        def _fetch():
            try:
                response = requests.get(f"{config.LICENSE_SERVER_URL}/api/files/list", headers=headers, timeout=15)
                if response.status_code == 200:
                    data = response.json()
                    files = data.get('files', [])
                    total_usage = data.get('total_usage', 0)
                    self.app.after(0, self.update_file_list, files)
                    self.app.after(0, self.update_storage_info, total_usage)
                else:
                    self.app.after(0, messagebox.showerror, "Error", f"Failed to fetch file list: {response.json().get('reason')}")
            except requests.exceptions.RequestException as e:
                self.app.after(0, messagebox.showerror, "Connection Error", f"Could not connect to the server: {e}")
        
        threading.Thread(target=_fetch, daemon=True).start()

    def update_file_list(self, files):
        self.files_tree.delete(*self.files_tree.get_children())
        for file_info in files:
            # --- FIX: Handle different date formats from the server ---
            try:
                # First, try to parse the expected ISO format
                date_obj = datetime.fromisoformat(file_info['uploaded_at'].replace('Z', '+00:00'))
            except ValueError:
                # Fallback for other common web formats like 'Wed, 06 Aug 2025 05:44:49 GMT'
                try:
                    date_obj = datetime.strptime(file_info['uploaded_at'], '%a, %d %b %Y %H:%M:%S %Z')
                except ValueError:
                    # If all else fails, display the raw string
                    formatted_date = file_info['uploaded_at']
            
            if 'date_obj' in locals():
                formatted_date = date_obj.strftime('%Y-%m-%d %I:%M %p')
            
            self.files_tree.insert("", "end", iid=file_info['id'], values=(
                file_info['filename'],
                humanize.naturalsize(file_info['filesize']),
                formatted_date
            ))

    def update_storage_info(self, total_usage):
        storage_limit = 500 * 1024 * 1024  # 500 MB
        # --- FIX: Ensure total_usage is an integer before division ---
        try:
            numeric_usage = int(total_usage)
            usage_percent = numeric_usage / storage_limit if storage_limit > 0 else 0
            self.storage_label.configure(text=f"Storage Used: {humanize.naturalsize(numeric_usage)} / 500 MB")
            self.storage_progress.set(usage_percent)
        except (ValueError, TypeError):
            self.storage_label.configure(text="Storage Used: Error")
            self.storage_progress.set(0)

    def upload_files(self):
        filepaths = filedialog.askopenfilenames(title="Select File(s) to Upload")
        if not filepaths: return

        headers = self.get_auth_headers()
        if not headers: return

        for path in filepaths:
            threading.Thread(target=self._perform_upload, args=(path, headers), daemon=True).start()

    def _perform_upload(self, filepath, headers):
        filename = os.path.basename(filepath)
        try:
            with open(filepath, 'rb') as f:
                files = {'file': (filename, f)}
                response = requests.post(f"{config.LICENSE_SERVER_URL}/api/files/upload", headers=headers, files=files, timeout=120)
            
            if response.status_code == 201:
                self.app.after(0, self.refresh_files)
            else:
                self.app.after(0, messagebox.showerror, f"Upload Failed: {filename}", response.json().get('reason', 'Unknown server error.'))

        except requests.exceptions.RequestException as e:
            self.app.after(0, messagebox.showerror, f"Upload Failed: {filename}", f"A connection error occurred: {e}")
        except Exception as e:
            self.app.after(0, messagebox.showerror, f"Upload Failed: {filename}", f"An unexpected error occurred: {e}")

    def download_selected_file(self):
        selected_item = self.files_tree.selection()
        if not selected_item: return
        
        file_id = selected_item[0]
        filename = self.files_tree.item(file_id, "values")[0]

        save_path = filedialog.asksaveasfilename(initialfile=filename, title="Save File As")
        if not save_path: return

        headers = self.get_auth_headers()
        if not headers: return

        def _download():
            try:
                with requests.get(f"{config.LICENSE_SERVER_URL}/api/files/download/{file_id}", headers=headers, stream=True, timeout=120) as r:
                    r.raise_for_status()
                    with open(save_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
                self.app.after(0, messagebox.showinfo, "Download Complete", f"Successfully downloaded '{filename}'")
            except requests.exceptions.RequestException as e:
                self.app.after(0, messagebox.showerror, "Download Failed", f"Failed to download file: {e}")

        threading.Thread(target=_download, daemon=True).start()

    def delete_selected_file(self):
        selected_item = self.files_tree.selection()
        if not selected_item: return

        file_id = selected_item[0]
        filename = self.files_tree.item(file_id, "values")[0]

        if not messagebox.askyesno("Confirm Deletion", f"Are you sure you want to permanently delete '{filename}'?"):
            return

        headers = self.get_auth_headers()
        if not headers: return

        def _delete():
            try:
                response = requests.delete(f"{config.LICENSE_SERVER_URL}/api/files/delete/{file_id}", headers=headers, timeout=30)
                if response.status_code == 200:
                    self.app.after(0, self.refresh_files)
                else:
                    self.app.after(0, messagebox.showerror, "Deletion Failed", response.json().get('reason', 'Unknown server error.'))
            except requests.exceptions.RequestException as e:
                self.app.after(0, messagebox.showerror, "Deletion Failed", f"A connection error occurred: {e}")
        
        threading.Thread(target=_delete, daemon=True).start()
