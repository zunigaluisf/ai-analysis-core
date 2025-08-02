import os
from pathlib import Path
from typing import List, Dict

MAX_LINES = 300  # Max lines to include from a large file

def get_file_snippet(path: Path) -> str:
    """
    Read file and return a truncated version with head and tail content if it's too large.
    """
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        total = len(lines)
        if total > MAX_LINES:
            head = lines[:150]
            tail = lines[-150:]
            snippet = "".join(head + ["...\n"] + tail)
        else:
            snippet = "".join(lines)
        return snippet.strip()
    except Exception as e:
        return f"[Error reading file: {e}]"

def build_prompt(files: List[Dict], context: Dict) -> str:
    """
    Builds a prompt from the list of file dicts and context metadata.

    Each file dict must contain:
    - name: original filename
    - path: path to local file
    - Optional: url to full file if it's too large (public S3, etc.)
    """
    prompt_header = (
        "You are a senior performance engineer.\n\n"
        "You will receive a series of artifacts from a performance test (logs, metrics, reports, etc.).\n\n"
        "Your job is to:\n"
        "1. Summarize the system behavior\n"
        "2. Identify performance bottlenecks\n"
        "3. Provide actionable recommendations\n\n"
        "The context and artifacts are below.\n"
        "====================\n"
    )

    # Insert test context metadata
    context_block = "Test Context:\n"
    for k, v in context.items():
        context_block += f"- {k}: {v}\n"
    context_block += "\n====================\n"

    # Include each file block
    file_blocks = ""
    for f in files:
        file_path = Path(f["path"])
        snippet = get_file_snippet(file_path)
        num_lines = snippet.count("\n")
        file_blocks += f"File: {f['name']}\n--------------------\n"

        if num_lines >= MAX_LINES:
            file_blocks += "[File too large to include in full.]\n"
            if f.get("url"):
                file_blocks += f"Link to full file: {f['url']}\n"
            file_blocks += "\n--- Snippet ---\n"

        file_blocks += snippet + "\n"
        file_blocks += "====================\n\n"

    return prompt_header + context_block + file_blocks
