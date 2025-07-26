# tabs/autocomplete_widget.py
import customtkinter as ctk

class AutocompleteEntry(ctk.CTkEntry):
    def __init__(self, parent, suggestions_list=None, **kwargs):
        super().__init__(parent, **kwargs)

        self.suggestions = suggestions_list if suggestions_list is not None else []
        self._suggestion_toplevel = None

        self.bind("<KeyRelease>", self._on_key_release)
        self.bind("<FocusOut>", self._on_focus_out)
        self.bind("<Down>", self._on_arrow_down)

    def _on_key_release(self, event):
        if event.keysym in ("BackSpace", "Left", "Right", "Up", "Down", "Shift_L", "Shift_R", "Control_L", "Control_R"):
            return

        current_text = self.get().lower()
        self._hide_suggestions()

        if current_text:
            matching_suggestions = [s for s in self.suggestions if current_text in s.lower()]
            if matching_suggestions:
                self._show_suggestions(matching_suggestions)

    def _show_suggestions(self, suggestions):
        if self._suggestion_toplevel:
            self._suggestion_toplevel.destroy()

        self._suggestion_toplevel = ctk.CTkToplevel(self)
        self._suggestion_toplevel.wm_overrideredirect(True) # No title bar

        # Position the dropdown
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height()
        self._suggestion_toplevel.wm_geometry(f"+{x}+{y}")
        self._suggestion_toplevel.lift()
        self._suggestion_toplevel.attributes("-topmost", True)

        self._suggestion_listbox = ctk.CTkFrame(self._suggestion_toplevel, fg_color=("gray90", "gray20"))
        self._suggestion_listbox.pack(expand=True, fill="both")

        for item in suggestions[:5]: # Show max 5 suggestions
            label = ctk.CTkLabel(self._suggestion_listbox, text=item, anchor="w", padx=5)
            label.pack(fill="x")
            label.bind("<Button-1>", lambda e, val=item: self._select_suggestion(val))
            label.bind("<Enter>", lambda e, w=label: w.configure(fg_color="gray70"))
            label.bind("<Leave>", lambda e, w=label: w.configure(fg_color="transparent"))

    def _hide_suggestions(self):
        if self._suggestion_toplevel:
            self._suggestion_toplevel.destroy()
            self._suggestion_toplevel = None

    def _select_suggestion(self, value):
        self.delete(0, "end")
        self.insert(0, value)
        self._hide_suggestions()
        self.focus()

    def _on_focus_out(self, event):
        self.after(200, self._hide_suggestions) # Delay to allow click to register

    def _on_arrow_down(self, event):
        if self._suggestion_toplevel:
            first_label = self._suggestion_listbox.winfo_children()[0]
            first_label.focus_set()