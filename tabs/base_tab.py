# tabs/base_tab.py
import tkinter
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
import os, sys, subprocess, csv, platform
from datetime import datetime
import imgkit
from fpdf import FPDF

class BaseAutomationTab(ctk.CTkFrame):
    def __init__(self, parent, app_instance, automation_key):
        super().__init__(parent, fg_color="transparent")
        self.app = app_instance
        self.automation_key = automation_key

    # --- FIX 1: Corrected wkhtmltoimage path for Windows ---
    def _get_wkhtml_path(self):
        """Gets the correct path to the wkhtmltoimage executable based on the OS."""
        os_type = platform.system()
    
        if hasattr(sys, '_MEIPASS'):
            # In a bundled app, the executable is at the root of the temp folder
            base_path = sys._MEIPASS
            if os_type == "Windows":
                return os.path.join(base_path, 'wkhtmltoimage.exe')
            elif os_type == "Darwin":  # macOS
                return os.path.join(base_path, 'wkhtmltoimage')
        else:
            # In a development environment, the base path is the project root.
            base_path = os.path.abspath(".")
            if os_type == "Windows":
                return os.path.join(base_path, 'bin', 'win', 'wkhtmltoimage.exe')
            elif os_type == "Darwin":
                return os.path.join(base_path, 'bin', 'mac', 'wkhtmltoimage')
                
        # Fallback for other systems (like Linux)
        return 'wkhtmltoimage'
    def generate_report_image(self, data, headers, title, date_str, footer, output_path):
        try:
            path_wkhtmltoimage = self._get_wkhtml_path()
            if not os.path.exists(path_wkhtmltoimage):
                messagebox.showerror("Error", f"wkhtmltoimage not found at {path_wkhtmltoimage}")
                return False

            config = imgkit.config(wkhtmltoimage=path_wkhtmltoimage)
            
            header_html = "".join(f"<th>{h}</th>" for h in headers)
            rows_html = "".join("<tr>" + "".join(f"<td>{item}</td>" for item in row) + "</tr>" for row in data)
            
            html_content = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 20px; }}
                    table {{ border-collapse: collapse; width: 100%; font-size: 12px; }}
                    th, td {{ border: 1px solid #dddddd; text-align: left; padding: 8px; }}
                    th {{ background-color: #f2f2f2; }}
                    .header {{ text-align: center; margin-bottom: 20px; }}
                    .header h1 {{ margin: 0; font-size: 20px; }}
                    .header p {{ margin: 5px 0; font-size: 12px; color: #555; }}
                    .footer {{ text-align: center; margin-top: 20px; font-size: 10px; color: #777; }}
                </style>
            </head>
            <body>
                <div class="header"><h1>{title}</h1><p>{date_str}</p></div>
                <table><thead><tr>{header_html}</tr></thead><tbody>{rows_html}</tbody></table>
                <div class="footer"><p>{footer}</p></div>
            </body>
            </html>
            """
            
            options = {'width': 800, 'quality': 100, 'enable-local-file-access': None}
            imgkit.from_string(html_content, output_path, config=config, options=options)
            return True
        except Exception as e:
            self.app.log_message(self.log_display, f"Failed to generate image report. Error: {e}", "error")
            messagebox.showerror("Image Export Failed", f"Could not generate image report:\n{e}")
            return False

    # --- FIX 2: Removed conditional colors for a clean PDF look ---
    def generate_report_pdf(self, data, headers, col_widths, title, date_str, file_path):
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            
            pdf.cell(0, 10, title, 0, 1, 'C')
            pdf.set_font("Arial", '', 10)
            pdf.cell(0, 5, date_str, 0, 1, 'C')
            pdf.ln(10)

            pdf.set_font("Arial", 'B', 8)
            pdf.set_fill_color(240, 240, 240)
            
            total_width = sum(col_widths)
            
            for i, header in enumerate(headers):
                width_percentage = col_widths[i] / total_width
                pdf.cell(pdf.w * width_percentage * 0.95, 8, header, 1, 0, 'C', 1)
            pdf.ln()

            pdf.set_font("Arial", '', 7)
            for row in data:
                # This block used to contain the logic for setting red/green colors.
                # It has been removed to make all text black by default.
                pdf.set_text_color(0, 0, 0) # Ensures text is always black

                for i, item in enumerate(row):
                    width_percentage = col_widths[i] / total_width
                    pdf.cell(pdf.w * width_percentage * 0.95, 6, str(item), 1, 0)
                pdf.ln()

            pdf.output(file_path)
            return True
        except Exception as e:
            messagebox.showerror("PDF Export Failed", f"Could not generate PDF report:\n{e}", parent=self)
            return False

    # --- Other existing methods in your base_tab.py ---

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
        log_frame.grid_rowconfigure(0, weight=1)

        self.log_display = ctk.CTkTextbox(log_frame, state="disabled")
        self.log_display.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        status_bar_frame = ctk.CTkFrame(log_frame, height=30)
        status_bar_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=(0, 5))

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
        # This should be implemented in the child class
        raise NotImplementedError

    def stop_automation(self):
        self.app.stop_events[self.automation_key].set()
        self.app.log_message(self.log_display, "Stop signal sent. Finishing current task...", "warning")

    def reset_ui(self):
        # This should be implemented in the child class
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
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(tree["columns"])
                for item_id in tree.get_children():
                    writer.writerow(tree.item(item_id)['values'])
            messagebox.showinfo("Success", f"Report successfully exported to\n{file_path}", parent=self)
        except Exception as e:
            messagebox.showerror("Export Failed", f"An error occurred while saving the CSV file:\n{e}", parent=self)
