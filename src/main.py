from src.scraper.browser import BrowserManager
from src.scraper.scraper import scrape
from src.services.telegram_captcha import TelegramCaptchaManager
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from fastapi.responses import JSONResponse
import asyncio


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Constructor (Startup) ---
    manager = BrowserManager()
    await manager.start()
    captcha = TelegramCaptchaManager()

    app.state.browser_manager = manager
    app.state.captcha_manager = captcha

    yield

    # --- Destructor (Shutdown) ---
    await manager.close()


app = FastAPI(lifespan=lifespan)


@app.get("/pessoa")
async def pessoa(query: str):
    try:
        browser_manager = app.state.browser_manager
        captcha_manager = app.state.captcha_manager
        result = await asyncio.wait_for(
            scrape(browser_manager, captcha_manager, query), timeout=120
        )

        return JSONResponse(content=result)

    except asyncio.TimeoutError:
        return JSONResponse(
            status_code=408,
            content={"error": "Tempo limite excedido."},
        )


@app.post("/telegram-webhook")
async def telegram_webhook(request: Request):
    # Rota passiva. Apenas recebe o POST do Telegram e avisa o Manager.
    update = await request.json()

    captcha_manager: TelegramCaptchaManager = app.state.captcha_manager

    try:
        message = update.get("message", {})
        texto = message.get("text", "")

        # Verifica se é um reply e extrai o ID
        if "reply_to_message" in message and "caption" in message["reply_to_message"]:
            legenda = message["reply_to_message"]["caption"]
            if "ID: " in legenda:
                session_id = legenda.split("ID: ")[1].split("\n")[0].strip()
                # Passa a bola pro serviço resolver
                captcha_manager.process_webhook_reply(session_id, texto)

    except Exception as e:
        print(f"Erro ao processar webhook: {e}")

    return {"ok": True}
