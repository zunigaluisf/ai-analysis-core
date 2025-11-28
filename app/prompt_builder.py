from typing import List, Dict


def build_prompt(file_summaries: List[Dict], context: Dict) -> str:
    """
    Build the final analysis prompt using preprocessed summaries only.

    file_summaries items contain:
    - name: file name
    - file_type: detected type
    - summary: consolidated summary
    - chunks: chunk count
    - total_lines: line count
    """
    prompt_header = (
        "You are a senior performance engineer.\n"
        "You will receive preprocessed summaries of performance artifacts (logs, metrics, reports, configs).\n"
        "Use ONLY the provided summaries. Do not request or assume missing raw data.\n\n"
        "Produce a Markdown report with the following sections:\n"
        "- Executive Summary\n"
        "- Test Context\n"
        "- Key Metrics & Findings\n"
        "- Detailed Issues & Root Cause Hypotheses\n"
        "- Recommendations\n"
        "- Next Steps\n\n"
        "Be concise, evidence-driven, and avoid filler text. Tie recommendations to observed signals.\n"
        "====================\n"
    )

    context_block = "Test Context:\n"
    for k, v in context.items():
        context_block += f"- {k}: {v}\n"
    context_block += "\n====================\n"

    file_blocks = "File Summaries (preprocessed):\n"
    for f in file_summaries:
        summary_text = (f.get('summary', '') or '').replace("\n", "\n    ")
        file_blocks += (
            f"- File: {f.get('name')}\n"
            f"  - Type: {f.get('file_type', 'unknown')}\n"
            f"  - Lines: {f.get('total_lines', 'n/a')} | Chunks: {f.get('chunks', 0)}\n"
            f"  - Summary:\n    {summary_text}\n"
        )
    file_blocks += "\n====================\n"

    return prompt_header + context_block + file_blocks
