import os
import re
from html import unescape
from groq import Groq
from dotenv import load_dotenv
load_dotenv()
SUMMARIZER_PROMPT = """
You are a meeting minutes summarizer for a school Islamic organization (Rohis).

Your task is to create a VERY brief summary of meeting minutes (notulensi).

Rules:
- Maximum 2-3 sentences only
- Focus on KEY decisions, actions, or topics discussed
- Use simple, clear language
- Do NOT add any commentary or opinions
- Do NOT use markdown or formatting
- Output plain text only
- If the content is too short or unclear, output: "Meeting notes available."

Example input: "Meeting discussed Ramadan program planning. Decided to have iftar together on March 15th. Ahmad will coordinate with cafeteria. Also discussed fundraising ideas for new prayer mats."

Example output: "Discussed Ramadan program planning. Team will organize iftar gathering on March 15th, with Ahmad coordinating logistics. Fundraising ideas proposed for new prayer mats."
"""


class APIKeyError(Exception):
    """Raised when API key is missing or invalid"""
    pass


def get_groq_client():
    """
    Get Groq client with proper error handling.
    
    Raises:
        APIKeyError: If GROQ_API_KEY is not set in environment
    """
    api_key = os.environ.get("GROQ_API_KEY")
    
    if not api_key:
        raise APIKeyError(
            "GROQ_API_KEY environment variable is not set. "
            "Please set it in your .env file or environment variables."
        )
    
    if not api_key.strip():
        raise APIKeyError(
            "GROQ_API_KEY is empty. Please provide a valid API key."
        )
    
    try:
        return Groq(api_key=api_key)
    except Exception as e:
        raise APIKeyError(f"Failed to initialize Groq client: {str(e)}")


def clean_html(content: str) -> str:
    """
    Remove HTML tags and decode HTML entities.
    
    Args:
        content: HTML content string
        
    Returns:
        Clean text without HTML
    """
    # Strip HTML tags
    clean_text = re.sub('<[^<]+?>', '', content)
    # Decode HTML entities
    clean_text = unescape(clean_text).strip()
    return clean_text


def summarize_notulensi(content: str) -> str:
    """
    Summarize notulensi content into 2-3 sentences using AI.
    
    Args:
        content: HTML content from notulensi
        
    Returns:
        Brief summary string (2-3 sentences)
    """
    if not content or not content.strip():
        return "Meeting notes available."
    
    try:
        # Clean HTML from content
        clean_text = clean_html(content)
        
        # If content is too short after cleaning, return default
        if len(clean_text) < 50:
            return "Meeting notes available."
        
        # Truncate if too long (to save tokens and costs)
        if len(clean_text) > 2000:
            clean_text = clean_text[:2000] + "..."
        
        # Get Groq client
        client = get_groq_client()
        
        # Generate summary
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": SUMMARIZER_PROMPT},
                {"role": "user", "content": clean_text}
            ],
            temperature=0.3,
            max_tokens=150,
        )
        
        summary = completion.choices[0].message.content.strip()
        
        # Validate summary length (should be reasonable)
        if len(summary) < 10 or len(summary) > 500:
            print(f"Warning: Summary length unusual ({len(summary)} chars)")
            return "Meeting notes available."
            
        return summary
    
    except APIKeyError as e:
        # API key not configured
        print(f"API Key Error in summarizer: {e}")
        return "Meeting notes available."
    
    except Exception as e:
        # Any other error
        print(f"Summarization error: {type(e).__name__}: {e}")
        return "Meeting notes available."


def get_summary_cache_key(notulensi_id: int) -> str:
    """
    Generate cache key for notulensi summary.
    
    Args:
        notulensi_id: ID of the notulensi record
        
    Returns:
        Cache key string
    """
    return f"notulensi_summary_{notulensi_id}"