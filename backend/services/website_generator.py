import os
import asyncio
import logging
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
logger = logging.getLogger(__name__)


def get_unified_system_prompt():
    return """
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

def get_enhanced_user_prompt(original_prompt):
    return f"""
CREATE A WORLD-CLASS, CONTENT-RICH WEBSITE BASED ON THE FOLLOWING SPECIFICATION:

{original_prompt}

**MANDATORY REQUIREMENTS:**

1. **Use Real Content**: If the prompt contains specific information, use it:
   - Company/Product names
   - Contact information (phone, email, address, social media)
   - Services, features, or product offerings
   - Pricing, packages, or plans
   - Testimonials or reviews
   - Any other specific data mentioned

2. **Content Structure**: Create dedicated sections for each content category

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

**IMPORTANT**: This website should be production-ready and indistinguishable from those created by professional development teams. Use actual content when provided—avoid generic placeholders.

Remember to follow the three-part response format with proper markers for analysis, code, and summary.
"""


from core.config import settings

async def generate_html_stream(prompt: str, previous_html: str = None, previous_prompt: str = None):
    
    # Use system NVIDIA API key from environment
    effective_nvidia_key = settings.NVIDIA_API_KEY
        
    if not effective_nvidia_key:
        raise Exception("No valid NVIDIA API key found. Please set NVIDIA_API_KEY in your .env file.")

    nvidia_client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=effective_nvidia_key
    )

    
    system_prompt = get_unified_system_prompt()
    enhanced_prompt = get_enhanced_user_prompt(prompt)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": enhanced_prompt}
    ]

    # Use the selected model with fallback
    try:
        completion = nvidia_client.chat.completions.create(
            model="moonshotai/kimi-k2-instruct-0905",
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
                completion = or_client.chat.completions.create(
                    model="meta-llama/llama-3.1-405b-instruct", # High quality fallback
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
            for chunk in completion:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content.encode("utf-8")
                    # await asyncio.sleep(0.01)
        except Exception as e:
            logger.error(f"Stream error: {str(e)}")
            yield f"\n[ERROR]: Stream interrupted - {str(e)}".encode("utf-8")

    return stream_generator()