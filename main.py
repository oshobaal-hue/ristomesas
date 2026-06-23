"""
Railway TTS Service — Edge TTS (Microsoft)
Genera audio MP3 con voz neural en español mexicano.

Uso:
    POST /tts
    Body: { "text": "Texto a convertir", "voice": "es-MX-DaliaNeural" }
    Response: audio/mpeg

Despliegue en Railway:
    1. Sube esta carpeta a GitHub
    2. Conéctala a Railway como servicio
    3. Railway detecta automáticamente el Dockerfile
"""

import asyncio
import io
import logging
import os
import tempfile
from typing import Optional

import edge_tts
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tts-service")

app = FastAPI(title="Edge TTS Service", version="1.0.0")


class TTSRequest(BaseModel):
    text: str
    voice: str = "es-MX-DaliaNeural"
    rate: str = "+0%"
    pitch: str = "+0Hz"


class HealthResponse(BaseModel):
    status: str
    version: str
    default_voice: str


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="ok",
        version="1.0.0",
        default_voice="es-MX-DaliaNeural",
    )


@app.post("/tts")
async def text_to_speech(request: TTSRequest):
    """Convierte texto a audio MP3 usando Edge TTS."""
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="El texto no puede estar vacío")

    voice = request.voice or "es-MX-DaliaNeural"
    rate = request.rate or "+0%"
    pitch = request.pitch or "+0Hz"

    logger.info(f"Generando TTS: voice={voice}, text_len={len(text)}, rate={rate}, pitch={pitch}")

    try:
        communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
        audio_data = b""

        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]

        if not audio_data:
            raise HTTPException(status_code=500, detail="No se generó audio")

        logger.info(f"Audio generado: {len(audio_data)} bytes")

        return Response(
            content=audio_data,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": f'attachment; filename="tts-{voice}.mp3"',
                "X-Text-Length": str(len(text)),
                "X-Audio-Size": str(len(audio_data)),
            },
        )

    except Exception as e:
        logger.error(f"Error generando TTS: {e}")
        raise HTTPException(status_code=500, detail=f"Error generando audio: {str(e)}")


@app.get("/tts")
async def text_to_speech_get(
    text: str = Query(..., description="Texto a convertir"),
    voice: str = Query("es-MX-DaliaNeural", description="Voz a usar"),
    rate: str = Query("+0%", description="Velocidad"),
    pitch: str = Query("+0Hz", description="Tono"),
):
    """Versión GET del TTS para pruebas rápidas."""
    request = TTSRequest(text=text, voice=voice, rate=rate, pitch=pitch)
    return await text_to_speech(request)


@app.get("/voices")
async def list_voices():
    """Lista las voces disponibles en español."""
    try:
        voices = await edge_tts.list_voices()
        spanish_voices = [
            {
                "name": v["ShortName"],
                "locale": v["Locale"],
                "gender": v["Gender"],
                "description": v.get("LocalName", v["ShortName"]),
            }
            for v in voices
            if v["Locale"].startswith("es")
        ]
        return {"voices": spanish_voices}
    except Exception as e:
        logger.error(f"Error listando voces: {e}")
        return {"voices": [], "error": str(e)}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
