from typing import Protocol


class TelegramEvent(Protocol):
    raw_text: str


class Dialog(Protocol):
    name: str
    id: int
