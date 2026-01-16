import base64
import io
import json
from PIL import Image
import asyncio 
import logging
from openai import OpenAI
from core.config import settings

logger = logging.getLogger(__name__)
api_key = settings.API_KEY  # Use the API key from settings

def analyze_image(image_path: str) -> str:
    """
    Analyze an uploaded image and provide a detailed description of its content and layout.

    Args:
        image_path: The file path to the image to analyze

    Returns:
        A detailed description of the image content, layout, and website type
    """
    if not image_path:
        return "Error: No image path provided"

    # Use system API keys from environment
    effective_api_key = settings.NVIDIA_API_KEY or settings.OPENROUTER_API_KEY or settings.API_KEY
    
    if not effective_api_key:
        logger.error("No API key found in system settings")
        return "Error: No valid API key found. Please set NVIDIA_API_KEY or OPENROUTER_API_KEY in your .env file."

    key_prefix = effective_api_key[:10] + "..." if effective_api_key else "None"
    logger.info(f"Using system API key with prefix: {key_prefix}")

    try:
        # Open the image from the file path
        try:
            image = Image.open(image_path)
        except FileNotFoundError:
            return f"Error: Image file not found at {image_path}"
        except Exception as e:
            return f"Error opening image file: {str(e)}"

        # Determine base URL based on API key
        base_url = "https://openrouter.ai/api/v1"
        model = "Qwen/Qwen2.5-VL-72B-Instruct"
        
        if effective_api_key.startswith("nvapi-"):
            base_url = "https://integrate.api.nvidia.com/v1"
            model = "nvidia/llama-3.1-nemotron-nano-vl-8b-v1" 
        
        # Configure OpenAI client
        client = OpenAI(
            base_url=base_url,
            api_key=effective_api_key,
        )

        # Convert image to base64
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

        # Create prompt
        prompt = """
        Analyze this image and provide a concise description.
        Describe the main elements, colors, layout, and UI components.
        Identify what type of website or application this resembles.
        Focus on structural and visual elements that would be important for recreating the design.
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
        return f"Error analyzing image: {str(e)}"

def generate_html_code(description: str) -> str:
    """
    Generate HTML/CSS/JavaScript code based on a website description.

    Args:
        description: Detailed description of the website to generate

    Returns:
        Complete HTML code with embedded CSS and JavaScript
    """
    if not description or description.startswith("Error"):
        return "Error: Invalid or missing description"



    # Inline system prompt and enhanced prompt
    system_prompt = """
You are an expert web developer specializing in creating production-ready, content-rich websites. You will respond in EXACTLY three parts separated by specific markers:

PART 1 - ANALYSIS (between ===ANALYSIS_START=== and ===ANALYSIS_END===):
Provide a brief analysis of what the user needs, understanding their requirements, and what type of website would best serve their needs.

PART 2 - CODE (between ===CODE_START=== and ===CODE_END===):
Generate ONLY HTML, CSS AND JAVASCRIPT. 

**CRITICAL CONTENT REQUIREMENTS:**
- Use ALL actual content, data, and information provided in the description
- If contact information is provided (phone, email, address), include it in the website
- If services, features, or products are listed, create dedicated sections for them
- If pricing or packages are mentioned, display them prominently
- If company/product names are given, use them throughout the site
- Replace ALL placeholder text with real content from the description
- Create multiple sections based on the content categories identified

**DESIGN REQUIREMENTS:**
- If you want to use ICONS, import Font Awesome or Lucide icons library first
- For images, use www.unsplash.com with relevant search terms based on the content
- Create a modern, professional UI using HTML, CSS and JAVASCRIPT
- You may use TailwindCSS (import via <script src="https://cdn.tailwindcss.com"></script> in head)
- Implement smooth animations, hover effects, and interactive elements
- Ensure responsive design for all screen sizes
- Use a cohesive color scheme that matches the content theme

**OUTPUT FORMAT:**
OUTPUT ONLY THE COMPLETE HTML CODE STARTING WITH <!DOCTYPE html> AND ENDING WITH </html>. NO ADDITIONAL TEXT.

PART 3 - SUMMARY (between ===SUMMARY_START=== and ===SUMMARY_END===):
Explain what you have created, key features implemented, design choices made, and how it meets the user's requirements.

**STRICT FORMAT REQUIREMENT:**
===ANALYSIS_START===
[Your analysis here]
===ANALYSIS_END===

===CODE_START===
[Complete HTML code here]
===CODE_END===

===SUMMARY_START===
[Your summary here]
===SUMMARY_END===
"""

    enhanced_prompt = f"""
CREATE A WORLD-CLASS, CONTENT-RICH WEBSITE BASED ON THE FOLLOWING DETAILED SPECIFICATION:

{description}

**MANDATORY REQUIREMENTS:**

1. **Use Real Content**: Extract and use ALL actual content from the description above:
   - Company/Product names
   - Contact information (phone, email, address, social media)
   - Services, features, or product offerings
   - Pricing, packages, or plans
   - Testimonials or reviews
   - Any other specific data mentioned

2. **Content Structure**: Create dedicated sections for each content category identified in the description

3. **Professional Quality**: 
   - Modern, clean design with professional typography
   - Smooth animations and micro-interactions
   - Fully responsive layout
   - SEO-friendly structure with proper headings
   - Fast-loading, optimized code

4. **Visual Excellence**:
   - Use appropriate color schemes
   - High-quality images from Unsplash
   - Professional icons
   - Consistent spacing and alignment

5. **Functionality**:
   - Working navigation
   - Interactive elements (buttons, forms, etc.)
   - Smooth scrolling
   - Mobile-friendly menu

**IMPORTANT**: This website should be production-ready and indistinguishable from those created by professional development teams. Use the actual content provided—do not use generic placeholders.

Remember to follow the three-part response format with proper markers for analysis, code, and summary.
"""

    # Use system NVIDIA API key from environment
    effective_nvidia_key = settings.NVIDIA_API_KEY
        
    if not effective_nvidia_key:
        raise Exception("No valid NVIDIA API key found. Please set NVIDIA_API_KEY in your .env file.")

    nvidia_client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=effective_nvidia_key
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": enhanced_prompt}
    ]

    # Use the selected model with fallback
    try:
        response = nvidia_client.chat.completions.create(
            model="moonshotai/kimi-k2-instruct",
            messages=messages,
            temperature=0.2,
            max_tokens=85000,
            stream=True
        )
    except Exception as e:
        error_str = str(e)
        logger.warning(f"Primary AI generation failed: {error_str}")
        
        # Fallback if we get a 403/401 or if the primary key failed and we have an alternative
        can_fallback = ("403" in error_str or "401" in error_str or "Authorization failed" in error_str)
        
        if can_fallback and settings.OPENROUTER_API_KEY and effective_nvidia_key != settings.OPENROUTER_API_KEY:
            logger.info("Attempting fallback to OpenRouter for generation...")
            try:
                or_client = OpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=settings.OPENROUTER_API_KEY,
                )
                response = or_client.chat.completions.create(
                    model="meta-llama/llama-3.1-405b-instruct",
                    messages=messages,
                    temperature=0.2,
                    max_tokens=85000,
                    stream=True
                )
                logger.info("Fallback to OpenRouter successful")
            except Exception as fallback_err:
                logger.error(f"Fallback to OpenRouter also failed: {str(fallback_err)}")
                raise fallback_err
        else:
            raise e

    async def stream_generator():
        try:
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content.encode("utf-8")
                    await asyncio.sleep(0.01)
        except Exception as e:
            logger.error(f"Stream error: {str(e)}")
            yield f"\n[ERROR]: Stream interrupted - {str(e)}".encode("utf-8")

    return stream_generator()


def screenshot_to_code(image_path: str) -> tuple:
    """
    Complete pipeline: analyze image and generate corresponding HTML code.

    Args:
        image_path: Screenshot image path to analyze

    Returns:
        Tuple of (description, html_code)
    """
    # Analyze image
    description = analyze_image(image_path)

    if description.startswith("Error"):
        return description, "Error: Cannot generate code due to image analysis failure"

    # Generate code
    html_code = generate_html_code(description)

    return description, html_code