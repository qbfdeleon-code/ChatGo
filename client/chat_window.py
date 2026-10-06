"""Main chat window: conversation list (sidebar) + thread + message input."""
from __future__ import annotations

from datetime import datetime

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
    QScrollArea, QVBoxLayout, QWidget,
)

from client import theme
from client.network import NetworkClient
from client.widgets import AvatarWidget, ConversationTile, EmojiPicker, MessageBubble
from common.protocol import GENERAL


def short_time(ts: float) -> str:
    dt, today = datetime.fromtimestamp(ts), datetime.now().date()
    if dt.date() == today:
        return dt.strftime("%I:%M %p").lstrip("0")
    if (today - dt.date()).days == 1:
        return "Yesterday"
    return dt.strftime("%b %d")


class ChatWindow(QWidget):
    def __init__(self, client: NetworkClient, session: dict) -> None:
        super().__init__()
        self.client = client
        self.me: str = session["username"]
        self.my_avatar: str = session["avatar"]
        self.users: dict[str, dict] = {u["username"]: u for u in session["users"]}
        self.users[self.me] = {"username": self.me, "avatar": self.my_avatar, "online": True}

        self.messages: dict[str, list[dict]] = {GENERAL: []}   # conversation key -> messages
        self.unread: dict[str, int] = {}
        self.current = GENERAL
        self.editing_id: int | None = None

        for msg in session["history"]:
            self._store(msg)

        self._build_ui()
        self.client.packet_received.connect(self._on_packet)
        self.client.disconnected.connect(self._on_disconnected)
        self.client.start_listening()
        self._open_conversation(GENERAL)

    # ------------------------------------------------------------------- UI
    def _build_ui(self) -> None:
        self.setObjectName("Root")
        self.setWindowTitle(f"ChatWave — {self.my_avatar} {self.me}")
        self.resize(940, 680)
        self.setMinimumSize(720, 480)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---- sidebar
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(310)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(14, 16, 14, 12)
        side.setSpacing(10)

        brand = QLabel("ChatWave")
        brand.setObjectName("Brand")
        me = QLabel(f"{self.my_avatar} {self.me}")
        me.setObjectName("Me")
        side.addWidget(brand)
        side.addWidget(me)

        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍 Search conversations...")
        self.search.textChanged.connect(self._refresh_sidebar)
        side.addWidget(self.search)

        tiles_scroll = QScrollArea()
        tiles_scroll.setWidgetResizable(True)
        tiles_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        container = QWidget()
        container.setObjectName("TileContainer")
        self.tile_layout = QVBoxLayout(container)
        self.tile_layout.setContentsMargins(0, 0, 0, 0)
        self.tile_layout.setSpacing(8)
        tiles_scroll.setWidget(container)
        side.addWidget(tiles_scroll, 1)
        root.addWidget(sidebar)

        # ---- chat pane
        pane = QVBoxLayout()
        pane.setContentsMargins(16, 16, 16, 14)
        pane.setSpacing(10)

        header = QFrame()
        header.setObjectName("ChatHeader")
        h = QHBoxLayout(header)
        h.setContentsMargins(14, 10, 14, 10)
        self.header_avatar = AvatarWidget("👥", "#4B42D6", 44)
        titles = QVBoxLayout()
        titles.setSpacing(0)
        self.header_title = QLabel()
        self.header_title.setObjectName("HeaderTitle")
        self.header_status = QLabel()
        self.header_status.setObjectName("HeaderStatus")
        titles.addWidget(self.header_title)
        titles.addWidget(self.header_status)
        h.addWidget(self.header_avatar)
        h.addLayout(titles)
        h.addStretch()
        pane.addWidget(header)

        self.banner = QLabel("")
        self.banner.setObjectName("Banner")
        self.banner.hide()
        pane.addWidget(self.banner)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.msg_area = QWidget()
        self.msg_area.setObjectName("MessageArea")
        self.msg_layout = QVBoxLayout(self.msg_area)
        self.msg_layout.setContentsMargins(6, 6, 6, 6)
        self.msg_layout.setSpacing(8)
        self.scroll.setWidget(self.msg_area)
        pane.addWidget(self.scroll, 1)

        # input row: emoji button, text box, send button
        row = QHBoxLayout()
        self.emoji_button = QPushButton("😊")
        self.emoji_button.setObjectName("EmojiToggle")
        self.emoji_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.emoji_button.clicked.connect(self._show_emoji_picker)
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Type a message...")
        self.message_input.returnPressed.connect(self._send)          # Enter to send
        self.send_button = QPushButton("Send")
        self.send_button.setObjectName("Primary")
        self.send_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_button.clicked.connect(self._send)
        row.addWidget(self.emoji_button)
        row.addWidget(self.message_input, 1)
        row.addWidget(self.send_button)
        pane.addLayout(row)

        # edit row
        edit_row = QHBoxLayout()
        self.edit_button = QPushButton("✏️ Edit last message")
        self.edit_button.setObjectName("Ghost")
        self.edit_button.clicked.connect(self._start_edit)
        self.cancel_edit_button = QPushButton("✖ Cancel edit")
        self.cancel_edit_button.setObjectName("Ghost")
        self.cancel_edit_button.clicked.connect(self._cancel_edit)
        self.cancel_edit_button.hide()
        edit_row.addWidget(self.edit_button)
        edit_row.addWidget(self.cancel_edit_button)
        edit_row.addStretch()
        pane.addLayout(edit_row)
        root.addLayout(pane, 1)

        esc = QShortcut(QKeySequence("Esc"), self.message_input)
        esc.setContext(Qt.ShortcutContext.WidgetShortcut)
        esc.activated.connect(self._cancel_edit)

        self.picker = EmojiPicker(self)
        self.picker.emoji_selected.connect(self._insert_emoji)

    # ----------------------------------------------------------- data helpers
    def _key_for(self, msg: dict) -> str:
        if msg.get("to") is None:
            return GENERAL
        return msg["to"] if msg["sender"] == self.me else msg["sender"]

    def _store(self, msg: dict) -> str:
        key = self._key_for(msg)
        self.messages.setdefault(key, []).append(msg)
        return key

    def _last_message(self, key: str) -> dict | None:
        for msg in reversed(self.messages.get(key, [])):
            if not msg.get("system"):
                return msg
        return None

    @staticmethod
    def _discard(widget: QWidget) -> None:
        """Remove a widget from the screen immediately, free it when Qt gets to it."""
        widget.setParent(None)
        widget.deleteLater()

    # ---------------------------------------------------------------- sidebar
    def _refresh_sidebar(self) -> None:
        while self.tile_layout.count():
            item = self.tile_layout.takeAt(0)
            if item.widget():
                self._discard(item.widget())

        query = self.search.text().strip().lower()
        others = sorted((u for n, u in self.users.items() if n != self.me),
                        key=lambda u: (not u["online"], u["username"].lower()))
        entries = [(GENERAL, "General Chat", "👥", theme.ACCENT, None)]
        entries += [(u["username"], u["username"], u["avatar"],
                     theme.color_for(u["username"]), u["online"]) for u in others]

        for key, title, glyph, color, online in entries:
            if query and query not in title.lower():
                continue
            last = self._last_message(key)
            preview, when = "No messages yet", ""
            if last:
                who = "You" if last["sender"] == self.me else last["sender"]
                preview = f"{who}: {last['text']}" if key == GENERAL else (
                    f"You: {last['text']}" if who == "You" else last["text"])
                when = short_time(last["ts"])
            tile = ConversationTile(key, title, glyph, color, preview, when,
                                    self.unread.get(key, 0), online, key == self.current)
            tile.clicked.connect(self._open_conversation)
            self.tile_layout.addWidget(tile)
        self.tile_layout.addStretch()

    # ------------------------------------------------------------ conversation
    def _open_conversation(self, key: str) -> None:
        self.current = key
        self.unread[key] = 0
        self._cancel_edit()
        self._update_header()
        self._render_messages()
        self._refresh_sidebar()
        self.message_input.setFocus()

    def _update_header(self) -> None:
        if self.current == GENERAL:
            online = sum(1 for u in self.users.values() if u["online"])
            self.header_avatar.set_avatar("👥", "#4B42D6")
            self.header_title.setText("Group 2 Chat")
            self.header_status.setText(f"{online} online")
        else:
            user = self.users.get(self.current, {"avatar": "👤", "online": False})
            self.header_avatar.set_avatar(user["avatar"], theme.color_for(self.current))
            self.header_title.setText(self.current)
            self.header_status.setText("● online" if user["online"] else "offline")

    def _render_messages(self) -> None:
        while self.msg_layout.count():
            item = self.msg_layout.takeAt(0)
            if item.widget():
                self._discard(item.widget())
        self.msg_layout.addStretch()                  # keeps messages anchored to the bottom
        for msg in self.messages.get(self.current, []):
            self.msg_layout.addWidget(self._make_row(msg))
        self._scroll_to_bottom()

    def _make_row(self, msg: dict) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        if msg.get("system"):
            note = QLabel(msg["text"])
            note.setObjectName("SystemNote")
            note.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(note)
            return row
        own = msg["sender"] == self.me
        bubble = MessageBubble(msg, own)
        if own:
            layout.addStretch()
            layout.addWidget(bubble)
        else:
            layout.addWidget(bubble)
            layout.addStretch()
        return row

    def _scroll_to_bottom(self) -> None:
        bar = self.scroll.verticalScrollBar()
        QTimer.singleShot(40, lambda: bar.setValue(bar.maximum()))

    # --------------------------------------------------------------- sending
    def _send(self) -> None:
        text = self.message_input.text().strip()
        if not text:
            return
        if self.editing_id is not None:
            packet = {"type": "edit", "id": self.editing_id, "text": text}
        else:
            packet = {"type": "message", "text": text,
                      "to": None if self.current == GENERAL else self.current}
        if not self.client.send(packet):
            QMessageBox.warning(self, "Error", "Message could not be sent.")
            return
        self.message_input.clear()
        self._cancel_edit()

    def _insert_emoji(self, emoji: str) -> None:
        self.message_input.insert(emoji)
        self.message_input.setFocus()

    def _show_emoji_picker(self) -> None:
        self.picker.show_above(self.emoji_button)

    # --------------------------------------------------------------- editing
    def _start_edit(self) -> None:
        mine = [m for m in self.messages.get(self.current, [])
                if not m.get("system") and m["sender"] == self.me]
        if not mine:
            QMessageBox.information(self, "Edit message",
                                    "You have no message to edit in this conversation yet.")
            return
        last = mine[-1]
        self.editing_id = last["id"]
        self.message_input.setText(last["text"])
        self.message_input.setPlaceholderText("Editing your last message…")
        self.send_button.setText("Save")
        self.cancel_edit_button.show()
        self.message_input.setFocus()

    def _cancel_edit(self) -> None:
        if self.editing_id is None:
            return
        self.editing_id = None
        self.message_input.clear()
        self.message_input.setPlaceholderText("Type a message...")
        self.send_button.setText("Send")
        self.cancel_edit_button.hide()

    # ------------------------------------------------------ incoming packets
    def _on_packet(self, packet: dict) -> None:
        handler = {
            "message": self._on_message, "edited": self._on_edited,
            "presence": self._on_presence, "system": self._on_system,
            "error": self._on_error,
        }.get(packet.get("type"))
        if handler:
            handler(packet)

    def _on_message(self, packet: dict) -> None:
        msg = packet["message"]
        key = self._store(msg)
        if key == self.current:
            self.msg_layout.addWidget(self._make_row(msg))
            self._scroll_to_bottom()
        elif msg["sender"] != self.me:
            self.unread[key] = self.unread.get(key, 0) + 1
        self._refresh_sidebar()

    def _on_edited(self, packet: dict) -> None:
        for msgs in self.messages.values():
            for msg in msgs:
                if msg.get("id") == packet["id"]:
                    msg["text"], msg["edited"] = packet["text"], True
        self._render_messages()
        self._refresh_sidebar()

    def _on_presence(self, packet: dict) -> None:
        user = packet["user"]
        self.users[user["username"]] = user
        self._update_header()
        self._refresh_sidebar()

    def _on_system(self, packet: dict) -> None:
        note = {"system": True, "text": packet["text"], "ts": packet["ts"], "to": None}
        self.messages[GENERAL].append(note)
        if self.current == GENERAL:
            self.msg_layout.addWidget(self._make_row(note))
            self._scroll_to_bottom()

    def _on_error(self, packet: dict) -> None:
        QMessageBox.warning(self, "ChatWave", packet.get("reason", "Something went wrong."))

    def _on_disconnected(self, reason: str) -> None:
        self.banner.setText(f"⚠️ {reason} Restart the app to reconnect.")
        self.banner.show()
        for w in (self.message_input, self.send_button, self.emoji_button, self.edit_button):
            w.setEnabled(False)

    def closeEvent(self, event) -> None:
        self.client.close()
        super().closeEvent(event)
