import os
import google.genai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

def call_ai(prompt, model_name='gemini-3.1-flash-lite-preview'):
    """
    Centralized function to call an AI model. 
    This wrapper abstracts the AI provider, ensuring easy swapping between
    Gemini, OpenAI, local LLMs, etc. for production flexibility.
    Though not as advanced solution as discussed in the issues but a good start.
    Fixes #13
    """
    if not client:
        raise Exception("AI client is not initialized (e.g. missing API key).")
        
    response = client.models.generate_content(
        model=model_name,
        contents=prompt
    )
    return response.text.strip()
