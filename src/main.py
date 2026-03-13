from src.scraper.browser import BrowserManager
from src.scraper.scraper import scrape
from src.services.telegram_captcha import TelegramCaptchaManager
from src.models.schemas import ScraperResponse, TelegramUpdate
from fastapi import FastAPI, Request, Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader
from contextlib import asynccontextmanager
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import asyncio
import os


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
load_dotenv()
API_KEY = os.getenv("API_KEY")
api_key_header = APIKeyHeader(name="X-API-KEY", auto_error=False)

if not API_KEY:
    raise ValueError("API Key não encontrada no env!")


async def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header == API_KEY:
        return api_key_header
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Acesso negado: Chave de API inválida",
    )


@app.get(
    "/pessoa",
    summary="Consulta beneficiário",
    description="Realiza a busca no Portal da Transparência e resolve captchas via Telegram.",
    response_model=ScraperResponse,
)  # ScraperResponse é sua classe Pydantic)
async def pessoa(query: str, api_key: str = Security(get_api_key)):
    """
    Endpoint utilizado para realizar a busca no Portal da Transparência
    Recebe a query e a chave de api na url e no header, respectivamente.
    """

    try:
        browser_manager = app.state.browser_manager
        captcha_manager = app.state.captcha_manager
        result = await asyncio.wait_for(
            scrape(browser_manager, captcha_manager, query), timeout=120
        )

        return JSONResponse(content=result)
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)},
        )

    except asyncio.TimeoutError:
        return JSONResponse(
            status_code=408,
            content={"error": "Tempo limite excedido."},
        )
    except Exception as e:
        print(e)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Erro inesperado ao processar o scraping. Verifique os logs"
            },
        )


@app.post(
    "/telegram-webhook",
    tags=["Webhooks"],
    summary="Recebe resposta do Captcha",
    response_model=TelegramUpdate,
)
async def telegram_webhook(request: Request):
    """
    Endpoint utilizado pelo Telegram para notificar a resolução do captcha.
    O CaptchaManager processa o 'update' e libera o Lock do scraper correspondente.
    """
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
