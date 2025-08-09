# tabs/file_management_tab.py
import tkinter
from tkinter import ttk, messagebox, filedialog, simpledialog
import customtkinter as ctk
import requests
import os
import threading
from datetime import datetime
import humanize  # You will need to add this library: pip install humanize
from pathlib import Path

import config

class FileManagementTab(ctk.CTkFrame):
    """A tab for users to upload, download, and manage their cloud files and folders."""
    def __init__(self, parent, app_instance):
        super().__init__(parent, fg_color="transparent")
        self.app = app_instance
        self.current_folder_id = None
        self.current_path_breadcrumbs = []
        self.item_map = {} # To store full item details by ID

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1) # Adjusted for breadcrumbs

        self._create_widgets()
        self.refresh_files()

    def _create_widgets(self):
        # --- Header with Title and Storage Info ---
        header_frame = ctk.CTkFrame(self)
        header_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(header_frame, text="Cloud File Manager", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, padx=15, pady=10, sticky="w")
        
        storage_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        storage_frame.grid(row=0, column=1, padx=15, pady=10, sticky="e")
        self.storage_label = ctk.CTkLabel(storage_frame, text="Storage: Calculating...")
        self.storage_label.pack(anchor="e")
        self.storage_progress = ctk.CTkProgressBar(storage_frame, width=150)
        self.storage_progress.set(0)
        self.storage_progress.pack(anchor="e", pady=(5,0))

        # --- Breadcrumb and Controls Frame ---
        nav_frame = ctk.CTkFrame(self)
        nav_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")
        nav_frame.grid_columnconfigure(1, weight=1)

        # Action Buttons
        controls_frame = ctk.CTkFrame(nav_frame, fg_color="transparent")
        controls_frame.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        self.upload_file_button = ctk.CTkButton(controls_frame, text="Upload File(s)", width=120, command=self.upload_files)
        self.upload_file_button.pack(side="left", padx=(0, 5))
        
        self.upload_folder_button = ctk.CTkButton(controls_frame, text="Upload Folder", width=120, command=self.upload_folder)
        self.upload_folder_button.pack(side="left", padx=5)

        self.new_folder_button = ctk.CTkButton(controls_frame, text="New Folder", width=110, command=self.create_new_folder)
        self.new_folder_button.pack(side="left", padx=5)

        self.refresh_button = ctk.CTkButton(controls_frame, text="Refresh", width=90, command=lambda: self.refresh_files(self.current_folder_id))
        self.refresh_button.pack(side="left", padx=5)
        
        # Breadcrumbs
        self.breadcrumb_frame = ctk.CTkFrame(nav_frame, fg_color="transparent")
        self.breadcrumb_frame.grid(row=0, column=1, padx=10, pady=5, sticky="e")

        # --- Treeview for file list ---
        main_frame = ctk.CTkFrame(self)
        main_frame.grid(row=2, column=0, padx=10, pady=0, sticky="nsew")
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)

        cols = ("Name", "Size", "Date Modified")
        self.files_tree = ttk.Treeview(main_frame, columns=cols, show='headings')
        for col in cols: self.files_tree.heading(col, text=col)
        self.files_tree.column("Name", width=400, anchor="w")
        self.files_tree.column("Size", width=100, anchor="e")
        self.files_tree.column("Date Modified", width=150, anchor="center")
        self.files_tree.grid(row=0, column=0, sticky='nsew')
        
        scrollbar = ctk.CTkScrollbar(main_frame, command=self.files_tree.yview)
        self.files_tree.configure(yscroll=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky='ns')
        
        self.style_treeview(self.files_tree)
        self.files_tree.bind("<<TreeviewSelect>>", self.on_item_select)
        self.files_tree.bind("<Double-1>", self.on_item_double_click)

        # --- Action buttons for selected items ---
        action_bar = ctk.CTkFrame(self, fg_color="transparent")
        action_bar.grid(row=3, column=0, padx=10, pady=10, sticky="ew")
        self.download_button = ctk.CTkButton(action_bar, text="Download", command=self.download_selected_item, state="disabled")
        self.download_button.pack(side="left", padx=(0, 5))
        self.delete_button = ctk.CTkButton(action_bar, text="Delete", command=self.delete_selected_item, state="disabled", fg_color="#D32F2F", hover_color="#B71C1C")
        self.delete_button.pack(side="left", padx=5)

        # --- Progress bar for multi-file operations ---
        self.op_progress_label = ctk.CTkLabel(self, text="", text_color="gray50")
        self.op_progress_label.grid(row=4, column=0, padx=10, pady=(0,5), sticky="w")
        self.op_progress = ctk.CTkProgressBar(self)
        self.op_progress.grid(row=5, column=0, padx=10, pady=(0, 10), sticky="ew")
        self.op_progress.set(0)
        self.op_progress.grid_remove() # Hide initially
        self.op_progress_label.grid_remove()

    def style_treeview(self, treeview_widget: ttk.Treeview):
        # (Same as your existing style_treeview method)
        style = ttk.Style()
        bg_color = self.app._apply_appearance_mode(ctk.ThemeManager.theme["CTkFrame"]["fg_color"])
        text_color = self.app._apply_appearance_mode(ctk.ThemeManager.theme["CTkLabel"]["text_color"])
        header_bg = self.app._apply_appearance_mode(ctk.ThemeManager.theme["CTkButton"]["fg_color"])
        selected_color = self.app._apply_appearance_mode(ctk.ThemeManager.theme["CTkButton"]["hover_color"])
        style.theme_use("clam")
        style.configure("Treeview", background=bg_color, foreground=text_color, fieldbackground=bg_color, borderwidth=0, rowheight=25)
        style.map('Treeview', background=[('selected', selected_color)])
        style.configure("Treeview.Heading", background=header_bg, foreground=text_color, relief="flat", font=('sans-serif', 10, 'bold'))
        style.map("Treeview.Heading", background=[('active', selected_color)])

    def on_item_select(self, event=None):
        is_selected = bool(self.files_tree.selection())
        state = "normal" if is_selected else "disabled"
        self.download_button.configure(state=state)
        self.delete_button.configure(state=state)

    def on_item_double_click(self, event=None):
        selected_iid = self.files_tree.focus()
        if not selected_iid: return
        
        item_data = self.item_map.get(int(selected_iid))
        if item_data and item_data['is_folder']:
            self.refresh_files(folder_id=item_data['id'])

    def get_auth_headers(self):
        if not self.app.license_info.get('key'):
            messagebox.showerror("Authentication Error", "No active license key found.")
            return None
        return {'Authorization': f"Bearer {self.app.license_info['key']}"}

    def refresh_files(self, folder_id=None):
        self.files_tree.delete(*self.files_tree.get_children())
        self.on_item_select()
        
        headers = self.get_auth_headers()
        if not headers: return

        self.current_folder_id = folder_id
        url = f"{config.LICENSE_SERVER_URL}/files/api/list"
        if folder_id:
            url += f"/{folder_id}"

        def _fetch():
            try:
                response = requests.get(url, headers=headers, timeout=15)
                if response.status_code == 200:
                    data = response.json()
                    self.app.after(0, self.update_ui_with_data, data)
                else:
                    reason = response.json().get('reason', 'Unknown error')
                    self.app.after(0, messagebox.showerror, "Error", f"Failed to fetch file list: {reason}")
            except requests.exceptions.RequestException as e:
                self.app.after(0, messagebox.showerror, "Connection Error", f"Could not connect to the server: {e}")
        
        threading.Thread(target=_fetch, daemon=True).start()

    def update_ui_with_data(self, data):
        self.update_file_list(data.get('files', []))
        self.update_storage_info(data.get('total_usage', 0), data.get('storage_limit', 1))
        self.update_breadcrumbs(data.get('path', []))

    def update_file_list(self, files):
        self.files_tree.delete(*self.files_tree.get_children())
        self.item_map.clear()
        for item in files:
            self.item_map[item['id']] = item
            try:
                date_obj = datetime.fromisoformat(item['uploaded_at'].replace('Z', '+00:00'))
                formatted_date = date_obj.strftime('%Y-%m-%d %I:%M %p')
            except (ValueError, TypeError):
                formatted_date = item['uploaded_at']
            
            icon = "📁" if item['is_folder'] else "📄"
            name = f"{icon} {item['filename']}"
            size = humanize.naturalsize(item['filesize']) if not item['is_folder'] else "—"

            self.files_tree.insert("", "end", iid=item['id'], values=(name, size, formatted_date))

    def update_storage_info(self, total_usage, storage_limit):
        try:
            numeric_usage = int(total_usage)
            numeric_limit = int(storage_limit) if storage_limit else 1
            usage_percent = numeric_usage / numeric_limit
            self.storage_label.configure(text=f"Storage: {humanize.naturalsize(numeric_usage)} / {humanize.naturalsize(numeric_limit)}")
            self.storage_progress.set(usage_percent)
        except (ValueError, TypeError):
            self.storage_label.configure(text="Storage: Error")
            self.storage_progress.set(0)

    def update_breadcrumbs(self, path):
        for widget in self.breadcrumb_frame.winfo_children():
            widget.destroy()
        
        home_btn = ctk.CTkButton(self.breadcrumb_frame, text="Home", command=lambda: self.refresh_files(None), width=50)
        home_btn.pack(side="left")
        
        self.current_path_breadcrumbs = path
        for folder in path:
            ctk.CTkLabel(self.breadcrumb_frame, text="/").pack(side="left", padx=2)
            btn = ctk.CTkButton(self.breadcrumb_frame, text=folder['filename'], command=lambda f_id=folder['id']: self.refresh_files(f_id))
            btn.pack(side="left")

    def upload_files(self):
        filepaths = filedialog.askopenfilenames(title="Select File(s) to Upload")
        if not filepaths: return
        self._start_upload_session(filepaths, is_folder=False)

    def upload_folder(self):
        folder_path = filedialog.askdirectory(title="Select Folder to Upload")
        if not folder_path: return
        
        files_to_upload = []
        base_folder_name = os.path.basename(folder_path)
        for root, _, files in os.walk(folder_path):
            for filename in files:
                local_path = os.path.join(root, filename)
                # Create a relative path for the server
                relative_path = os.path.join(base_folder_name, os.path.relpath(local_path, folder_path))
                files_to_upload.append({'local_path': local_path, 'relative_path': str(Path(relative_path))})
        
        if not files_to_upload:
            messagebox.showinfo("Empty Folder", "The selected folder is empty.")
            return
        
        self._start_upload_session(files_to_upload, is_folder=True)

    def _start_upload_session(self, items, is_folder):
        headers = self.get_auth_headers()
        if not headers: return
        
        self.op_progress.grid()
        self.op_progress_label.grid()
        self.op_progress.set(0)
        
        def _upload_worker():
            total_items = len(items)
            for i, item in enumerate(items):
                if is_folder:
                    local_path = item['local_path']
                    relative_path = item['relative_path']
                else:
                    local_path = item
                    relative_path = ''
                
                filename = os.path.basename(local_path)
                self.app.after(0, self.op_progress_label.configure, {"text": f"Uploading ({i+1}/{total_items}): {filename}"})
                
                success = self._perform_upload(local_path, relative_path, headers)
                if not success:
                    # Ask user if they want to continue on failure
                    if not messagebox.askyesno("Upload Failed", f"Failed to upload {filename}. Continue with remaining files?"):
                        break
                
                self.app.after(0, self.op_progress.set, (i + 1) / total_items)

            self.app.after(0, self.op_progress.grid_remove)
            self.app.after(0, self.op_progress_label.grid_remove)
            self.app.after(100, self.refresh_files, self.current_folder_id)

        threading.Thread(target=_upload_worker, daemon=True).start()

    def _perform_upload(self, filepath, relative_path, headers):
        try:
            with open(filepath, 'rb') as f:
                files = {'file': (os.path.basename(filepath), f)}
                data = {'parent_id': self.current_folder_id or '', 'relative_path': relative_path}
                response = requests.post(f"{config.LICENSE_SERVER_URL}/files/api/upload", headers=headers, files=files, data=data, timeout=300)
            return response.status_code == 201
        except requests.exceptions.RequestException:
            return False
        except Exception:
            return False

    def create_new_folder(self):
        folder_name = simpledialog.askstring("New Folder", "Enter a name for the new folder:", parent=self)
        if not folder_name or not folder_name.strip():
            return

        headers = self.get_auth_headers()
        if not headers: return
        
        data = {'folder_name': folder_name.strip(), 'parent_id': self.current_folder_id or ''}

        def _create():
            try:
                # Note: This requires a new API endpoint. Assuming it's `/api/create-folder`
                response = requests.post(f"{config.LICENSE_SERVER_URL}/files/api/create-folder", headers=headers, json=data, timeout=30)
                if response.status_code == 201:
                    self.app.after(0, self.refresh_files, self.current_folder_id)
                else:
                    self.app.after(0, messagebox.showerror, "Creation Failed", response.json().get('reason', 'Server error'))
            except requests.exceptions.RequestException as e:
                self.app.after(0, messagebox.showerror, "Connection Error", str(e))
        
        threading.Thread(target=_create, daemon=True).start()

    def download_selected_item(self):
        selected_iid = self.files_tree.selection()
        if not selected_iid: return
        
        item_data = self.item_map.get(int(selected_iid[0]))
        if not item_data: return

        if item_data['is_folder']:
            self.download_folder(item_data)
        else:
            self.download_file(item_data)

    def download_file(self, item_data):
        save_path = filedialog.asksaveasfilename(initialfile=item_data['filename'], title="Save File As")
        if not save_path: return

        headers = self.get_auth_headers()
        if not headers: return
        
        self.op_progress.grid()
        self.op_progress_label.grid()
        self.op_progress_label.configure(text=f"Downloading: {item_data['filename']}")
        self.op_progress.configure(mode="indeterminate")
        self.op_progress.start()

        def _download():
            try:
                with requests.get(f"{config.LICENSE_SERVER_URL}/files/api/download/{item_data['id']}", headers=headers, stream=True, timeout=300) as r:
                    r.raise_for_status()
                    with open(save_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
                self.app.after(0, messagebox.showinfo, "Download Complete", f"Successfully downloaded '{item_data['filename']}'")
            except requests.exceptions.RequestException as e:
                self.app.after(0, messagebox.showerror, "Download Failed", str(e))
            finally:
                self.app.after(0, self.op_progress.stop)
                self.app.after(0, self.op_progress.grid_remove)
                self.app.after(0, self.op_progress_label.grid_remove)

        threading.Thread(target=_download, daemon=True).start()

    def download_folder(self, folder_data):
        save_location = filedialog.askdirectory(title=f"Select where to save the '{folder_data['filename']}' folder")
        if not save_location: return
        
        headers = self.get_auth_headers()
        if not headers: return

        self.op_progress.grid()
        self.op_progress_label.grid()

        def _download_worker():
            files_to_download = []
            
            # Recursively get file list
            def get_all_files(folder_id, current_path):
                url = f"{config.LICENSE_SERVER_URL}/files/api/list/{folder_id}"
                try:
                    response = requests.get(url, headers=headers, timeout=15)
                    response.raise_for_status()
                    items = response.json().get('files', [])
                    for item in items:
                        new_path = os.path.join(current_path, item['filename'])
                        if item['is_folder']:
                            get_all_files(item['id'], new_path)
                        else:
                            files_to_download.append({'id': item['id'], 'path': new_path})
                except requests.exceptions.RequestException:
                    self.app.after(0, messagebox.showerror, "Error", "Could not fetch folder contents.")
                    return

            get_all_files(folder_data['id'], folder_data['filename'])
            
            total_files = len(files_to_download)
            if total_files == 0:
                os.makedirs(os.path.join(save_location, folder_data['filename']), exist_ok=True)
                self.app.after(0, messagebox.showinfo, "Complete", "Downloaded empty folder structure.")
                return

            for i, file_info in enumerate(files_to_download):
                self.app.after(0, self.op_progress_label.configure, {"text": f"Downloading ({i+1}/{total_files}): {os.path.basename(file_info['path'])}"})
                
                local_path = os.path.join(save_location, file_info['path'])
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                
                try:
                    with requests.get(f"{config.LICENSE_SERVER_URL}/files/api/download/{file_info['id']}", headers=headers, stream=True, timeout=300) as r:
                        r.raise_for_status()
                        with open(local_path, 'wb') as f:
                            for chunk in r.iter_content(chunk_size=8192): f.write(chunk)
                except requests.exceptions.RequestException:
                    if not messagebox.askyesno("Download Failed", f"Failed to download {os.path.basename(file_info['path'])}. Continue?"):
                        break
                
                self.app.after(0, self.op_progress.set, (i + 1) / total_files)

            self.app.after(0, messagebox.showinfo, "Download Complete", f"Finished downloading folder '{folder_data['filename']}'.")
            self.app.after(0, self.op_progress.grid_remove)
            self.app.after(0, self.op_progress_label.grid_remove)

        threading.Thread(target=_download_worker, daemon=True).start()

    def delete_selected_item(self):
        selected_iid = self.files_tree.selection()
        if not selected_iid: return

        item_data = self.item_map.get(int(selected_iid[0]))
        if not item_data: return

        if not messagebox.askyesno("Confirm Deletion", f"Are you sure you want to permanently delete '{item_data['filename']}'? This cannot be undone."):
            return

        headers = self.get_auth_headers()
        if not headers: return

        def _delete():
            try:
                response = requests.delete(f"{config.LICENSE_SERVER_URL}/files/api/delete/{item_data['id']}", headers=headers, timeout=30)
                if response.status_code == 200:
                    self.app.after(0, self.refresh_files, self.current_folder_id)
                else:
                    self.app.after(0, messagebox.showerror, "Deletion Failed", response.json().get('reason', 'Server error'))
            except requests.exceptions.RequestException as e:
                self.app.after(0, messagebox.showerror, "Deletion Failed", str(e))
        
        threading.Thread(target=_delete, daemon=True).start()
