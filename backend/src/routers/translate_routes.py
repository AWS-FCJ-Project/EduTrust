from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import ValidationError
from src.auth.dependencies import get_current_user
from src.schemas.translate_schema import TranslateRequest, TranslateResponse
from src.translate_service.translate import TranslateService

router = APIRouter(prefix="/translate", tags=["Translate"])


@lru_cache
def get_translate_service() -> TranslateService:
    return TranslateService()


@router.post("/text", response_model=TranslateResponse)
async def translate(
    request: TranslateRequest,
    email: Annotated[str, Depends(get_current_user)],
    translate_service: Annotated[TranslateService, Depends(get_translate_service)],
) -> TranslateResponse:
    """Translate text to the specified language."""
    if not request.language or not request.text:
        raise HTTPException(
            status_code=400, detail="Missing required target language or text"
        )

    try:
        translated = await translate_service.translate_text(
            text=request.text, language=request.language
        )
        return TranslateResponse(text=translated)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors()) from e


@router.post("/file", response_model=TranslateResponse)
async def translate_file_endpoint(
    language: Annotated[str, Query(..., description="Target language")],
    file: Annotated[UploadFile, File(..., description="File to translate")],
    email: Annotated[str, Depends(get_current_user)],
    translate_service: Annotated[TranslateService, Depends(get_translate_service)],
) -> TranslateResponse:
    """Translate a file (PDF, DOCX, TXT, images) to the specified language."""
    try:
        translated_text = await translate_service.translate_file(
            file=file, language=language
        )
        return TranslateResponse(text=translated_text)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
