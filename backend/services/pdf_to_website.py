import fitz  # PyMuPDF
import base64
import io
import logging
from PIL import Image
from openai import OpenAI
from core.config import settings
from services.image_to_website import generate_html_code

logger = logging.getLogger(__name__)

def analyze_pdf(pdf_path: str) -> str:
    """
    Analyze an uploaded PDF by converting its first page to an image and extracting text.
    """
    if not pdf_path:
        return "Error: No PDF path provided"

    # Use system API keys from environment
    effective_api_key = settings.NVIDIA_API_KEY or settings.OPENROUTER_API_KEY or settings.API_KEY
    
    if not effective_api_key:
        logger.error("No API key found in system settings")
        return "Error: No valid API key found. Please set NVIDIA_API_KEY or OPENROUTER_API_KEY in your .env file."

    key_prefix = effective_api_key[:10] + "..." if effective_api_key else "None"
    logger.info(f"Using system API key with prefix: {key_prefix}")


    try:
        # Open the PDF
        doc = fitz.open(pdf_path)
        if len(doc) == 0:
            return "Error: PDF is empty"

        # Extract comprehensive text from ALL pages
        full_text_content = ""
        page_texts = []
        
        for page_num, page in enumerate(doc):
            page_text = page.get_text()
            page_texts.append(f"--- Page {page_num + 1} ---\n{page_text}")
            full_text_content += page_text + "\n\n"
        
        # Get PDF metadata
        total_pages = len(doc)
        metadata = doc.metadata
        
        # Convert the first page to an image for visual analysis
        page = doc[0]
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) # 2x zoom for better quality
        img_data = pix.tobytes("png")
        image = Image.open(io.BytesIO(img_data))
        
        doc.close()

        # Determine base URL based on API key
        base_url = "https://openrouter.ai/api/v1"
        model = "Qwen/Qwen2.5-VL-72B-Instruct"
        
        if effective_api_key.startswith("nvapi-"):
            base_url = "https://integrate.api.nvidia.com/v1"
            model = "nvidia/llama-3.1-nemotron-nano-vl-8b-v1"
        
        client = OpenAI(
            base_url=base_url,
            api_key=effective_api_key,
        )

        # Convert image to base64
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

        # Create enhanced prompt with full content
        prompt = f"""
        Analyze this PDF document to create a comprehensive website design specification.
        
        PDF METADATA:
        - Total Pages: {total_pages}
        - Title: {metadata.get('title', 'N/A')}
        
        COMPLETE EXTRACTED TEXT (All {total_pages} pages):
        {full_text_content[:8000]}  # Increased limit for more content
        
        VISUAL ANALYSIS (First page image attached):
        Based on the image and text, provide a detailed description that includes:
        
        1. **Content Structure**: Identify all sections, headings, and key information from the PDF
        2. **Visual Design**: Describe colors, fonts, layout patterns, and styling from the first page
        3. **Content Categories**: List all distinct content types (e.g., contact info, services, features, pricing, testimonials, etc.)
        4. **Key Information**: Extract specific details like:
           - Company/Product name
           - Contact information (phone, email, address)
           - Services or features offered
           - Pricing or packages
           - Any calls-to-action
           - Social media or website links
        
        5. **Website Type**: Determine what type of website this should be (landing page, portfolio, business site, etc.)
        
        IMPORTANT: Your description will be used to generate a complete, content-rich website. Include ALL important text content, data, and information from the PDF so it can be incorporated into the final website code.
        """

        # Use the selected model with fallback
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{img_str}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1000,
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            error_str = str(e)
            logger.warning(f"Primary AI analysis failed: {error_str}")
            
            # Fallback if we get a 403/401 or if the primary key failed and we have an alternative
            can_fallback = ("403" in error_str or "401" in error_str or "Authorization failed" in error_str)
            
            if can_fallback and settings.OPENROUTER_API_KEY and effective_api_key != settings.OPENROUTER_API_KEY:
                logger.info("Attempting fallback to OpenRouter...")
                try:
                    fallback_client = OpenAI(
                        base_url="https://openrouter.ai/api/v1",
                        api_key=settings.OPENROUTER_API_KEY,
                    )
                    response = fallback_client.chat.completions.create(
                        model="Qwen/Qwen2.5-VL-72B-Instruct",
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": prompt},
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/png;base64,{img_str}"
                                        }
                                    }
                                ]
                            }
                        ],
                        max_tokens=1000,
                        temperature=0.7
                    )
                    logger.info("Fallback to OpenRouter successful")
                    return response.choices[0].message.content
                except Exception as fallback_err:
                    logger.error(f"Fallback to OpenRouter also failed: {str(fallback_err)}")
                    raise fallback_err
            else:
                raise e

    except Exception as e:
        logger.error(f"Error analyzing PDF: {str(e)}")
        return f"Error analyzing PDF: {str(e)}"
