# routes/generate.py

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from services.website_generator import generate_html_stream
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/api/generate")
async def generate_website(request: Request):
    try:
        body = await request.json()
        prompt = body.get("prompt", "").strip()
        previous_html = body.get("previous_html")
        previous_prompt = body.get("previous_prompt")

        if not prompt:
            return JSONResponse(status_code=400, content={"error": "Prompt is required"})
            
        stream = await generate_html_stream(prompt, previous_html, previous_prompt)
        return StreamingResponse(stream, media_type="text/event-stream")

    except Exception as e:
        logger.error(f"Generation error: {str(e)}")
        return JSONResponse(status_code=500, content={"error": str(e)})
