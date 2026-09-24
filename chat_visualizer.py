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
        self.geometry("1800x900")

        self.conversations: list[Conversation] = []
        self.player_colors: dict[str, str] = {}
        self.selected_conversation_id: str | None = None

        controls = ttk.Frame(self)
        controls.pack(fill=tk.X, padx=8, pady=8)

        ttk.Button(controls, text="Open JSON", command=self._open_json).pack(side=tk.LEFT)
        self.status = ttk.Label(controls, text="Load a JSON file to begin")
        self.status.pack(side=tk.LEFT, padx=12)

        content = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        content.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        left_panel = ttk.Frame(content)
        right_panel = ttk.Frame(content)
        content.add(left_panel, weight=2, minsize=1000)
        content.add(right_panel, weight=1, minsize=500)

        columns = (
            ("name", "Conversation", 220),
            ("creator", "Created By", 140),
            ("participants", "Participants", 260),
            ("message_count", "Player Messages", 110),
            ("created_round", "Created In Round", 120),
            ("last_round", "Last Used In Round", 120),
        )
        self.table_column_widths = [width for _key, _heading, width in columns]
        table = ttk.Frame(left_panel)
        table.pack(fill=tk.BOTH, expand=True)
        for column_index, (_key, heading, width) in enumerate(columns):
            ttk.Label(table, text=heading, anchor=tk.W, padding=(4, 2)).grid(
                row=0, column=column_index, sticky="nsew"
            )
            table.grid_columnconfigure(column_index, minsize=width, weight=1)
        self.conversation_table = table
        self.table_body = ttk.Frame(table)
        self.table_body.grid(row=1, column=0, columnspan=len(columns), sticky="nsew")
        for column_index, width in enumerate(self.table_column_widths):
            self.table_body.grid_columnconfigure(column_index, minsize=width, weight=1)
        table.grid_rowconfigure(1, weight=1)

        self.message_view = tk.Text(right_panel, wrap=tk.WORD, state=tk.DISABLED)
        self.message_view.pack(fill=tk.BOTH, expand=True)
        self.message_view.tag_configure("round", foreground="#7f1d1d", font=("TkDefaultFont", 10, "bold"))
        self.message_view.tag_configure("notification", foreground="#1d4ed8")
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
        for child in self.table_body.winfo_children():
            child.destroy()
        for row_index, conversation in enumerate(self.conversations):
            row = tk.Frame(self.table_body, borderwidth=0)
            row.grid(row=row_index, column=0, sticky="ew")
            for column_index, width in enumerate(self.table_column_widths):
                row.grid_columnconfigure(column_index, minsize=width, weight=1)
            values = (
                conversation.name,
                conversation.creator or "(not provided)",
                conversation.participants,
                conversation.player_message_count,
                conversation.created_round if conversation.created_round is not None else "1",
                conversation.last_active_round if conversation.last_active_round is not None else "1",
            )
            for column_index, value in enumerate(values):
                cell = tk.Frame(row, borderwidth=0, padx=4, pady=3)
                cell.grid(row=0, column=column_index, sticky="nsew")
                if column_index == 2 and isinstance(value, list):
                    if value:
                        for participant in value:
                            self._colored_label(cell, participant).pack(anchor=tk.W)
                    else:
                        tk.Label(cell, text="(not provided)", fg="#374151").pack(anchor=tk.W)
                else:
                    player = value if column_index == 1 and value != "(not provided)" else None
                    label = self._colored_label(cell, player) if player else tk.Label(cell, text=str(value), fg="#374151")
                    label.pack(anchor=tk.W)
                self._bind_table_widget(cell, conversation.conversation_id)
            self._bind_table_widget(row, conversation.conversation_id)

        self.status.configure(text=f"Loaded {len(self.conversations)} conversations from {file_name}")
        if self.conversations:
            self._select_conversation(self.conversations[0].conversation_id)

    def _render_conversation(self, _event):
        if self.selected_conversation_id is None:
            return

        conversation = next(
            (item for item in self.conversations if item.conversation_id == self.selected_conversation_id), None
        )
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

    def _select_conversation(self, conversation_id: str):
        self.selected_conversation_id = conversation_id
        self._render_conversation(None)

    def _bind_table_widget(self, widget: tk.Widget, conversation_id: str):
        widget.bind("<Button-1>", lambda _event: self._select_conversation(conversation_id))
        for child in widget.winfo_children():
            self._bind_table_widget(child, conversation_id)

    def _colored_label(self, parent: tk.Widget, player: str) -> tk.Label:
        color = self._player_color(player)
        return tk.Label(parent, text=player, fg=color, font=("TkDefaultFont", 9, "bold"))

    def _player_color(self, player: str) -> str:
        if player not in self.player_colors:
            color_index = len(self.player_colors)
            hue = (color_index * 0.618033988749895) % 1
            red, green, blue = colorsys.hsv_to_rgb(hue, 0.72, 0.72)
            self.player_colors[player] = f"#{round(red * 255):02x}{round(green * 255):02x}{round(blue * 255):02x}"
        return self.player_colors[player]

    def _player_tag(self, player: str) -> str:
        tag = f"player-{player}"
        if player not in self.player_colors:
            self._player_color(player)
        self.message_view.tag_configure(
            tag, foreground=self.player_colors[player], font=("TkDefaultFont", 10, "bold")
        )
        return tag


def main():
    app = ChatVisualizerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
