# tabs/base_tab.py
import tkinter
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
import os, sys, subprocess, csv, platform, re
from datetime import datetime
from fpdf import FPDF

class BaseAutomationTab(ctk.CTkFrame):
    def __init__(self, parent, app_instance, automation_key):
        super().__init__(parent, fg_color="transparent")
        self.app = app_instance
        self.automation_key = automation_key

    def _get_wkhtml_path(self):
        """Gets the correct path to the wkhtmltoimage executable based on the OS."""
        os_type = platform.system()
    
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS
            if os_type == "Windows":
                return os.path.join(base_path, 'wkhtmltoimage.exe')
            elif os_type == "Darwin":
                return os.path.join(base_path, 'wkhtmltoimage')
        else:
            base_path = os.path.abspath(".")
            if os_type == "Windows":
                return os.path.join(base_path, 'bin', 'win', 'wkhtmltoimage.exe')
            elif os_type == "Darwin":
                return os.path.join(base_path, 'bin', 'mac', 'wkhtmltoimage')
                
        return 'wkhtmltoimage'
        
    def generate_report_image(self, data, headers, title, date_str, footer, output_path):
        """Shows a 'Coming Soon' message instead of generating an image."""
        messagebox.showinfo(
            "Feature in Development",
            "Image export is being optimized to reduce application size and will be available in a future update.",
            parent=self.app
        )
        return False

    def generate_report_pdf(self, data, headers, col_widths, title, date_str, file_path):
        try:
            pdf = FPDF(orientation='L', unit='mm', format='A4')
            pdf.add_page()
            try:
                font_path = self.app.resource_path("assets/fonts/DejaVuSans.ttf")
                pdf.add_font('DejaVu', '', font_path, uni=True)
                pdf.set_font('DejaVu', '', 14)
            except Exception as e:
                print(f"Custom font not found, falling back to Arial: {e}")
                pdf.set_font("Arial", 'B', 16)
            
            pdf.cell(0, 10, title, 0, 1, 'C')
            pdf.set_font('DejaVu' if 'font_path' in locals() else 'Arial', '', 10)
            pdf.cell(0, 5, date_str, 0, 1, 'C')
            pdf.ln(10)

            pdf.set_font('DejaVu' if 'font_path' in locals() else 'Arial', 'B', 8)
            pdf.set_fill_color(240, 240, 240)
            
            for i, header in enumerate(headers):
                pdf.cell(col_widths[i], 8, str(header), 1, 0, 'C', 1)
            pdf.ln()

            pdf.set_font('DejaVu' if 'font_path' in locals() else 'Arial', '', 7)
            for row in data:
                # Determine max number of lines in the row to calculate row height
                max_lines = 1
                for i, item in enumerate(row):
                    # Use the correct width for split_only calculation
                    lines = len(pdf.multi_cell(col_widths[i], 6, str(item), split_only=True))
                    if lines > max_lines:
                        max_lines = lines
                
                cell_height = 6 * max_lines

                # Check for page break BEFORE drawing the row
                if pdf.get_y() + cell_height > pdf.page_break_trigger:
                    pdf.add_page()
                    # Redraw headers on new page
                    pdf.set_font('DejaVu' if 'font_path' in locals() else 'Arial', 'B', 8)
                    pdf.set_fill_color(240, 240, 240)
                    for i, header in enumerate(headers):
                        pdf.cell(col_widths[i], 8, str(header), 1, 0, 'C', 1)
                    pdf.ln()
                    pdf.set_font('DejaVu' if 'font_path' in locals() else 'Arial', '', 7)

                # Get starting position of the row
                y_pos = pdf.get_y()
                x_pos = pdf.get_x()

                # Draw each cell of the row explicitly, managing x/y positions manually
                for i, item in enumerate(row):
                    current_x = x_pos + sum(col_widths[:i])
                    pdf.set_xy(current_x, y_pos)
                    pdf.multi_cell(col_widths[i], 6, str(item), border=1, align='L')
                
                # Move cursor to the start of the next line, below the row we just drew
                pdf.set_xy(pdf.l_margin, y_pos + cell_height)

            pdf.output(file_path)
            return True
        except Exception as e:
            messagebox.showerror("PDF Export Failed", f"Could not generate PDF report:\n{e}", parent=self)
            return False


    def _create_action_buttons(self, parent_frame):
        action_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
        
        self.start_button = ctk.CTkButton(action_frame, text="Start Automation", command=self.start_automation, width=150)
        self.start_button.pack(side="left", padx=5)

        self.stop_button = ctk.CTkButton(action_frame, text="Stop Automation", command=self.stop_automation, state="disabled", fg_color="red", hover_color="#C70000")
        self.stop_button.pack(side="left", padx=5)
        
        self.reset_button = ctk.CTkButton(action_frame, text="Reset Form", command=self.reset_ui, fg_color="gray", hover_color="gray50")
        self.reset_button.pack(side="left", padx=5)

        return action_frame

    def _create_log_and_status_area(self, parent_notebook):
        log_frame = parent_notebook.add("Logs & Status")
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(1, weight=1)

        log_actions_frame = ctk.CTkFrame(log_frame, fg_color="transparent")
        log_actions_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=(5, 0))

        def copy_logs_to_clipboard():
            logs = self.log_display.get("1.0", tkinter.END)
            if logs.strip():
                self.app.clipboard_clear(); self.app.clipboard_append(logs)
                messagebox.showinfo("Copied", "Logs copied to clipboard.", parent=self.app)
            else:
                messagebox.showwarning("Empty", "There are no logs to copy.", parent=self.app)

        copy_button = ctk.CTkButton(log_actions_frame, text="Copy Logs", width=100, command=copy_logs_to_clipboard)
        copy_button.pack(side="right")

        self.log_display = ctk.CTkTextbox(log_frame, state="disabled")
        self.log_display.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        
        status_bar_frame = ctk.CTkFrame(log_frame, height=30)
        status_bar_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=(0, 5))

        self.status_label = ctk.CTkLabel(status_bar_frame, text="Status: Ready", anchor="w")
        self.status_label.pack(side="left", padx=10)
        
        self.progress_bar = ctk.CTkProgressBar(status_bar_frame, mode="determinate")
        self.progress_bar.set(0)
        self.progress_bar.pack(side="right", padx=10, fill="x", expand=True)
    
    def set_common_ui_state(self, running: bool):
        self.start_button.configure(state="disabled" if running else "normal")
        self.stop_button.configure(state="normal" if running else "disabled")
        self.reset_button.configure(state="disabled" if running else "normal")

    def start_automation(self):
        raise NotImplementedError

    def stop_automation(self):
        self.app.stop_events[self.automation_key].set()
        self.app.log_message(self.log_display, "Stop signal sent. Finishing current task...", "warning")

    def reset_ui(self):
        raise NotImplementedError
        
    def update_status(self, message, progress=None):
        self.status_label.configure(text=f"Status: {message}")
        if progress is not None:
            self.progress_bar.set(float(progress))

    def style_treeview(self, tree):
        style = ttk.Style()
        bg_color = self._apply_appearance_mode(ctk.ThemeManager.theme["CTkFrame"]["fg_color"])
        text_color = self._apply_appearance_mode(ctk.ThemeManager.theme["CTkLabel"]["text_color"])
        heading_bg = self._apply_appearance_mode(ctk.ThemeManager.theme["CTkButton"]["fg_color"])
        
        style.theme_use("default")
        style.configure("Treeview", background=bg_color, foreground=text_color, fieldbackground=bg_color, borderwidth=0)
        style.map('Treeview', background=[('selected', ctk.ThemeManager.theme["CTkButton"]["fg_color"])])
        style.configure("Treeview.Heading", background=heading_bg, foreground=text_color, relief="flat", font=('Calibri', 10,'bold'))
        style.map("Treeview.Heading", background=[('active', ctk.ThemeManager.theme["CTkButton"]["hover_color"])])

        tree.tag_configure('failed', foreground='red')

    def _setup_treeview_sorting(self, tree):
        for col in tree["columns"]:
            tree.heading(col, text=col, command=lambda _col=col: self._treeview_sort_column(tree, _col, False))

    def _treeview_sort_column(self, tv, col, reverse):
        l = [(tv.set(k, col), k) for k in tv.get_children('')]
        try:
            l.sort(key=lambda t: float(t[0]), reverse=reverse)
        except ValueError:
            l.sort(reverse=reverse)
        for index, (val, k) in enumerate(l):
            tv.move(k, '', index)
        tv.heading(col, command=lambda: self._treeview_sort_column(tv, col, not reverse))
        
    def export_treeview_to_csv(self, tree, default_filename):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialdir=self.app.get_user_downloads_path(),
            initialfile=default_filename,
            title="Save CSV Report"
        )
        if not file_path: return
        
        try:
            # FIX: Changed encoding to 'utf-8-sig' to support Hindi/Unicode in Windows Excel
            with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(tree["columns"])
                for item_id in tree.get_children():
                    writer.writerow(tree.item(item_id)['values'])
            messagebox.showinfo("Success", f"Report successfully exported to\n{file_path}", parent=self)
        except Exception as e:
            messagebox.showerror("Export Failed", f"An error occurred while saving the CSV file:\n{e}", parent=self)

    # --- NEW: Add this reusable method to the base class ---
    def _extract_and_update_workcodes(self, textbox_widget):
        """
        Extracts work codes (6-digit) and wagelist IDs from the
        provided textbox widget, removes duplicates, and updates the widget.
        """
        try:
            input_content = textbox_widget.get("1.0", tkinter.END)
            if not input_content.strip():
                return

            # Pattern for full work codes (e.g., 3404003009/IF/123456)
            work_code_pattern = re.compile(r'\b(34\d{8}(?:/\w+)+/\d+)\b')
            # Pattern for wagelist IDs (e.g., 3422003WL031552)
            wagelist_pattern = re.compile(r'\b\d+WL\d+\b', re.IGNORECASE)

            found_work_codes = work_code_pattern.findall(input_content)
            found_wagelists = wagelist_pattern.findall(input_content)

            processed_work_codes = []
            for code in found_work_codes:
                last_part = code.split('/')[-1]
                if len(last_part) > 7:
                    # Extracts the last 6 digits from longer codes like /123456
                    processed_work_codes.append(last_part[-6:])
                else:
                    # Assumes the last part is the 6-digit code
                    processed_work_codes.append(last_part)
            
            # Combine results and make wagelists uppercase
            results = processed_work_codes + [wl.upper() for wl in found_wagelists]

            # Remove duplicates while preserving order
            final_results = list(dict.fromkeys(results))

            if final_results:
                textbox_widget.configure(state="normal")
                textbox_widget.delete("1.0", tkinter.END)
                textbox_widget.insert("1.0", "\n".join(final_results))
                messagebox.showinfo("Extraction Complete", f"Found and extracted {len(final_results)} unique codes.", parent=self)
            else:
                messagebox.showinfo("No Codes Found", "Could not find any matching work codes or wagelist IDs in the text.", parent=self)
        
        except Exception as e:
            messagebox.showerror("Extraction Error", f"An error occurred during extraction: {e}", parent=self)
