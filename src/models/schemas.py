from pydantic import BaseModel
from typing import List, Optional


class BenefitDetail(BaseModel):
    # Ajuste os campos conforme as colunas reais do portal
    data_referencia: Optional[str] = None
    valor: Optional[str] = None


class Benefit(BaseModel):
    name: str
    totalAmount: str
    details: List[dict]  # Ou List[BenefitDetail] para ser mais rígido
    status: str


class ScraperResponse(BaseModel):
    success: bool
    name: Optional[str] = None
    CPF: Optional[str] = None
    location: Optional[str] = None
    benefits: List[Benefit]
    screenshot: Optional[str] = None
    results: Optional[str] = None


class TelegramUpdate(BaseModel):
    update_id: int
    message: Optional[dict] = None
    callback_query: Optional[dict] = None
