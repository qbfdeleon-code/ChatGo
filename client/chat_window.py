"""Phone-style chat window: chat list page -> conversation page (with a back button)."""
from __future__ import annotations

from datetime import datetime

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QKeySequence, QPixmap, QShortcut
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QMenu, QMessageBox, QPushButton, QScrollArea,
    QStackedWidget, QVBoxLayout, QWidget,
)

from client import theme
from client.images import pixmap_from_b64
from client.network import NetworkClient
from client.phone import place
from client.widgets import (
    AvatarWidget, ClickableAvatar, ConversationTile, EmojiPicker, LogoWidget, MessageBubble,
)
from common.protocol import GENERAL, MAX_MESSAGE_LENGTH, ROOM_TITLE

LIST_PAGE, THREAD_PAGE = 0, 1


def short_time(ts: float) -> str:
    dt, today = datetime.fromtimestamp(ts), datetime.now().date()
    if dt.date() == today:
        return dt.strftime("%I:%M %p").lstrip("0")
    if (today - dt.date()).days == 1:
        return "Yesterday"
    return dt.strftime("%b %d")


class ChatWindow(QWidget):
    def __init__(self, client: NetworkClient, session: dict, slot: int = 0) -> None:
        super().__init__()
        self.client = client
        self.me: str = session["username"]
        self.users: dict[str, dict] = {u["username"]: u for u in session["users"]}
        self.users[self.me] = {"username": self.me, "avatar": session["avatar"],
                               "picture": session.get("picture"), "online": True}

        self.messages: dict[str, list[dict]] = {GENERAL: []}   # conversation key -> messages
        self.unread: dict[str, int] = {}
        self.current = GENERAL            # conversation that Send writes to
        self.viewing: str | None = None   # conversation on screen (None = chat list)
        self.editing_id: int | None = None
        self._pixmaps: dict[str, QPixmap | None] = {}

        for msg in session["history"]:
            self._store(msg)

        self._build_ui()
        place(self, slot)
        self.client.packet_received.connect(self._on_packet)
        self.client.disconnected.connect(self._on_disconnected)
        self.client.start_listening()
        self._refresh_sidebar()

    # ------------------------------------------------------------ small helpers
    @property
    def my_avatar(self) -> str:
        return self.users[self.me]["avatar"]

    def _pixmap(self, username: str) -> QPixmap | None:
        data = self.users.get(username, {}).get("picture")
        if not data:
            return None
        if data not in self._pixmaps:
            self._pixmaps[data] = pixmap_from_b64(data)
        return self._pixmaps[data]

    @staticmethod
    def _discard(widget: QWidget) -> None:
        """Remove a widget from the screen immediately, free it when Qt gets to it."""
        widget.setParent(None)
        widget.deleteLater()

    # --------------------------------------------------------------------- UI
    def _build_ui(self) -> None:
        self.setObjectName("Root")
        self.setWindowTitle(f"ChatGo — {self.my_avatar} {self.me}")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_list_page())
        self.stack.addWidget(self._build_thread_page())
        outer.addWidget(self.stack)

        self.picker = EmojiPicker(self)
        self.picker.emoji_selected.connect(self._insert_emoji)

    def _build_list_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(16, 18, 16, 14)
        lay.setSpacing(12)

        top = QHBoxLayout()
        top.setSpacing(10)
        titles = QVBoxLayout()
        titles.setSpacing(0)
        brand = QLabel("ChatGo")
        brand.setObjectName("Brand")
        self.online_label = QLabel()
        self.online_label.setObjectName("Me")
        titles.addWidget(brand)
        titles.addWidget(self.online_label)
        self.me_avatar = ClickableAvatar(self.my_avatar, theme.ACCENT_DARK, 46,
                                         pixmap=self._pixmap(self.me))
        self.me_avatar.clicked.connect(self._show_profile_menu)
        top.addWidget(LogoWidget(46))
        top.addLayout(titles)
        top.addStretch()
        top.addWidget(self.me_avatar)
        lay.addLayout(top)

        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍 Search conversations...")
        self.search.textChanged.connect(self._refresh_sidebar)
        lay.addWidget(self.search)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        container = QWidget()
        container.setObjectName("TileContainer")
        self.tile_layout = QVBoxLayout(container)
        self.tile_layout.setContentsMargins(0, 0, 0, 0)
        self.tile_layout.setSpacing(8)
        scroll.setWidget(container)
        lay.addWidget(scroll, 1)
        return page

    def _build_thread_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(12, 14, 12, 12)
        lay.setSpacing(10)

        # header: back, avatar, title/status
        header = QFrame()
        header.setObjectName("ChatHeader")
        h = QHBoxLayout(header)
        h.setContentsMargins(8, 8, 14, 8)
        h.setSpacing(8)
        back = QPushButton("‹")
        back.setObjectName("Back")
        back.setCursor(Qt.CursorShape.PointingHandCursor)
        back.clicked.connect(self._show_list)
        self.header_avatar = AvatarWidget("👥", theme.ACCENT_DARK, 44)
        titles = QVBoxLayout()
        titles.setSpacing(0)
        self.header_title = QLabel()
        self.header_title.setObjectName("HeaderTitle")
        self.header_status = QLabel()
        self.header_status.setObjectName("HeaderStatus")
        titles.addWidget(self.header_title)
        titles.addWidget(self.header_status)
        h.addWidget(back)
        h.addWidget(self.header_avatar)
        h.addLayout(titles)
        h.addStretch()
        lay.addWidget(header)

        self.banner = QLabel("")
        self.banner.setObjectName("Banner")
        self.banner.setWordWrap(True)
        self.banner.hide()
        lay.addWidget(self.banner)

        # message area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.msg_area = QWidget()
        self.msg_area.setObjectName("MessageArea")
        self.msg_layout = QVBoxLayout(self.msg_area)
        self.msg_layout.setContentsMargins(4, 6, 4, 6)
        self.msg_layout.setSpacing(8)
        self.scroll.setWidget(self.msg_area)
        lay.addWidget(self.scroll, 1)

        # input row: emoji button, text box, send button
        row = QHBoxLayout()
        row.setSpacing(8)
        self.emoji_button = QPushButton("😊")
        self.emoji_button.setObjectName("EmojiToggle")
        self.emoji_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.emoji_button.clicked.connect(self._show_emoji_picker)
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Type a message...")
        self.message_input.textChanged.connect(self._on_text_changed)
        self.message_input.returnPressed.connect(self._send)             # Enter to send
        self.send_button = QPushButton("Send")
        self.send_button.setObjectName("Primary")
        self.send_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_button.clicked.connect(self._send)
        row.addWidget(self.emoji_button)
        row.addWidget(self.message_input, 1)
        row.addWidget(self.send_button)
        lay.addLayout(row)

        # edit row + character counter
        tools = QHBoxLayout()
        self.edit_button = QPushButton("✏️ Edit last message")
        self.edit_button.setObjectName("EditButton")
        self.edit_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.edit_button.clicked.connect(self._start_edit)
        self.cancel_edit_button = QPushButton("✖ Cancel")
        self.cancel_edit_button.setObjectName("Ghost")
        self.cancel_edit_button.clicked.connect(self._cancel_edit)
        self.cancel_edit_button.hide()
        self.counter = QLabel(f"0/{MAX_MESSAGE_LENGTH}")
        self.counter.setObjectName("Counter")
        tools.addWidget(self.edit_button)
        tools.addWidget(self.cancel_edit_button)
        tools.addStretch()
        tools.addWidget(self.counter)
        lay.addLayout(tools)

        esc = QShortcut(QKeySequence("Esc"), self.message_input)
        esc.setContext(Qt.ShortcutContext.WidgetShortcut)
        esc.activated.connect(self._cancel_edit)
        return page

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

    # ------------------------------------------------------------- chat list
    def _refresh_sidebar(self) -> None:
        while self.tile_layout.count():
            item = self.tile_layout.takeAt(0)
            if item.widget():
                self._discard(item.widget())

        online = sum(1 for u in self.users.values() if u["online"])
        self.online_label.setText(f"{online} online")

        query = self.search.text().strip().lower()
        others = sorted((u for n, u in self.users.items() if n != self.me),
                        key=lambda u: (not u["online"], u["username"].lower()))
        entries = [(GENERAL, ROOM_TITLE, "👥", theme.ACCENT_DARK, None, None)]
        entries += [(u["username"], u["username"], u["avatar"], theme.color_for(u["username"]),
                     u["online"], self._pixmap(u["username"])) for u in others]

        for key, title, glyph, color, is_online, pixmap in entries:
            if query and query not in title.lower():
                continue
            last = self._last_message(key)
            preview, when = "No messages yet", ""
            if last:
                who = "You" if last["sender"] == self.me else last["sender"]
                if key == GENERAL or who == "You":
                    preview = f"{who}: {last['text']}"
                else:
                    preview = last["text"]
                when = short_time(last["ts"])
            tile = ConversationTile(key, title, glyph, color, preview, when,
                                    self.unread.get(key, 0), is_online, pixmap)
            tile.clicked.connect(self._open_conversation)
            self.tile_layout.addWidget(tile)
        self.tile_layout.addStretch()

    def _show_profile_menu(self) -> None:
        menu = QMenu(self)
        menu.addAction(f"{self.my_avatar}  {self.me}").setEnabled(False)
        menu.addSeparator()
        menu.addAction("Log out", self.close)
        menu.exec(self.me_avatar.mapToGlobal(self.me_avatar.rect().bottomRight()))

    # ----------------------------------------------------------- conversation
    def _open_conversation(self, key: str) -> None:
        self._cancel_edit()
        self.current = self.viewing = key
        self.unread[key] = 0
        self._update_header()
        self._render_messages()
        self.stack.setCurrentIndex(THREAD_PAGE)
        self.message_input.setFocus()
        self._refresh_sidebar()

    def _show_list(self) -> None:
        self._cancel_edit()
        self.picker.hide()
        self.viewing = None
        self.stack.setCurrentIndex(LIST_PAGE)
        self._refresh_sidebar()

    def _update_header(self) -> None:
        if self.current == GENERAL:
            online = sum(1 for u in self.users.values() if u["online"])
            self.header_avatar.set_avatar("👥", theme.ACCENT_DARK)
            self.header_title.setText(ROOM_TITLE)
            self.header_status.setText(f"{online} online")
        else:
            user = self.users.get(self.current, {"avatar": "👤", "online": False})
            self.header_avatar.set_avatar(user["avatar"], theme.color_for(self.current), None,
                                          self._pixmap(self.current))
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
        bubble = MessageBubble(msg, own, self._pixmap(msg["sender"]), max_width=310)
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

    # ---------------------------------------------------------------- sending
    def _on_text_changed(self, text: str) -> None:
        if len(text) > MAX_MESSAGE_LENGTH:            # also catches long pastes
            self.message_input.setText(text[:MAX_MESSAGE_LENGTH])
            return
        self.counter.setText(f"{len(text)}/{MAX_MESSAGE_LENGTH}")
        warn = len(text) >= MAX_MESSAGE_LENGTH * 0.9
        if self.counter.property("warn") != warn:
            self.counter.setProperty("warn", warn)
            self.counter.style().unpolish(self.counter)
            self.counter.style().polish(self.counter)

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

    # ---------------------------------------------------------------- editing
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

    # -------------------------------------------------------- incoming packets
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
        if key == self.viewing:
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
        if self.viewing is not None:
            self._render_messages()
        self._refresh_sidebar()

    def _on_presence(self, packet: dict) -> None:
        user = packet["user"]
        self.users[user["username"]] = user
        if self.viewing is not None:
            self._update_header()
        self._refresh_sidebar()

    def _on_system(self, packet: dict) -> None:
        note = {"system": True, "text": packet["text"], "ts": packet["ts"], "to": None}
        self.messages[GENERAL].append(note)
        if self.viewing == GENERAL:
            self.msg_layout.addWidget(self._make_row(note))
            self._scroll_to_bottom()

    def _on_error(self, packet: dict) -> None:
        QMessageBox.warning(self, "ChatGo", packet.get("reason", "Something went wrong."))

    def _on_disconnected(self, reason: str) -> None:
        self.banner.setText(f"⚠️ {reason} Restart the app to reconnect.")
        self.banner.show()
        for w in (self.message_input, self.send_button, self.emoji_button, self.edit_button):
            w.setEnabled(False)

    def closeEvent(self, event) -> None:
        self.client.close()
        super().closeEvent(event)
