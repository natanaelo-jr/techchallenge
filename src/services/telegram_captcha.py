import asyncio
import httpx
import uuid
from dotenv import load_dotenv
import os


class TelegramCaptchaManager:
    def __init__(self):
        load_dotenv()
        self.token = os.getenv("TELEGRAM_TOKEN")
        if not self.token:
            raise ValueError(
                "No telegram token key found. Set the token environment variable."
            )

        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        if not self.chat_id:
            raise ValueError("No Chat Id detected. Set the chat id enviroment variable")

        # Guarda o estado das requisições simultâneas
        self._active_captchas = {}

    async def send_captcha_and_wait(self, screenshot_bytes: bytes) -> str:
        print("Called captcha resolver")
        # Chamado pelo scraper. Envia a foto e pausa esperando a resposta.
        session_id = str(uuid.uuid4())[:6]

        self._active_captchas[session_id] = {"event": asyncio.Event(), "response": ""}

        url = f"https://api.telegram.org/bot{self.token}/sendPhoto"
        files = {"photo": ("captcha.png", screenshot_bytes)}
        data = {
            "chat_id": self.chat_id,
            "caption": f"ID: {session_id}\nResponda com os números.",
        }

        async with httpx.AsyncClient() as client:
            await client.post(url, data=data, files=files)

        # Aguarda a resolução
        await self._active_captchas[session_id]["event"].wait()

        response = self._active_captchas[session_id]["response"]
        del self._active_captchas[session_id]

        return response

    def process_webhook_reply(self, session_id: str, text: str) -> bool:
        # Chamado pelo endpoint do FastAPI quando o Telegram avisa de uma mensagem.
        if session_id in self._active_captchas:
            self._active_captchas[session_id]["response"] = text
            self._active_captchas[session_id]["event"].set()
            return True
