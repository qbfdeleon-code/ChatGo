"""Settings shared by the server and the client."""

HOST = "127.0.0.1"          # address the client connects to (the server computer)
PORT = 5555

MAX_MESSAGE_LENGTH = 300    # characters per message
MIN_PASSWORD_LENGTH = 4
MAX_PICTURE_TEXT = 60000    # biggest profile picture (as text) the server accepts

PHONE_WIDTH = 390           # standard phone screen (iPhone 14 size)
PHONE_HEIGHT = 844

AVATARS = ["👤", "😀", "😎", "😂", "🥰", "😈", "🤖", "🐱", "🐶", "🐼"]

GROUP = "group"             # key of the group chat (usernames are used for private chats)
GROUP_NAME = "Group 2 Chat"
