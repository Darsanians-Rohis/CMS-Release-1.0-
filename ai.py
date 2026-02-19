import os
import re
from groq import Groq
from dotenv import load_dotenv
load_dotenv()
SYSTEM_PROMPT = """
You are an Islamic educational assistant for a school Rohis organization.
Explain concepts clearly and respectfully.
Do not issue fatwas or definitive rulings.
If a question requires a scholar, advise consulting a trusted ustadz.
Give concise short answers focused on Islamic teachings and values.
Avoid using table format.
Avoid using markdown or bold formatting.
If you don't know the answer, say "I'm sorry, I don't have that information."
Do not reference yourself as an AI model.
Keep answers under 200 words.
Do not provide legal, medical, or political advice.

If the user asks to go to a page or feature, respond ONLY with:
NAVIGATE: <page_name>

Valid page names:
dashboard, attendance, members, login
"""

ROUTE_MAP = {
    "dashboard": "/",
    "attendance": "/attendance",
    "members": "/member-list",
    "login": "/login",
}

NAV_REGEX = re.compile(r"^NAVIGATE\s*:\s*(\w+)$", re.IGNORECASE)


class APIKeyError(Exception):
    pass


def get_groq_client():
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


def call_chatbot_groq(message: str) -> dict:
    """
    Call Groq API for chatbot response.
    
    Args:
        message: User's input message
        
    Returns:
        dict with 'action' and either 'message' or 'redirect'
    """
    # Validate input
    if not message or not message.strip():
        return {
            "action": "chat",
            "message": "Please ask a question."
        }
    
    if len(message) > 500:
        return {
            "action": "chat",
            "message": "Please ask a shorter question (max 500 characters)."
        }

    try:
        # Get Groq client
        client = get_groq_client()
        
        # Make API call
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT.strip()},
                {"role": "user", "content": message.strip()}
            ],
            temperature=0.3,
            max_tokens=180,
        )

        content = completion.choices[0].message.content.strip()

        # Check for navigation command
        match = NAV_REGEX.match(content)
        if match:
            page = match.group(1).lower()
            route = ROUTE_MAP.get(page)
            if route:
                return {
                    "action": "navigate",
                    "redirect": route
                }

        # Return normal chat response
        return {
            "action": "chat",
            "message": content
        }

    except APIKeyError as e:
        # API key configuration error
        print(f"API Key Error: {e}")
        return {
            "action": "chat",
            "message": "Chat service is currently unavailable. Please contact the administrator."
        }
    
    except Exception as e:
        # Any other error (network, API rate limit, etc.)
        print(f"Groq API error: {type(e).__name__}: {e}")
        return {
            "action": "chat",
            "message": "I'm sorry, I can't respond right now. Please try again later."
        }