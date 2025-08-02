
import sys
import os
import zipfile
import json
from pathlib import Path
from datetime import datetime
from app.analyzer import analyze

def extract_if_zip(path: str, extract_to="tmp") -> str:
    """
    Extracts ZIP if necessary, returns folder path with extracted or single file.
    """
    if path.endswith(".zip"):
        with zipfile.ZipFile(path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        return extract_to
    return os.path.dirname(path)

def collect_files(folder: str) -> list:
    """
    Walk through extracted folder and collect files to analyze.
    """
    file_list = []
    for root, _, files in os.walk(folder):
        for name in files:
            full_path = os.path.join(root, name)
            file_list.append({
                "name": name,
                "path": full_path
            })
    return file_list

def main(input_path: str):
    extract_path = extract_if_zip(input_path)
    files = collect_files(extract_path)

    # Static context for now — in future this can be extracted from input or user form
    context = {
        "Type": "Load Test",
        "Duration": "10 minutes",
        "Virtual Users": "50",
        "Target": ".NET API on AWS",
        "Backend": "Oracle DB on EC2"
    }

    result = analyze(files, context)

    print("\n📊 AI Analysis Result:")
    print(json.dumps(result, indent=2))

    with open("output.json", "w") as f:
        json.dump(result, f, indent=2)
    print("\n✅ Saved output to output.json")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py path_to_file_or_zip")
        sys.exit(1)
    main(sys.argv[1])
