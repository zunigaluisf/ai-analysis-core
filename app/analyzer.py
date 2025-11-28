
import logging
import os
from datetime import datetime
from typing import List, Dict, Optional

from app.ai_engine import ANALYSIS_MODEL, ask_gpt
from app.preprocessing import preprocess_files
from app.prompt_builder import build_prompt

logger = logging.getLogger(__name__)


def _extract_section(markdown: str, title: str) -> str:
    """Extract a section by heading title (case-insensitive)."""
    lines = markdown.splitlines()
    start_idx: Optional[int] = None
    for idx, line in enumerate(lines):
        if line.strip().lower().lstrip("#").strip() == title.lower():
            start_idx = idx + 1
            break
    if start_idx is None:
        return ""

    collected: List[str] = []
    for line in lines[start_idx:]:
        stripped = line.strip()
        if stripped.startswith("#"):  # next heading reached
            break
        collected.append(line)
    return "\n".join(collected).strip()


def analyze(files: List[Dict], context: Dict) -> Dict:
    logger.info("Starting analysis with %s files and context keys=%s", len(files), list(context.keys()))
    file_summaries = preprocess_files(files)

    prompt = build_prompt(file_summaries, context)
    ai_response = ask_gpt(prompt, model=ANALYSIS_MODEL, temperature=0.35)
    logger.info("AI analysis complete using model=%s", ANALYSIS_MODEL)

    # Parse expected sections from Markdown response
    summary = _extract_section(ai_response, "Executive Summary")
    insights = _extract_section(ai_response, "Key Metrics & Findings")
    recommendations = _extract_section(ai_response, "Recommendations")
    if not summary:
        summary = ai_response

    return {
        "summary": summary.strip(),
        "insights": insights.strip(),
        "recommendations": recommendations.strip(),
        "response": ai_response.strip(),
        "markdown_report": ai_response.strip(),
        "ai_markdown_report": ai_response.strip(),
        "model_used": ANALYSIS_MODEL,
        "analyzed_at": datetime.utcnow().isoformat() + "Z",
        "preprocessing": {
            "files": [
                {
                    "name": f.get("name"),
                    "file_type": f.get("file_type"),
                    "chunks": f.get("chunks"),
                    "total_lines": f.get("total_lines"),
                }
                for f in file_summaries
            ]
        },
    }
