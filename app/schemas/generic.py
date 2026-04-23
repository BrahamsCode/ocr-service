from pydantic import BaseModel

from app.schemas.common import OcrMeta


class GenericTextResponse(BaseModel):
    text: str
    pages: list[str]
    meta: OcrMeta
