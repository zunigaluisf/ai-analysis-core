import os
import shutil
import uuid
import tempfile
import json
from typing import List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from app.analyzer import analyze
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
            with open(filepath, "wb") as f:
                f.write(await file.read())
            saved_files.append({"name": file.filename, "path": filepath})
            logging.info(f"File saved: {filepath}")

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
