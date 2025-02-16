from telethon import TelegramClient

from provider.telegram.model.protocols import Dialog, TelegramEvent


class Telegram:
    def __init__(self, session_name: str, api_id: str, api_hash: str):
        self.client = TelegramClient(session_name, api_id, api_hash)

    async def start(self) -> None:
        await self.client.start()

    async def run_until_disconnected(self) -> None:
        await self.client.run_until_disconnected()

    def add_event_handler(self, callback: callable, event: TelegramEvent) -> None:
        self.client.add_event_handler(callback, event)

    async def get_chat_id(self, chat_name: str) -> int:
        async for dialog in self.client.iter_dialogs():
            dialog: Dialog
            if dialog.name == chat_name:
                return dialog.id
