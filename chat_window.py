"""The main window: a chat list page and a conversation page (like a phone app)."""
from PyQt6.QtCore import QSize, Qt, QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMenu,
    QMessageBox, QPushButton, QScrollArea, QStackedWidget, QVBoxLayout, QWidget,
)

import config
import styles
from emoji_picker import EmojiPicker
from helpers import (
    format_time, make_avatar, make_logo, place_window, short_time, text_to_pixmap,
    wrap_long_words,
)

LIST_PAGE = 0
CHAT_PAGE = 1


class ChatWindow(QWidget):
    def __init__(self, connection, session, slot=0):
        super().__init__()
        self.setObjectName("screen")
        self.connection = connection
        self.me = session["username"]
        self.setWindowTitle(f"ChatGo - {self.me}")
        self.setWindowIcon(QIcon(make_logo(64)))
        place_window(self, slot)

        # users: username -> {"username", "avatar", "picture", "online"}
        self.users = {u["username"]: u for u in session["users"]}
        self.users[self.me] = {"username": self.me, "avatar": session["avatar"],
                               "picture": session["picture"], "online": True}

        self.messages = {config.GROUP: []}   # conversation key -> list of messages
        self.unread = {}                     # conversation key -> unread count
        self.current = config.GROUP          # conversation that "Send" writes to
        self.viewing = None                  # conversation on screen (None = chat list)
        self.editing_id = None               # id of the message being edited

        for message in session["history"]:
            self.add_to_conversation(message)

        self.build_ui()
        self.connection.packet_received.connect(self.on_packet)
        self.connection.disconnected.connect(self.on_disconnected)
        self.connection.start_listening()
        self.refresh_list()

    # ----------------------------------------------------------- building
    def build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.pages = QStackedWidget()
        self.pages.addWidget(self.build_list_page())
        self.pages.addWidget(self.build_chat_page())
        layout.addWidget(self.pages)

        self.picker = EmojiPicker(self)
        self.picker.emoji_clicked.connect(self.add_emoji)

    def build_list_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 18, 16, 14)
        layout.setSpacing(12)

        # top bar: logo, app name, my avatar
        top = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(make_logo(46))
        names = QVBoxLayout()
        names.setSpacing(0)
        app_name = QLabel("ChatGo")
        app_name.setObjectName("appName")
        self.online_label = QLabel()
        self.online_label.setObjectName("small")
        names.addWidget(app_name)
        names.addWidget(self.online_label)

        self.my_avatar_button = QPushButton()
        self.my_avatar_button.setObjectName("avatarButton")
        self.my_avatar_button.setIcon(QIcon(self.avatar_of(self.me, 46)))
        self.my_avatar_button.setIconSize(QSize(46, 46))
        self.my_avatar_button.setFixedSize(50, 50)
        self.my_avatar_button.clicked.connect(self.show_profile_menu)

        top.addWidget(logo)
        top.addLayout(names)
        top.addStretch()
        top.addWidget(self.my_avatar_button)
        layout.addLayout(top)

        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍 Search conversations...")
        self.search.textChanged.connect(self.refresh_list)
        layout.addWidget(self.search)

        self.chat_list = QListWidget()
        self.chat_list.setIconSize(QSize(46, 46))
        self.chat_list.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.chat_list.itemClicked.connect(self.on_list_clicked)
        layout.addWidget(self.chat_list)
        return page

    def build_chat_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 14, 12, 12)
        layout.setSpacing(10)

        # green header: back button, avatar, name, status
        header = QFrame()
        header.setObjectName("header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 8, 14, 8)
        back_button = QPushButton("‹")
        back_button.setObjectName("back")
        back_button.clicked.connect(self.show_list)
        self.header_avatar = QLabel()
        self.header_title = QLabel()
        self.header_title.setObjectName("headerTitle")
        self.header_status = QLabel()
        self.header_status.setObjectName("headerStatus")
        titles = QVBoxLayout()
        titles.setSpacing(0)
        titles.addWidget(self.header_title)
        titles.addWidget(self.header_status)
        header_layout.addWidget(back_button)
        header_layout.addWidget(self.header_avatar)
        header_layout.addLayout(titles)
        header_layout.addStretch()
        layout.addWidget(header)

        self.banner = QLabel("")
        self.banner.setObjectName("banner")
        self.banner.setWordWrap(True)
        self.banner.hide()
        layout.addWidget(self.banner)

        # scrollable area with the message bubbles
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        area = QWidget()
        area.setObjectName("messages")
        self.message_layout = QVBoxLayout(area)
        self.message_layout.setSpacing(8)
        self.scroll.setWidget(area)
        layout.addWidget(self.scroll)

        # bottom row: emoji button, text box, send button
        row = QHBoxLayout()
        self.emoji_button = QPushButton("😊")
        self.emoji_button.setObjectName("emojiButton")
        self.emoji_button.clicked.connect(lambda: self.picker.show_above(self.emoji_button))
        self.message_box = QLineEdit()
        self.message_box.setPlaceholderText("Type a message...")
        self.message_box.textChanged.connect(self.on_text_changed)
        self.message_box.returnPressed.connect(self.send)        # Enter sends too
        self.send_button = QPushButton("Send")
        self.send_button.setObjectName("primary")
        self.send_button.clicked.connect(self.send)
        row.addWidget(self.emoji_button)
        row.addWidget(self.message_box)
        row.addWidget(self.send_button)
        layout.addLayout(row)

        # edit button and character counter
        tools = QHBoxLayout()
        self.edit_button = QPushButton("✏️ Edit last message")
        self.edit_button.setObjectName("editButton")
        self.edit_button.clicked.connect(self.start_edit)
        self.cancel_button = QPushButton("✖ Cancel")
        self.cancel_button.setObjectName("ghost")
        self.cancel_button.clicked.connect(self.cancel_edit)
        self.cancel_button.hide()
        self.counter = QLabel(f"0/{config.MAX_MESSAGE_LENGTH}")
        self.counter.setObjectName("counter")
        tools.addWidget(self.edit_button)
        tools.addWidget(self.cancel_button)
        tools.addStretch()
        tools.addWidget(self.counter)
        layout.addLayout(tools)
        return page

    # ------------------------------------------------------------ helpers
    def avatar_of(self, username, size):
        user = self.users.get(username, {"avatar": "👤", "picture": None})
        return make_avatar(user["avatar"], text_to_pixmap(user["picture"]), size,
                           styles.color_for(username))

    def conversation_key(self, message):
        """Which conversation a message belongs to."""
        if message["to"] is None:
            return config.GROUP
        return message["to"] if message["sender"] == self.me else message["sender"]

    def add_to_conversation(self, message):
        key = self.conversation_key(message)
        self.messages.setdefault(key, []).append(message)
        return key

    def last_message(self, key):
        for message in reversed(self.messages.get(key, [])):
            if not message.get("notice"):
                return message
        return None

    def clear_layout(self, layout):
        while layout.count():
            widget = layout.takeAt(0).widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    # ---------------------------------------------------------- chat list
    def refresh_list(self):
        online = sum(1 for u in self.users.values() if u["online"])
        self.online_label.setText(f"{online} online")

        query = self.search.text().strip().lower()
        others = sorted((u for name, u in self.users.items() if name != self.me),
                        key=lambda u: (not u["online"], u["username"].lower()))
        conversations = [(config.GROUP, config.GROUP_NAME)]
        conversations += [(u["username"], u["username"]) for u in others]

        self.chat_list.clear()
        for key, title in conversations:
            if query and query not in title.lower():
                continue

            last = self.last_message(key)
            preview, when = "No messages yet", ""
            if last:
                who = "You" if last["sender"] == self.me else last["sender"]
                preview = f"{who}: {last['text']}" if key == config.GROUP or who == "You" \
                    else last["text"]
                if len(preview) > 32:
                    preview = preview[:31] + "…"
                when = short_time(last["time"])

            text = f"{title}    {when}\n{preview}"
            if self.unread.get(key):
                text += f"    🔴 {self.unread[key]}"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, key)
            if key == config.GROUP:
                icon = make_avatar("👥", None, 46, styles.DARK_GREEN)
            else:
                icon = self.avatar_of(key, 46)
            item.setIcon(QIcon(icon))
            item.setSizeHint(QSize(0, 70))
            self.chat_list.addItem(item)

    def on_list_clicked(self, item):
        self.open_conversation(item.data(Qt.ItemDataRole.UserRole))

    def show_profile_menu(self):
        menu = QMenu(self)
        menu.addAction(f"Signed in as {self.me}").setEnabled(False)
        menu.addSeparator()
        menu.addAction("Log out", self.close)
        menu.exec(self.my_avatar_button.mapToGlobal(self.my_avatar_button.rect().bottomRight()))

    # ------------------------------------------------------- conversation
    def open_conversation(self, key):
        self.cancel_edit()
        self.current = key
        self.viewing = key
        self.unread[key] = 0
        self.update_header()
        self.show_messages()
        self.pages.setCurrentIndex(CHAT_PAGE)
        self.message_box.setFocus()

    def show_list(self):
        self.cancel_edit()
        self.picker.hide()
        self.viewing = None
        self.pages.setCurrentIndex(LIST_PAGE)
        self.refresh_list()

    def update_header(self):
        if self.current == config.GROUP:
            online = sum(1 for u in self.users.values() if u["online"])
            self.header_avatar.setPixmap(make_avatar("👥", None, 44, styles.DARK_GREEN))
            self.header_title.setText(config.GROUP_NAME)
            self.header_status.setText(f"{online} online")
        else:
            user = self.users.get(self.current, {"online": False})
            self.header_avatar.setPixmap(self.avatar_of(self.current, 44))
            self.header_title.setText(self.current)
            self.header_status.setText("● online" if user["online"] else "offline")

    def show_messages(self):
        self.clear_layout(self.message_layout)
        self.message_layout.addStretch()           # pushes the messages to the bottom
        for message in self.messages.get(self.current, []):
            self.message_layout.addWidget(self.make_row(message))
        self.scroll_down()

    def make_row(self, message):
        """One line of the conversation: a notice or a message bubble."""
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)

        if message.get("notice"):
            label = QLabel(message["text"])
            label.setObjectName("notice")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            row_layout.addWidget(label)
            return row

        mine = message["sender"] == self.me
        bubble = QFrame()
        bubble.setObjectName("mine" if mine else "theirs")
        bubble.setMaximumWidth(310)
        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(12, 8, 12, 8)
        bubble_layout.setSpacing(4)

        # first line: avatar, username and date/time
        info_row = QHBoxLayout()
        info_row.setSpacing(6)
        picture = QLabel()
        picture.setPixmap(self.avatar_of(message["sender"], 22))
        info = QLabel(f"{message['sender']}  [{format_time(message['time'])}]")
        info.setObjectName("bubbleInfo")
        info.setWordWrap(True)
        info_row.addWidget(picture, 0, Qt.AlignmentFlag.AlignTop)
        info_row.addWidget(info, 1)
        bubble_layout.addLayout(info_row)

        text = QLabel(wrap_long_words(message["text"]))
        text.setWordWrap(True)
        text.setTextFormat(Qt.TextFormat.PlainText)
        bubble_layout.addWidget(text)
        if message["edited"]:
            edited = QLabel("(edited)")
            edited.setObjectName("bubbleInfo")
            edited.setAlignment(Qt.AlignmentFlag.AlignRight)
            bubble_layout.addWidget(edited)

        if mine:
            row_layout.addStretch()
            row_layout.addWidget(bubble)
        else:
            row_layout.addWidget(bubble)
            row_layout.addStretch()
        return row

    def scroll_down(self):
        bar = self.scroll.verticalScrollBar()
        QTimer.singleShot(40, lambda: bar.setValue(bar.maximum()))

    # ------------------------------------------------------------ sending
    def on_text_changed(self, text):
        """Keep the message under the limit and update the 0/300 counter."""
        limit = config.MAX_MESSAGE_LENGTH
        if len(text) > limit:                      # also cuts text that was pasted
            self.message_box.setText(text[:limit])
            return
        self.counter.setText(f"{len(text)}/{limit}")
        self.counter.setStyleSheet(f"color: {styles.PINK};" if len(text) >= limit * 0.9 else "")

    def send(self):
        text = self.message_box.text().strip()
        if text == "":
            return
        if self.editing_id is not None:
            packet = {"type": "edit", "id": self.editing_id, "text": text}
        else:
            to = None if self.current == config.GROUP else self.current
            packet = {"type": "message", "to": to, "text": text}

        if not self.connection.send(packet):
            QMessageBox.warning(self, "Error", "Message could not be sent.")
            return
        self.message_box.clear()
        self.cancel_edit()

    def add_emoji(self, emoji):
        self.message_box.insert(emoji)
        self.message_box.setFocus()

    # ------------------------------------------------------------ editing
    def start_edit(self):
        mine = [m for m in self.messages.get(self.current, [])
                if not m.get("notice") and m["sender"] == self.me]
        if not mine:
            QMessageBox.information(self, "Edit message",
                                    "You have no message to edit in this chat yet.")
            return
        self.editing_id = mine[-1]["id"]
        self.message_box.setText(mine[-1]["text"])
        self.message_box.setPlaceholderText("Editing your last message...")
        self.send_button.setText("Save")
        self.cancel_button.show()
        self.message_box.setFocus()

    def cancel_edit(self):
        if self.editing_id is None:
            return
        self.editing_id = None
        self.message_box.clear()
        self.message_box.setPlaceholderText("Type a message...")
        self.send_button.setText("Send")
        self.cancel_button.hide()

    # ---------------------------------------------------- server packets
    def on_packet(self, packet):
        kind = packet.get("type")
        if kind == "message":
            self.on_message(packet["message"])
        elif kind == "edited":
            self.on_edited(packet)
        elif kind == "status":
            self.users[packet["user"]["username"]] = packet["user"]
            if self.viewing is not None:
                self.update_header()
            self.refresh_list()
        elif kind == "notice":
            self.on_notice(packet)
        elif kind == "error":
            QMessageBox.warning(self, "ChatGo", packet.get("reason", "Something went wrong."))

    def on_message(self, message):
        key = self.add_to_conversation(message)
        if key == self.viewing:
            self.message_layout.addWidget(self.make_row(message))
            self.scroll_down()
        elif message["sender"] != self.me:
            self.unread[key] = self.unread.get(key, 0) + 1
        self.refresh_list()

    def on_edited(self, packet):
        for conversation in self.messages.values():
            for message in conversation:
                if message.get("id") == packet["id"]:
                    message["text"] = packet["text"]
                    message["edited"] = True
        if self.viewing is not None:
            self.show_messages()
        self.refresh_list()

    def on_notice(self, packet):
        notice = {"notice": True, "text": packet["text"]}
        self.messages[config.GROUP].append(notice)
        if self.viewing == config.GROUP:
            self.message_layout.addWidget(self.make_row(notice))
            self.scroll_down()

    def on_disconnected(self):
        self.banner.setText("⚠️ Connection to the server was lost. Restart the app to reconnect.")
        self.banner.show()
        for widget in (self.message_box, self.send_button, self.emoji_button, self.edit_button):
            widget.setEnabled(False)

    def closeEvent(self, event):
        self.connection.close()
        event.accept()
