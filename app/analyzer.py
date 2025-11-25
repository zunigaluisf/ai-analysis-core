
import os
from datetime import datetime
from typing import List, Dict

from app.prompt_builder import build_prompt
from app.ai_engine import ask_gpt

def analyze(files: List[Dict], context: Dict) -> Dict:
    print(f"Starting analysis with {len(files)} files and context: {context}")  # Debugging log
    """
    Orchestrates the full AI analysis pipeline:
    - Builds prompt from uploaded files and test context
    - Sends to LLM (e.g. OpenAI)
    - Returns structured analysis

    Args:
        files: List of dicts with keys: name, path, optional url
        context: Dict of test metadata (duration, type, target, etc.)

    Returns:
        Dict with keys: summary, insights, recommendations, model_used, analyzed_at
    """
    prompt = build_prompt(files, context)
    ai_response = ask_gpt(prompt)
    print("AI Response:", ai_response)  # Debugging log
    # Parse into sections; fall back to full response as summary if headers missing
    sections = {"summary": "", "insights": "", "recommendations": ""}
    current = None
    for line in ai_response.splitlines():
        line_clean = line.strip().lower()
        if line_clean.startswith("summary:"):
            current = "summary"
            continue
        if line_clean.startswith("insights:"):
            current = "insights"
            continue
        if line_clean.startswith("recommendations:"):
            current = "recommendations"
            continue
        if current:
            sections[current] += line + "\n"

    # If nothing parsed, treat entire response as summary
    if not any(sections.values()):
        sections["summary"] = ai_response

    print("AI Response Sections:", sections)  # Debugging log
    return {
        "summary": sections["summary"].strip(),
        "insights": sections["insights"].strip(),
        "recommendations": sections["recommendations"].strip(),
        "response": ai_response.strip(),
        "model_used": os.getenv("OPENAI_MODEL", "unknown"),
        "analyzed_at": datetime.utcnow().isoformat() + "Z"
    }
