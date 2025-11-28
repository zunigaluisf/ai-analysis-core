import json
import logging
import os
import shutil
import tempfile
import threading
import uuid
import zipfile
from pathlib import Path
from typing import List

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.analyzer import analyze
from app.progress import progress_manager


def setup_logging():
  enabled = os.getenv("LOG_ENABLED", "true").lower() == "true"
  if not enabled:
      return
  default_path = Path(__file__).resolve().parents[1] / "analysis-core.log"
  log_file = Path(os.getenv("AICORE_LOG_FILE", default_path))
  log_file.parent.mkdir(parents=True, exist_ok=True)
  logging.basicConfig(
      level=logging.INFO,
      format='%(asctime)s - %(levelname)s - %(message)s',
      handlers=[logging.FileHandler(log_file), logging.StreamHandler()]
  )
setup_logging()

app = FastAPI()

@app.post("/analyze")
async def analyze_files(
    files: List[UploadFile] = File(...),
    context: str = Form(default="{}")
):
    logging.info("Received request to /analyze endpoint")
    logging.info(f"Number of files received: {len(files)}")
    logging.info(f"Context received: {context}")
    
    """
    Accepts multiple uploaded files and optional context metadata.
    Performs AI-based analysis and returns structured response.
    """
    temp_dir = tempfile.mkdtemp()
    logging.info(f"Temporary directory created at: {temp_dir}")
    try:
        # Save uploaded files to temporary directory
        saved_files = []
        for file in files:
            filename = f"{uuid.uuid4()}_{file.filename}"
            filepath = os.path.join(temp_dir, filename)
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, "wb") as f:
                f.write(await file.read())
            size_bytes = os.path.getsize(filepath)
            saved_files.append({
                "file_id": str(uuid.uuid4()),
                "name": file.filename,
                "path": filepath,
                "size_bytes": size_bytes,
                "file_type": _detect_file_type(file.filename),
            })
            logging.info(f"File saved: {filepath}")

        # Expand zips into individual files for detailed processing and progress UI
        expanded: List[dict] = []
        for f in saved_files:
            if f["name"].lower().endswith(".zip"):
                logging.info("Expanding zip %s", f["name"])
                expanded.extend(_expand_zip(f["path"], f["name"], temp_dir))
            else:
                expanded.append(f)
        if expanded:
            logging.info("Zip expansion produced %s files", len(expanded))
        saved_files = expanded or saved_files
        logging.info("Final file list for analysis: %s", [f.get("name") for f in saved_files])

        # Parse context JSON
        try:
            context_data = json.loads(context)
            logging.info("Context JSON parsed successfully")
        except json.JSONDecodeError:
            logging.error("Invalid JSON in context")
            raise HTTPException(status_code=400, detail="Invalid JSON in context")

        # Call analyzer
        logging.info("Calling analyzer with saved files and context data")
        result = analyze(saved_files, context_data)
        logging.info("Analysis completed successfully")
        return result

    except Exception as e:
        logging.error(f"Analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    finally:
        shutil.rmtree(temp_dir)
        logging.info(f"Temporary directory removed: {temp_dir}")


@app.post("/analyze/progress")
async def analyze_files_with_progress(
    files: List[UploadFile] = File(...),
    context: str = Form(default="{}")
):
    logging.info("Received request to /analyze/progress endpoint")
    temp_dir = tempfile.mkdtemp()
    try:
        saved_files = []
        for file in files:
            filename = f"{uuid.uuid4()}_{file.filename}"
            filepath = os.path.join(temp_dir, filename)
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, "wb") as f:
                f.write(await file.read())
            size_bytes = os.path.getsize(filepath)
            saved_files.append({
                "file_id": str(uuid.uuid4()),
                "name": file.filename,
                "path": filepath,
                "size_bytes": size_bytes,
                "file_type": _detect_file_type(file.filename),
            })

        # Expand zips into individual files for detailed processing and progress UI
        expanded: List[dict] = []
        for f in saved_files:
            if f["name"].lower().endswith(".zip"):
                logging.info("Expanding zip %s", f["name"])
                expanded.extend(_expand_zip(f["path"], f["name"], temp_dir))
            else:
                expanded.append(f)
        if expanded:
            logging.info("Zip expansion produced %s files", len(expanded))
        saved_files = expanded or saved_files
        logging.info("Final file list for analysis: %s", [f.get("name") for f in saved_files])

        try:
            context_data = json.loads(context)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON in context")

        job_id = progress_manager.create_job(saved_files)
        initial = progress_manager.get(job_id)

        def _run():
            try:
                result = analyze(saved_files, context_data, job_id=job_id)
                progress_manager.set_result(job_id, result)
            except Exception as exc:
                logging.exception("Progress analysis failed")
                progress_manager.fail(job_id, f"Analysis failed: {exc}")
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)

        threading.Thread(target=_run, daemon=True).start()
        return {"job_id": job_id, "initial_progress": initial}
    except Exception as exc:
        logging.exception("Failed to start progress analysis")
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"Failed to start analysis: {exc}")


@app.get("/analyze/progress/{job_id}")
async def get_progress(job_id: str):
    job = progress_manager.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
def _detect_file_type(name: str) -> str:
    lower = name.lower()
    if lower.endswith(".log"):
        return "log"
    if lower.endswith(".csv"):
        return "csv"
    if lower.endswith(".jmx"):
        return "jmx"
    if lower.endswith(".json"):
        return "json"
    if lower.endswith(".md") or lower.endswith(".markdown"):
        return "markdown"
    if lower.endswith(".txt"):
        return "text"
    return "unknown"

def _expand_zip(file_path: str, original_name: str, temp_dir: str) -> List[dict]:
    extracted = []
    try:
        with zipfile.ZipFile(file_path, "r") as zf:
            for member in zf.infolist():
                if member.is_dir():
                    continue
                dest_path = os.path.join(temp_dir, member.filename)
                Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
                with zf.open(member) as src, open(dest_path, "wb") as dst:
                    dst.write(src.read())
                size_bytes = os.path.getsize(dest_path)
                extracted.append({
                    "file_id": str(uuid.uuid4()),
                    "name": member.filename,
                    "path": dest_path,
                    "size_bytes": size_bytes,
                    "file_type": _detect_file_type(member.filename),
                    "source_zip": original_name,
                    "message": f"Extracted from {original_name}",
                })
    except Exception as exc:
        logging.warning("Failed to expand zip %s: %s", original_name, exc)
    return extracted
