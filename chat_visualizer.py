import tkinter as tk
import colorsys
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from urllib.parse import unquote

from chat_parser import Conversation, load_conversations


class ChatVisualizerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Chat Visualizer")
        self.geometry("1200x720")

        self.conversations: list[Conversation] = []
        self.player_colors: dict[str, str] = {}

        controls = ttk.Frame(self)
        controls.pack(fill=tk.X, padx=8, pady=8)

        ttk.Button(controls, text="Open JSON", command=self._open_json).pack(side=tk.LEFT)
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
            columns=("name", "creator", "participants", "message_count", "created_round", "last_round"),
            show="headings",
            selectmode="browse",
        )
        self.conversation_table.heading("name", text="Conversation")
        self.conversation_table.heading("creator", text="Created By")
        self.conversation_table.heading("participants", text="Participants")
        self.conversation_table.heading("message_count", text="Player Messages")
        self.conversation_table.heading("created_round", text="Created In Round")
        self.conversation_table.heading("last_round", text="Last Used In Round")
        self.conversation_table.column("name", width=220)
        self.conversation_table.column("creator", width=140)
        self.conversation_table.column("participants", width=260)
        self.conversation_table.column("message_count", width=110, anchor=tk.CENTER)
        self.conversation_table.column("created_round", width=120, anchor=tk.CENTER)
        self.conversation_table.column("last_round", width=120, anchor=tk.CENTER)
        self.conversation_table.bind("<<TreeviewSelect>>", self._render_conversation)
        self.conversation_table.pack(fill=tk.BOTH, expand=True)

        self.message_view = tk.Text(right_panel, wrap=tk.WORD, state=tk.DISABLED)
        self.message_view.pack(fill=tk.BOTH, expand=True)
        self.message_view.tag_configure("round", foreground="#7f1d1d", font=("TkDefaultFont", 10, "bold"))
        self.message_view.tag_configure("notification", foreground="#374151")
        self.message_view.tag_configure("metadata", foreground="#374151")

    def _open_json(self):
        file_path = filedialog.askopenfilename(
            title="Choose chat JSON",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not file_path:
            return

        try:
            self.conversations = load_conversations(file_path)
        except Exception as exc:  # pragma: no cover - tkinter path
            messagebox.showerror("Invalid file", f"Could not load file:\n{exc}")
            return

        self._populate_conversations(Path(file_path).name)

    def _populate_conversations(self, file_name: str):
        self.conversation_table.delete(*self.conversation_table.get_children())
        for conversation in self.conversations:
            participants = ", ".join(conversation.participants) if conversation.participants else "(not provided)"
            creator = conversation.creator or "(not provided)"
            message_count = conversation.player_message_count
            created_round = conversation.created_round if conversation.created_round is not None else "1"
            last_round = conversation.last_active_round if conversation.last_active_round is not None else "1"
            self.conversation_table.insert(
                "",
                tk.END,
                iid=conversation.conversation_id,
                values=(conversation.name, creator, participants, message_count, created_round, last_round),
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

        conversation_id = selected[0]
        conversation = next((item for item in self.conversations if item.conversation_id == conversation_id), None)
        if conversation is None:
            return

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
            if message.runtime_type == "gameNotification":
                self.message_view.insert(tk.END, f"[GAME] {message.body}\n", "notification")
            else:
                sender = unquote(message.sender or "Unknown")
                self.message_view.insert(tk.END, f"{sender}: ", self._player_tag(sender))
                self.message_view.insert(tk.END, f"{message.body}\n")

        self.message_view.config(state=tk.DISABLED)

    def _player_tag(self, player: str) -> str:
        tag = f"player-{player}"
        if player not in self.player_colors:
            color_index = len(self.player_colors)
            hue = (color_index * 0.618033988749895) % 1
            red, green, blue = colorsys.hsv_to_rgb(hue, 0.72, 0.72)
            color = f"#{round(red * 255):02x}{round(green * 255):02x}{round(blue * 255):02x}"
            self.player_colors[player] = color
            self.message_view.tag_configure(tag, foreground=color, font=("TkDefaultFont", 10, "bold"))
        return tag


def main():
    app = ChatVisualizerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
