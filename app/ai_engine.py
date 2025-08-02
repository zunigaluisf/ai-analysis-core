import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

model = os.getenv("OPENAI_MODEL", "gpt-4")

def ask_gpt(prompt: str) -> str:
    """Send a prompt to OpenAI ChatCompletion API and return the reply."""
 
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4
    )
 
    return response.choices[0].message.content
