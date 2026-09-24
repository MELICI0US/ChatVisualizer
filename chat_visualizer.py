from __future__ import annotations

import tkinter as tk
import colorsys
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from urllib.parse import unquote

from chat_parser import (
    Conversation,
    load_common_reasons,
    load_conversations,
    reasons_path_for,
    save_reasons,
)


COMMON_REASONS_PATH = Path(__file__).with_name("common_reasons.json")
DEFAULT_COMMON_REASONS = (
    "random initial group",
    "combining groups",
    "continuing an existing group",
    "testing a group",
)
OTHER_REASON = "Other"


class ChatVisualizerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Chat Visualizer")
        self.geometry("1600x720")

        self.conversations: list[Conversation] = []
        try:
            common_reasons = load_common_reasons(COMMON_REASONS_PATH)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Invalid common reasons file", f"Could not load common reasons:\n{exc}")
            common_reasons = list(DEFAULT_COMMON_REASONS)
        self.common_reasons = tuple(common_reasons)
        self.reasons_path: Path | None = None
        self.player_colors: dict[str, str] = {}
        self.player_tags: dict[str, str] = {}
        self.table_player_tags: dict[str, str] = {}
        self._next_color_index = 0

        controls = ttk.Frame(self)
        controls.pack(fill=tk.X, padx=8, pady=8)

        ttk.Button(controls, text="Open JSON", command=self._open_json).pack(side=tk.LEFT)
        self.save_reasons_button = ttk.Button(
            controls,
            text="Save Reasons",
            command=self._save_reasons,
            state=tk.DISABLED,
        )
        self.save_reasons_button.pack(side=tk.LEFT, padx=(8, 0))
        self.status = ttk.Label(controls, text="Load a JSON file to begin")
        self.status.pack(side=tk.LEFT, padx=12)

        content = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        content.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        left_panel = ttk.Frame(content)
        right_panel = ttk.Frame(content)
        content.add(left_panel, weight=1)
        content.add(right_panel, weight=2)

        self.conversation_table = ttk.Treeview(
            left_panel,
            columns=("name", "creator", "participants", "message_count", "created_round", "last_round", "reason"),
            show="headings",
            selectmode="browse",
        )
        self.conversation_table.heading("name", text="Conversation")
        self.conversation_table.heading("creator", text="Created By")
        self.conversation_table.heading("participants", text="Participants")
        self.conversation_table.heading("message_count", text="# Messages")
        self.conversation_table.heading("created_round", text="Created Round")
        self.conversation_table.heading("last_round", text="Last Used Round")
        self.conversation_table.heading("reason", text="Reason")
        self.conversation_table.column("name", width=220)
        self.conversation_table.column("creator", width=140)
        self.conversation_table.column("participants", width=140)
        self.conversation_table.column("message_count", width=110, anchor=tk.CENTER)
        self.conversation_table.column("created_round", width=120, anchor=tk.CENTER)
        self.conversation_table.column("last_round", width=120, anchor=tk.CENTER)
        self.conversation_table.column("reason", width=220)
        self.conversation_table.tag_configure("conversation-separator", foreground="#9ca3af")
        self.conversation_table.bind("<<TreeviewSelect>>", self._render_conversation)
        self.conversation_table.pack(fill=tk.BOTH, expand=True)

        reason_frame = ttk.Frame(right_panel)
        reason_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(reason_frame, text="Why was this chat created?").pack(side=tk.LEFT)
        self.reason_choice_var = tk.StringVar()
        self.reason_choice = ttk.Combobox(
            reason_frame,
            textvariable=self.reason_choice_var,
            values=(*self.common_reasons, OTHER_REASON),
            state="readonly",
            width=28,
        )
        self.reason_choice.pack(side=tk.LEFT, padx=(8, 0))
        self.reason_choice.bind("<<ComboboxSelected>>", self._reason_choice_selected)
        self.reason_entry_var = tk.StringVar()
        self.reason_entry = ttk.Entry(reason_frame, textvariable=self.reason_entry_var, state=tk.DISABLED)
        self.reason_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0))
        self.reason_entry.bind("<KeyRelease>", self._update_current_reason)
        self.reason_entry.bind("<Return>", self._save_current_reason)

        self.message_view = tk.Text(right_panel, wrap=tk.WORD, state=tk.DISABLED)
        self.message_view.pack(fill=tk.BOTH, expand=True)
        self.message_view.tag_configure("round", foreground="#7f1d1d", font=("TkDefaultFont", 10, "bold"))
        self.message_view.tag_configure("notification", foreground="#000000")
        self.message_view.tag_configure("metadata", foreground="#374151")

    def _open_json(self):
        file_path = filedialog.askopenfilename(
            title="Choose chat JSON",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not file_path:
            return

        try:
            self.reasons_path = reasons_path_for(file_path)
            self.conversations = load_conversations(file_path, self.reasons_path)
        except Exception as exc:  # pragma: no cover - tkinter path
            messagebox.showerror("Invalid file", f"Could not load file:\n{exc}")
            return

        self._populate_conversations(Path(file_path).name)
        self.save_reasons_button.configure(state=tk.NORMAL)

    def _populate_conversations(self, file_name: str):
        self.conversation_table.delete(*self.conversation_table.get_children())
        for conversation_index, conversation in enumerate(self.conversations):
            creator = conversation.creator or "(not provided)"
            message_count = conversation.player_message_count
            created_round = conversation.created_round if conversation.created_round is not None else "1"
            last_round = conversation.last_active_round if conversation.last_active_round is not None else "1"
            participants = conversation.participants or ["(not provided)"]
            for index, participant in enumerate(participants):
                player_tag = self._table_player_tag(participant) if participant != "(not provided)" else ()
                self.conversation_table.insert(
                    "",
                    tk.END,
                    iid=f"{conversation.conversation_id}:{index}",
                    values=(
                        conversation.name if index == 0 else "",
                        creator if index == 0 else "",
                        participant,
                        message_count if index == 0 else "",
                        created_round if index == 0 else "",
                        last_round if index == 0 else "",
                        conversation.reason if index == 0 else "",
                    ),
                    tags=(player_tag,) if player_tag else (),
                )
            if conversation_index < len(self.conversations) - 1:
                self.conversation_table.insert(
                    "",
                    tk.END,
                    iid=f"__separator__{conversation_index}",
                    values=("-" * 18, "-" * 12, "-" * 20, "-" * 8, "-" * 10, "-" * 10, "-" * 18),
                    tags=("conversation-separator",),
                )

        self.status.configure(text=f"Loaded {len(self.conversations)} conversations from {file_name}")
        first = self.conversation_table.get_children()
        if first:
            self.conversation_table.selection_set(first[0])
            self._render_conversation(None)

    def _render_conversation(self, _event):
        selected = self.conversation_table.selection()
        if not selected:
            return

        if "conversation-separator" in self.conversation_table.item(selected[0], "tags"):
            self.conversation_table.selection_remove(selected[0])
            return

        conversation_id = selected[0].rsplit(":", 1)[0]
        conversation = next((item for item in self.conversations if item.conversation_id == conversation_id), None)
        if conversation is None:
            return

        if conversation.reason in self.common_reasons:
            self.reason_choice_var.set(conversation.reason)
            self.reason_entry_var.set("")
            self.reason_entry.configure(state=tk.DISABLED)
        else:
            self.reason_choice_var.set(OTHER_REASON)
            self.reason_entry.configure(state=tk.NORMAL)
            self.reason_entry_var.set(conversation.reason)
        self.message_view.config(state=tk.NORMAL)
        self.message_view.delete("1.0", tk.END)

        self.message_view.insert(tk.END, f"{conversation.name}\n", "metadata")
        self.message_view.insert(tk.END, "Participants: ", "metadata")
        if conversation.participants:
            for index, participant in enumerate(conversation.participants):
                if index:
                    self.message_view.insert(tk.END, ", ", "metadata")
                self.message_view.insert(tk.END, participant, self._player_tag(participant))
            self.message_view.insert(tk.END, "\n")
        else:
            self.message_view.insert(tk.END, "(not provided)\n", "metadata")
        self.message_view.insert(tk.END, "Created by: ", "metadata")
        if conversation.creator:
            self.message_view.insert(tk.END, conversation.creator, self._player_tag(conversation.creator))
        else:
            self.message_view.insert(tk.END, "(not provided)", "metadata")
        self.message_view.insert(tk.END, "\n")

        created = conversation.created_at.isoformat() if conversation.created_at else "n/a"
        last_used = conversation.last_active_at.isoformat() if conversation.last_active_at else "n/a"
        self.message_view.insert(
            tk.END,
            f"Created: {created} (Round {conversation.created_round if conversation.created_round is not None else '1'})\n",
            "metadata",
        )
        self.message_view.insert(
            tk.END,
            f"Last used: {last_used} (Round {conversation.last_active_round if conversation.last_active_round is not None else '?'})\n\n",
            "metadata",
        )

        current_round = object()
        for message in conversation.messages:
            marker = message.round_number if message.round_number is not None else "1"
            if marker != current_round:
                self.message_view.insert(tk.END, f"=== Round {marker} ===\n", "round")
                current_round = marker

            timestamp = message.time.isoformat()
            if message.runtime_type != "gameNotification":
                sender = unquote(message.sender or "Unknown")
                self.message_view.insert(tk.END, f"{sender}: ", self._player_tag(sender))
                self.message_view.insert(tk.END, f"{message.body}\n")

        self.message_view.config(state=tk.DISABLED)

    def _selected_conversation(self) -> Conversation | None:
        selected = self.conversation_table.selection()
        if not selected or "conversation-separator" in self.conversation_table.item(selected[0], "tags"):
            return None
        conversation_id = selected[0].rsplit(":", 1)[0]
        return next((item for item in self.conversations if item.conversation_id == conversation_id), None)

    def _save_current_reason(self, _event=None):
        self._update_current_reason()
        self._save_reasons()

    def _reason_choice_selected(self, _event=None):
        if self.reason_choice_var.get() == OTHER_REASON:
            self.reason_entry.configure(state=tk.NORMAL)
            self.reason_entry.focus_set()
        else:
            self.reason_entry_var.set("")
            self.reason_entry.configure(state=tk.DISABLED)
        self._update_current_reason()

    def _current_reason(self) -> str:
        if self.reason_choice_var.get() == OTHER_REASON:
            return self.reason_entry_var.get().strip()
        return self.reason_choice_var.get().strip()

    def _update_current_reason(self, _event=None):
        conversation = self._selected_conversation()
        if conversation is None:
            return
        conversation.reason = self._current_reason()
        self.conversation_table.set(self.conversation_table.selection()[0], "reason", conversation.reason)

    def _save_reasons(self):
        conversation = self._selected_conversation()
        if conversation is not None:
            conversation.reason = self._current_reason()
            self.conversation_table.set(self.conversation_table.selection()[0], "reason", conversation.reason)
        if self.reasons_path is None:
            return
        try:
            save_reasons(self.reasons_path, {item.conversation_id: item.reason for item in self.conversations})
        except OSError as exc:  # pragma: no cover - tkinter path
            messagebox.showerror("Could not save reasons", f"Could not save reasons file:\n{exc}")
            return
        self.status.configure(text=f"Saved chat reasons to {self.reasons_path.name}")

    def _player_tag(self, player: str) -> str:
        tag = self.player_tags.get(player)
        if tag is None:
            tag = f"player-{len(self.player_tags)}"
            self.player_tags[player] = tag
        color = self._ensure_player_color(player)
        self.message_view.tag_configure(tag, foreground=color, font=("TkDefaultFont", 10, "bold"))
        return tag

    def _ensure_player_color(self, player: str) -> str:
        color = self.player_colors.get(player)
        if color is not None:
            return color

        while True:
            hue = (self._next_color_index * 0.618033988749895) % 1
            self._next_color_index += 1
            red, green, blue = colorsys.hsv_to_rgb(hue, 0.72, 0.72)
            color = f"#{round(red * 255):02x}{round(green * 255):02x}{round(blue * 255):02x}"
            if color != "#000000" and color not in self.player_colors.values():
                break

        self.player_colors[player] = color
        return color

    def _table_player_tag(self, player: str) -> str:
        tag = self.table_player_tags.get(player)
        if tag is None:
            tag = f"table-player-{len(self.table_player_tags)}"
            self.table_player_tags[player] = tag
        self.conversation_table.tag_configure(tag, foreground=self._ensure_player_color(player))
        return tag


def main():
    app = ChatVisualizerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
