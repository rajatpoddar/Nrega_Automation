# tabs/workcode_extractor_tab.py
import tkinter
import customtkinter as ctk
import re
import webbrowser

class WorkcodeExtractorTab(ctk.CTkFrame):
    def __init__(self, parent, app_instance):
        super().__init__(parent, fg_color="transparent")
        self.app = app_instance

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Main frame to hold input and output side-by-side
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        main_container.grid_columnconfigure((0, 1), weight=1)
        main_container.grid_rowconfigure(1, weight=1)

        # --- Input Frame (Left Side) ---
        input_frame = ctk.CTkFrame(main_container)
        input_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 5))
        input_frame.grid_columnconfigure(0, weight=1)
        input_frame.grid_rowconfigure(2, weight=1) # Make space for the new note

        ctk.CTkLabel(input_frame, text="Paste Text Below", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=15, pady=(10,0), sticky="w")

        # Instructional note and link
        note_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        note_frame.grid(row=1, column=0, sticky="w", padx=15, pady=(2, 8))
        
        ctk.CTkLabel(note_frame, text="Note: Go to the ").pack(side="left")
        
        link_label = ctk.CTkLabel(note_frame, text="MR Tracking Page", text_color=("#0000EE", "#ADD8E6"), cursor="hand2")
        link_label.pack(side="left")
        link_url = "https://nregastrep.nic.in/netnrega/dynamic_muster_track.aspx?lflag=eng&state_code=34&fin_year=2025-2026&state_name=JHARKHAND&Digest=FjAL4jfLQiHS1NU1KnbRZg"
        link_label.bind("<Button-1>", lambda e: webbrowser.open_new_tab(link_url))
        
        ctk.CTkLabel(note_frame, text=", copy the entire table, and paste it below.").pack(side="left")
        
        self.input_text = ctk.CTkTextbox(input_frame, wrap=tkinter.WORD)
        self.input_text.grid(row=2, column=0, sticky="nsew", padx=15, pady=(0, 15))

        # --- Output Frame (Right Side) ---
        output_frame = ctk.CTkFrame(main_container)
        output_frame.grid(row=1, column=1, sticky="nsew", padx=(5, 0))
        output_frame.grid_columnconfigure(0, weight=1)
        output_frame.grid_rowconfigure(1, weight=1)
        
        output_header_frame = ctk.CTkFrame(output_frame, fg_color="transparent")
        output_header_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=10)
        output_header_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(output_header_frame, text="Extracted Codes", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w")
        self.copy_button = ctk.CTkButton(output_header_frame, text="Copy", width=70, command=self._copy_results)
        self.copy_button.grid(row=0, column=2, sticky="e")

        self.output_text = ctk.CTkTextbox(output_frame, wrap=tkinter.NONE, state="disabled")
        self.output_text.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))
        
        # --- Action Buttons (Top) ---
        action_frame = ctk.CTkFrame(main_container)
        action_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        action_frame.grid_columnconfigure(1, weight=1) # Allow checkbox to center
        
        self.extract_button = ctk.CTkButton(action_frame, text="▶ Extract Codes", command=self._extract_codes)
        self.extract_button.grid(row=0, column=0, padx=15, pady=10)
        
        # --- ADDED: Checkbox to remove duplicates ---
        self.remove_duplicates_checkbox = ctk.CTkCheckBox(action_frame, text="Remove Duplicates (for eMB entry)")
        self.remove_duplicates_checkbox.grid(row=0, column=1, padx=10, pady=10, sticky="w")
        
        self.clear_button = ctk.CTkButton(action_frame, text="Clear All", command=self._clear_all, fg_color="transparent", border_width=2, text_color=("gray10", "#DCE4EE"))
        self.clear_button.grid(row=0, column=2, padx=15, pady=10)

    def _extract_codes(self):
        """Finds work codes in the input text and displays the processed results."""
        input_content = self.input_text.get("1.0", tkinter.END)
        if not input_content.strip():
            return

        work_code_pattern = re.compile(r'\b(34\d{8}(?:/\w+)+/\d+)\b')
        found_codes = work_code_pattern.findall(input_content)
        
        extracted_results = []
        for code in found_codes:
            last_part = code.split('/')[-1]
            if len(last_part) > 7:
                extracted_results.append(last_part[-6:])
            else:
                extracted_results.append(last_part)
        
        # --- MODIFIED: Handle duplicates based on checkbox state ---
        if self.remove_duplicates_checkbox.get():
            # If checkbox is checked, remove duplicates while preserving order
            final_results = list(dict.fromkeys(extracted_results))
        else:
            # Otherwise, keep all results including duplicates
            final_results = extracted_results
        
        # Display the results
        self.output_text.configure(state="normal")
        self.output_text.delete("1.0", tkinter.END)
        if final_results:
            self.output_text.insert("1.0", "\n".join(final_results))
        else:
            self.output_text.insert("1.0", "No matching work codes found.")
        self.output_text.configure(state="disabled")

    def _copy_results(self):
        """Copies the content of the output textbox to the clipboard."""
        results = self.output_text.get("1.0", tkinter.END).strip()
        if results and "No matching" not in results:
            self.app.clipboard_clear()
            self.app.clipboard_append(results)
            self.copy_button.configure(text="Copied!")
            self.app.after(2000, lambda: self.copy_button.configure(text="Copy"))

    def _clear_all(self):
        """Clears both the input and output textboxes."""
        self.input_text.delete("1.0", tkinter.END)
        self.output_text.configure(state="normal")
        self.output_text.delete("1.0", tkinter.END)
        self.output_text.configure(state="disabled")