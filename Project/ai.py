import os
import google.genai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

def call_ai(prompt, model_name='gemini-2.5-flash-lite'):
    """
    Centralized function to call an AI model.
    Change this implementation to connect to OpenAI, Anthropic, local LLM, or anything else.
    """
    if not client:
        raise Exception("AI client is not initialized (e.g. missing API key).")
        
    response = client.models.generate_content(
        model=model_name,
        contents=prompt
    )
    return response.text.strip()
