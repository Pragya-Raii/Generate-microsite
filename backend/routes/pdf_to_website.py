from fastapi import APIRouter, UploadFile, File, HTTPException, status
from fastapi.responses import StreamingResponse
import logging
import tempfile
import os
from schemas.token import DescriptionRequest
from services.pdf_to_website import analyze_pdf
from services.image_to_website import generate_html_code

router = APIRouter(tags=["pdf-to-website"])
logger = logging.getLogger(__name__)

ALLOWED_PDF_TYPES = {"application/pdf"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB

@router.post("/api/analyze-pdf")
async def analyze_uploaded_pdf(file: UploadFile = File(...)):
    """
    Analyze an uploaded PDF and return a description.
    """
    try:
        if file.content_type not in ALLOWED_PDF_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type. Only PDF is allowed."
            )
        
        file_content = await file.read()
        if len(file_content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
            )
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file.write(file_content)
            temp_path = temp_file.name
        
        try:
            description = analyze_pdf(temp_path)
            
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            
            if description.startswith("Error"):
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=description
                )
            
            return {
                "success": True,
                "description": description,
                "filename": file.filename,
                "message": "PDF analyzed successfully."
            }
            
        except Exception as e:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise e
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in PDF analysis: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during PDF analysis"
        )

@router.post("/api/generate-website-from-pdf")
async def generate_website_from_pdf_description(request: DescriptionRequest):
    """
    Generate website code from a PDF description.
    """
    description = request.description
    
    try:
        if not description or description.strip() == "":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Description is required"
            )
        
        html_stream = generate_html_code(description)
        
        return StreamingResponse(
            html_stream,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "X-Accel-Buffering": "no",
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in PDF website generation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during website generation"
        )
