import asyncio
import math
import os
import pathlib
import re
import time
import typing

import click
from loguru import logger
from telethon import TelegramClient
from telethon.sessions import MemorySession

GIGABYTE_BYTES = 1e9
# Current telegram limit is 2GB. Is better to make custom chunked reader, but undercover,
# telethon just reads out whole reader to memory. So to prevent memory overflow I set
# 300 MB
TELEGRAM_BYTES_LIMIT = int(GIGABYTE_BYTES * 0.300)
CALM_DELAY = 60 * 15  # 15 minutes
# Access hash extracted from Telegram Desktop
API_ID = 2040
API_HASH = "b18441a1ff607e10a989891a5462e627"


class FileWatcher:
    def __init__(
        self,
        path: str,
        calm_delay: int,
        filename_regex: str,
        chat_id: str,
        bot_token: str,
    ):
        self.path = pathlib.Path(path)
        self.calm_delay = calm_delay
        self.filename_regex = re.compile(filename_regex)
        self.chat_id = chat_id
        self.bot_token = bot_token

        self.client: typing.Optional[TelegramClient] = None

    async def start(self):
        self.client = TelegramClient(
            MemorySession(), api_id=API_ID, api_hash=API_HASH
        )
        await self.client.connect()
        await self.client.sign_in(bot_token=self.bot_token)
        logger.info("Signed in!")

        while True:
            try:
                await self._upload_calm_files()
            except Exception:
                logger.exception("Exception during checking files")
            await asyncio.sleep(30)

    def _get_calm_files(self) -> typing.Generator[pathlib.Path, None, None]:
        """Finds files which have not been modified for N seconds"""
        for filepath in self.path.iterdir():
            if not filepath.is_file():
                continue

            if not self.filename_regex.match(filepath.name):
                continue

            modified_seconds_ago = time.time() - os.path.getmtime(filepath)
            if modified_seconds_ago > self.calm_delay:
                yield filepath

    async def _upload_calm_files(self):
        for filepath in self._get_calm_files():
            await self._upload_file(filepath)
            filepath.unlink()

    async def _upload_file(self, path: pathlib.Path):
        file_size = self.get_file_size(path)
        gigabytes_filesize = file_size / GIGABYTE_BYTES

        log_str = f"Uploading file: {path.name} ({gigabytes_filesize:.2f} GB)"
        logger.info(log_str)
        msg = await self.client.send_message(self.chat_id, log_str)

        if file_size > TELEGRAM_BYTES_LIMIT:
            await self.upload_file_chunked(path)
        else:
            await self.client.send_file(
                self.chat_id, str(path), caption=path.name
            )

        await self.client.delete_messages(self.chat_id, [msg.id])

    @staticmethod
    def get_file_size(filepath: pathlib.Path):
        file_size = filepath.stat().st_size
        return file_size

    async def upload_file_chunked(self, path: pathlib.Path):
        """Sends chunks of file to telegram"""
        file_size = self.get_file_size(path)
        chunks_count = math.ceil(file_size / TELEGRAM_BYTES_LIMIT)
        with open(str(path), "rb") as file:
            for i in range(chunks_count):
                data = file.read(TELEGRAM_BYTES_LIMIT)

                chunk_name = f"{path.name}: {i + 1} / {chunks_count}"
                logger.info("Uploading chunk " + chunk_name)
                file_id = await self.client.upload_file(
                    data, file_name=f"{path.name}.{i}"
                )
                await self.client.send_file(
                    self.chat_id, file_id, caption=chunk_name
                )


@click.command()
@click.option(
    "--path", required=True, envvar="SYNC_PATH", type=click.Path(exists=True)
)
@click.option("--filename-regex", required=True, envvar="SYNC_FILENAME_REGEX")
@click.option("--chat-id", required=True, envvar="SYNC_CHAT", type=int)
@click.option("--bot-token", required=True, envvar="SYNC_BOT_TOKEN")
def main(path, filename_regex, chat_id, bot_token):
    watcher = FileWatcher(path, CALM_DELAY, filename_regex, chat_id, bot_token)
    asyncio.run(watcher.start())


if __name__ == "__main__":
    asyncio.run(main())
