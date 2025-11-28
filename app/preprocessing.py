import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Tuple

from app.ai_engine import SUMMARY_MODEL, ask_gpt

logger = logging.getLogger(__name__)

# Chunking thresholds to stay well under model context limits
MAX_LINES_PER_CHUNK = int(os.getenv("PREPROCESS_MAX_LINES_PER_CHUNK", "400"))
MAX_CHARS_PER_CHUNK = int(os.getenv("PREPROCESS_MAX_CHARS_PER_CHUNK", "6000"))
MAX_FILE_WORKERS = int(os.getenv("PREPROCESS_MAX_WORKERS", "4"))
MAX_CHUNK_WORKERS = int(os.getenv("PREPROCESS_MAX_CHUNK_WORKERS", str(MAX_FILE_WORKERS)))


def detect_file_type(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in {".log"}:
        return "log"
    if ext in {".csv"}:
        return "csv"
    if ext in {".jmx"}:
        return "jmx"
    if ext in {".json"}:
        return "json"
    if ext in {".md", ".markdown"}:
        return "markdown"
    if ext in {".txt"}:
        return "text"
    return "unknown"


def _chunk_text(text: str) -> List[str]:
    lines = text.splitlines()
    chunks: List[str] = []
    current_lines: List[str] = []
    current_len = 0

    for line in lines:
        # Reserve newline as well
        line_len = len(line) + 1
        if (
            current_lines
            and (len(current_lines) >= MAX_LINES_PER_CHUNK or current_len + line_len > MAX_CHARS_PER_CHUNK)
        ):
            chunks.append("\n".join(current_lines))
            current_lines = []
            current_len = 0
        current_lines.append(line)
        current_len += line_len

    if current_lines:
        chunks.append("\n".join(current_lines))
    return chunks


def _read_file(path: Path) -> Tuple[str, int]:
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
        return content, content.count("\n") + 1
    except Exception as exc:
        logger.warning("Failed to read file %s: %s", path, exc)
        return "", 0


def _summarize_chunk(file_name: str, file_type: str, chunk_text: str, chunk_index: int, total_chunks: int) -> str:
    prompt = (
        f"You are summarizing {file_type or 'file'} content for performance analysis.\n"
        f"File: {file_name}\n"
        f"Chunk {chunk_index + 1} of {total_chunks}\n"
        "Summarize key performance signals, metrics, errors, and anomalies in under 180 words. "
        "Use concise bullet points when possible. Focus on latency, throughput, errors, resource saturation, and lock/GC warnings. "
        "Do NOT add extra commentary or conclusions beyond what appears in this chunk.\n\n"
        "Chunk Content:\n"
        "----------------\n"
        f"{chunk_text[:MAX_CHARS_PER_CHUNK]}\n"
    )
    return ask_gpt(prompt, model=SUMMARY_MODEL, temperature=0.2)


def _summarize_file_from_chunks(file_name: str, file_type: str, chunks: List[str]) -> Tuple[str, List[str]]:
    chunk_summaries = [None] * len(chunks)
    # Parallel chunk summarization with ordering preservation
    try:
        with ThreadPoolExecutor(max_workers=MAX_CHUNK_WORKERS) as executor:
            future_to_idx = {executor.submit(_summarize_chunk, file_name, file_type, chunk, idx, len(chunks)): idx for idx, chunk in enumerate(chunks)}
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    chunk_summaries[idx] = future.result().strip()
                except Exception as exc:
                    logger.warning("Chunk summary failed for file=%s chunk=%s: %s", file_name, idx, exc)
                    chunk_summaries[idx] = f"[Chunk {idx + 1} summary failed: {exc}]"
    except Exception as exc:
        # Fallback to sequential if executor setup fails
        logger.warning("Parallel chunk summarization failed for file=%s, falling back to sequential: %s", file_name, exc)
        for idx, chunk in enumerate(chunks):
            try:
                chunk_summaries[idx] = _summarize_chunk(file_name, file_type, chunk, idx, len(chunks)).strip()
            except Exception as inner_exc:
                logger.warning("Sequential chunk summary failed for file=%s chunk=%s: %s", file_name, idx, inner_exc)
                chunk_summaries[idx] = f"[Chunk {idx + 1} summary failed: {inner_exc}]"

    # Meta-summary across chunk summaries
    combined_prompt = (
        f"File: {file_name}\n"
        f"Type: {file_type or 'unknown'}\n"
        "You are consolidating multiple partial summaries for this file. "
        "Combine them into a single meta-summary (max 220 words) highlighting key signals, metrics, and anomalies. "
        "Avoid repetition. Keep bullet structure tight.\n\n"
        "Partial Summaries:\n"
        "------------------\n"
        + "\n\n".join(chunk_summaries)
    )
    meta_summary = ask_gpt(combined_prompt, model=SUMMARY_MODEL, temperature=0.2)
    return meta_summary.strip(), chunk_summaries


def preprocess_files(files: List[Dict]) -> List[Dict]:
    """
    Preprocess uploaded files:
    - Detect type
    - Chunk large files
    - Summarize chunks with gpt-4.1-mini
    - Meta-summarize per file
    Returns list of dicts containing summaries only (no raw content).
    """
    file_summaries: List[Dict] = [None] * len(files)

    def _process_file(idx: int, file_dict: Dict) -> Dict:
        path = Path(file_dict["path"])
        file_type = detect_file_type(path)
        content, total_lines = _read_file(path)
        if not content:
            return {
                "name": file_dict.get("name") or path.name,
                "file_type": file_type,
                "summary": "Unable to read file content.",
                "chunks": 0,
                "chunk_summaries": [],
                "total_lines": total_lines,
            }

        chunks = _chunk_text(content)
        if not chunks:
            return {
                "name": file_dict.get("name") or path.name,
                "file_type": file_type,
                "summary": "Empty file.",
                "chunks": 0,
                "chunk_summaries": [],
                "total_lines": total_lines,
            }

        logger.info("Preprocessing file=%s type=%s chunks=%s lines=%s", path.name, file_type, len(chunks), total_lines)
        meta_summary, chunk_summaries = _summarize_file_from_chunks(file_dict.get("name") or path.name, file_type, chunks)
        return {
            "name": file_dict.get("name") or path.name,
            "file_type": file_type,
            "summary": meta_summary,
            "chunks": len(chunks),
            "chunk_summaries": chunk_summaries,
            "total_lines": total_lines,
        }

    try:
        with ThreadPoolExecutor(max_workers=MAX_FILE_WORKERS) as executor:
            future_to_idx = {executor.submit(_process_file, idx, f): idx for idx, f in enumerate(files)}
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    file_summaries[idx] = future.result()
                except Exception as exc:
                    logger.warning("File preprocessing failed for %s: %s", files[idx].get("name"), exc)
                    file_summaries[idx] = {
                        "name": files[idx].get("name") or Path(files[idx]["path"]).name,
                        "file_type": detect_file_type(Path(files[idx]["path"])),
                        "summary": f"[Preprocessing failed: {exc}]",
                        "chunks": 0,
                        "chunk_summaries": [],
                        "total_lines": 0,
                    }
    except Exception as exc:
        logger.warning("Parallel file preprocessing failed, falling back to sequential: %s", exc)
        for idx, f in enumerate(files):
            try:
                file_summaries[idx] = _process_file(idx, f)
            except Exception as inner_exc:
                logger.warning("Sequential file preprocessing failed for %s: %s", f.get("name"), inner_exc)
                file_summaries[idx] = {
                    "name": f.get("name") or Path(f["path"]).name,
                    "file_type": detect_file_type(Path(f["path"])),
                    "summary": f"[Preprocessing failed: {inner_exc}]",
                    "chunks": 0,
                    "chunk_summaries": [],
                    "total_lines": 0,
                }

    return file_summaries
