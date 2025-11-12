# tabs/autocomplete_widget.py
import customtkinter as ctk

class AutocompleteEntry(ctk.CTkEntry):
    def __init__(self, parent, suggestions_list=None, app_instance=None, history_key=None, **kwargs):
        super().__init__(parent, **kwargs)

        self.suggestions = suggestions_list if suggestions_list is not None else []
        self.app = app_instance
        self.history_key = history_key
        
        self._suggestion_toplevel = None
        self._suggestion_listbox = None
        
        self._focus_out_after_id = None
        self._debounce_after_id = None
        
        self._active_suggestion_index = -1
        self._suggestion_labels = []
        self._suggestion_frames = [] 

        self._create_suggestion_toplevel() # --- NEW: Create toplevel once ---

        self.bind("<KeyRelease>", self._on_key_release_debounce)
        self.bind("<FocusOut>", self._on_focus_out)
        self.bind("<Down>", self._on_arrow_down)
        self.bind("<Up>", self._on_arrow_up)
        self.bind("<Return>", self._on_enter)
        self.bind("<Escape>", lambda e: self._hide_suggestions()) # --- NEW: Hide on Escape ---

    def _create_suggestion_toplevel(self):
        """Creates the suggestion toplevel window one time and hides it."""
        if self._suggestion_toplevel:
            return

        self._suggestion_toplevel = ctk.CTkToplevel(self)
        self._suggestion_toplevel.wm_overrideredirect(True)
        self._suggestion_toplevel.attributes("-topmost", True)
        
        self._suggestion_listbox = ctk.CTkFrame(self._suggestion_toplevel, fg_color=("gray90", "gray20"))
        self._suggestion_listbox.pack(expand=True, fill="both")
        
        self._suggestion_toplevel.withdraw() # Hide it initially

    def _on_key_release_debounce(self, event):
        """Debounces the key release event to avoid flickering."""
        # Stop if the user is just navigating
        if event.keysym in ("Up", "Down", "Return", "Enter", "Escape"):
            return

        # Stop for non-character keys
        if event.keysym in ("BackSpace", "Left", "Right", "Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R", "Tab"):
             # Allow BackSpace to trigger an immediate update if desired, or debounce it
             pass # Debouncing BackSpace too for consistency

        # Cancel any pending search
        if self._debounce_after_id:
            self.after_cancel(self._debounce_after_id)
            self._debounce_after_id = None

        # Schedule a new search after 300ms
        self._debounce_after_id = self.after(300, self._perform_search)

    def _perform_search(self):
        """Performs the actual search and shows suggestions."""
        self._debounce_after_id = None
        current_text = self.get().lower()

        if current_text:
            matching_suggestions = [s for s in self.suggestions if current_text in s.lower()]
            if matching_suggestions:
                self._show_suggestions(matching_suggestions)
            else:
                self._hide_suggestions()
        else:
            self._hide_suggestions()

    def _show_suggestions(self, suggestions):
        # --- MODIFIED: Clear old widgets, don't destroy toplevel ---
        for widget in self._suggestion_listbox.winfo_children():
            widget.destroy()

        self._suggestion_labels.clear()
        self._suggestion_frames.clear()
        self._active_suggestion_index = -1

        # --- Repopulate the listbox ---
        for i, item in enumerate(suggestions[:5]): # Show max 5 suggestions
            item_frame = ctk.CTkFrame(self._suggestion_listbox, fg_color="transparent")
            item_frame.pack(fill="x")
            item_frame.grid_columnconfigure(0, weight=1)

            label = ctk.CTkLabel(item_frame, text=item, anchor="w", padx=5)
            label.grid(row=0, column=0, sticky="ew")
            
            if self.app and self.history_key:
                del_button = ctk.CTkButton(
                    item_frame, text="X", width=25, height=25,
                    fg_color="transparent", text_color=("gray40", "gray60"), hover_color="gray70",
                    command=lambda val=item: self._delete_suggestion(val)
                )
                del_button.grid(row=0, column=1, padx=(0, 5))
            
            item_frame.bind("<Button-1>", lambda e, val=item: self._select_suggestion(val))
            label.bind("<Button-1>", lambda e, val=item: self._select_suggestion(val))
            
            item_frame.bind("<Enter>", lambda e, index=i: self._on_mouse_enter(index))
            item_frame.bind("<Leave>", lambda e, index=i: self._on_mouse_leave(index))
            
            self._suggestion_labels.append(label)
            self._suggestion_frames.append(item_frame)

        # --- MODIFIED: Update position and show (deiconify) ---
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height()
        w = self.winfo_width()
        
        self._suggestion_toplevel.wm_geometry(f"{w}x{y}+{x}+{y}")
        self._suggestion_toplevel.deiconify() # Show the existing window
        self._suggestion_toplevel.lift()

    def _hide_suggestions(self):
        # --- MODIFIED: Just withdraw, don't destroy ---
        if self._focus_out_after_id:
            self.after_cancel(self._focus_out_after_id)
            self._focus_out_after_id = None
            
        if self._suggestion_toplevel:
            self._suggestion_toplevel.withdraw() # Hide the window
            
        self._active_suggestion_index = -1

    def _select_suggestion(self, value):
        # --- MODIFIED: Cancel focus-out timer before hiding ---
        if self._focus_out_after_id:
            self.after_cancel(self._focus_out_after_id)
            self._focus_out_after_id = None

        self.delete(0, "end")
        self.insert(0, value)
        self._hide_suggestions()
        self.focus() # Return focus to the entry

    def _on_focus_out(self, event):
        # --- MODIFIED: Use a 300ms delay to allow clicks on suggestion/button ---
        if self._focus_out_after_id:
            self.after_cancel(self._focus_out_after_id)
        self._focus_out_after_id = self.after(300, self._hide_suggestions)

    def _delete_suggestion(self, value):
        if self.app and self.history_key:
            self.app.remove_history(self.history_key, value)
            
            if value in self.suggestions:
                self.suggestions.remove(value)
                
            # --- MODIFIED: Cancel focus-out, regain focus, and re-run search ---
            if self._focus_out_after_id:
                self.after_cancel(self._focus_out_after_id)
                self._focus_out_after_id = None
            
            self.focus()
            self._perform_search() # Re-filter and show the updated list

    def _highlight_suggestion(self, index):
        for i, frame in enumerate(self._suggestion_frames):
            if i == index:
                frame.configure(fg_color="gray70")
            else:
                frame.configure(fg_color="transparent")

    def _on_mouse_enter(self, index):
        if 0 <= index < len(self._suggestion_frames):
            # self._highlight_suggestion(index) # This causes highlight to fight with arrow keys
            self._suggestion_frames[index].configure(fg_color="gray70")
            self._active_suggestion_index = index

    def _on_mouse_leave(self, index):
        if 0 <= index < len(self._suggestion_frames):
            self._suggestion_frames[index].configure(fg_color="transparent")
            self._active_suggestion_index = -1

    def _on_arrow_down(self, event):
        if not self._suggestion_toplevel.winfo_viewable() or not self._suggestion_frames:
            return

        self._active_suggestion_index += 1
        if self._active_suggestion_index >= len(self._suggestion_frames):
            self._active_suggestion_index = 0
            
        self._highlight_suggestion(self._active_suggestion_index)
        return "break"

    def _on_arrow_up(self, event):
        if not self._suggestion_toplevel.winfo_viewable() or not self._suggestion_frames:
            return

        self._active_suggestion_index -= 1
        if self._active_suggestion_index < 0:
            self._active_suggestion_index = len(self._suggestion_frames) - 1
            
        self._highlight_suggestion(self._active_suggestion_index)
        return "break"

    def _on_enter(self, event):
        """Handles the Enter/Return key."""
        # --- MODIFIED: Allow Enter to propagate if dropdown is not active ---
        if not self._suggestion_toplevel.winfo_viewable() or not self._suggestion_labels:
            return # DO NOT return "break". Let the event pass through to other widgets.

        if 0 <= self._active_suggestion_index < len(self._suggestion_labels):
            selected_value = self._suggestion_labels[self._active_suggestion_index].cget("text")
            self._select_suggestion(selected_value)
            
        return "break" # NOW we stop the event, because we've used it to select an item.