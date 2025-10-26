# tabs/autocomplete_widget.py
import customtkinter as ctk

class AutocompleteEntry(ctk.CTkEntry):
    def __init__(self, parent, suggestions_list=None, app_instance=None, history_key=None, **kwargs):
        super().__init__(parent, **kwargs)

        self.suggestions = suggestions_list if suggestions_list is not None else []
        self.app = app_instance
        self.history_key = history_key
        
        self._suggestion_toplevel = None
        self._after_id = None
        
        # --- For keyboard navigation ---
        self._active_suggestion_index = -1
        self._suggestion_labels = []
        self._suggestion_frames = [] # --- NEW: To hold label + button

        self.bind("<KeyRelease>", self._on_key_release)
        self.bind("<FocusOut>", self._on_focus_out)
        self.bind("<Down>", self._on_arrow_down)
        self.bind("<Up>", self._on_arrow_up)
        self.bind("<Return>", self._on_enter) # Bind Enter key

    def _on_key_release(self, event):
        # Stop if the user is just navigating
        if event.keysym in ("Up", "Down", "Return", "Enter"):
            return

        if event.keysym in ("BackSpace", "Left", "Right", "Shift_L", "Shift_R", "Control_L", "Control_R"):
            return

        current_text = self.get().lower()
        
        # --- MODIFIED: Refresh suggestions if they exist ---
        if self._suggestion_toplevel:
            self._hide_suggestions()
        # ---

        if current_text:
            matching_suggestions = [s for s in self.suggestions if current_text in s.lower()]
            if matching_suggestions:
                self._show_suggestions(matching_suggestions)

    def _show_suggestions(self, suggestions):
        if self._suggestion_toplevel:
            self._suggestion_toplevel.destroy()

        self._suggestion_labels.clear()
        self._suggestion_frames.clear() # --- NEW ---
        self._active_suggestion_index = -1

        self._suggestion_toplevel = ctk.CTkToplevel(self)
        self._suggestion_toplevel.wm_overrideredirect(True) # No title bar

        # Position the dropdown
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height()
        w = self.winfo_width() # Match the entry width
        self._suggestion_toplevel.wm_geometry(f"{w}x{y}+{x}+{y}")
        self._suggestion_toplevel.lift()
        self._suggestion_toplevel.attributes("-topmost", True)

        self._suggestion_listbox = ctk.CTkFrame(self._suggestion_toplevel, fg_color=("gray90", "gray20"))
        self._suggestion_listbox.pack(expand=True, fill="both")

        for i, item in enumerate(suggestions[:5]): # Show max 5 suggestions
            # --- NEW: Create a frame for each item ---
            item_frame = ctk.CTkFrame(self._suggestion_listbox, fg_color="transparent")
            item_frame.pack(fill="x")
            item_frame.grid_columnconfigure(0, weight=1)

            label = ctk.CTkLabel(item_frame, text=item, anchor="w", padx=5)
            label.grid(row=0, column=0, sticky="ew")
            
            # --- NEW: Add delete button if app and key are provided ---
            if self.app and self.history_key:
                del_button = ctk.CTkButton(
                    item_frame, text="X", width=25, height=25,
                    fg_color="transparent", text_color=("gray40", "gray60"), hover_color="gray70",
                    command=lambda val=item: self._delete_suggestion(val)
                )
                del_button.grid(row=0, column=1, padx=(0, 5))
            
            # Bind events to the whole frame
            item_frame.bind("<Button-1>", lambda e, val=item: self._select_suggestion(val))
            label.bind("<Button-1>", lambda e, val=item: self._select_suggestion(val)) # Also bind label for good measure
            
            item_frame.bind("<Enter>", lambda e, index=i: self._on_mouse_enter(index))
            item_frame.bind("<Leave>", lambda e, index=i: self._on_mouse_leave(index))
            
            self._suggestion_labels.append(label)
            self._suggestion_frames.append(item_frame) # --- NEW ---

    def _hide_suggestions(self):
        self._after_id = None
        if self._suggestion_toplevel:
            self._suggestion_toplevel.destroy()
            self._suggestion_toplevel = None
            
        self._suggestion_labels.clear()
        self._suggestion_frames.clear() # --- NEW ---
        self._active_suggestion_index = -1

    def _select_suggestion(self, value):
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None

        self.delete(0, "end")
        self.insert(0, value)
        self._hide_suggestions()
        self.focus()

    def _on_focus_out(self, event):
        if self._after_id:
            self.after_cancel(self._after_id)
        # --- MODIFIED: Use a 300ms delay to allow delete button to be clicked ---
        self._after_id = self.after(300, self._hide_suggestions)

    # --- NEW: Delete Suggestion Method ---
    def _delete_suggestion(self, value):
        if self.app and self.history_key:
            # 1. Ask the app to remove it from the master list (HistoryManager)
            self.app.remove_history(self.history_key, value)
            
            # 2. Remove from this widget's local list
            if value in self.suggestions:
                self.suggestions.remove(value)
                
            # 3. Refresh the dropdown to show the change
            self._hide_suggestions()
            # Simulate a key release to re-filter and re-open the dropdown
            self.event_generate("<KeyRelease>", keysym="a")
            self.delete(len(self.get())-1, "end") # Remove the 'a' we just typed
            
            # Stop the focus-out event from firing
            if self._after_id:
                self.after_cancel(self._after_id)
                self._after_id = None
            
            self.focus()


    def _highlight_suggestion(self, index):
        """Highlights the suggestion at the given index."""
        # --- MODIFIED: Use suggestion_frames ---
        for i, frame in enumerate(self._suggestion_frames):
            if i == index:
                frame.configure(fg_color="gray70")
            else:
                frame.configure(fg_color="transparent")

    def _on_mouse_enter(self, index):
        """Syncs the active index when mousing over."""
        # --- MODIFIED: Use suggestion_frames ---
        if 0 <= index < len(self._suggestion_frames):
            self._suggestion_frames[index].configure(fg_color="gray70")
            self._active_suggestion_index = index

    def _on_mouse_leave(self, index):
        """Resets the active index when mousing out."""
        # --- MODIFIED: Use suggestion_frames ---
        if 0 <= index < len(self.Ssuggestion_frames):
            self._suggestion_frames[index].configure(fg_color="transparent")
            self._active_suggestion_index = -1

    def _on_arrow_down(self, event):
        """Handles the Down arrow key."""
        # --- MODIFIED: Use suggestion_frames ---
        if not self._suggestion_toplevel or not self._suggestion_frames:
            return

        self._active_suggestion_index += 1
        if self._active_suggestion_index >= len(self._suggestion_frames):
            self._active_suggestion_index = 0
            
        self._highlight_suggestion(self._active_suggestion_index)
        return "break"

    def _on_arrow_up(self, event):
        """Handles the Up arrow key."""
        # --- MODIFIED: Use suggestion_frames ---
        if not self._suggestion_toplevel or not self._suggestion_frames:
            return

        self._active_suggestion_index -= 1
        if self._active_suggestion_index < 0:
            self._active_suggestion_index = len(self._suggestion_frames) - 1
            
        self._highlight_suggestion(self._active_suggestion_index)
        return "break"

    def _on_enter(self, event):
        """Handles the Enter/Return key."""
        # --- MODIFIED: Use suggestion_labels ---
        if not self._suggestion_toplevel or not self._suggestion_labels:
            return

        if 0 <= self._active_suggestion_index < len(self._suggestion_labels):
            selected_value = self._suggestion_labels[self._active_suggestion_index].cget("text")
            self._select_suggestion(selected_value)
            
        return "break"