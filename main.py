import zipfile
import sys
import os
from app.ai_engine import ask_gpt
from app.processors.csv_parser import read_metrics_csv
from app.processors.json_parser import read_summary_json

BASE_PROMPT_PATH = "app/prompts/base_prompt.txt"

def extract_if_zip(path: str, extract_to="tmp") -> str:
    """Extracts ZIP if necessary, returns folder path with extracted or single file."""
    if path.endswith(".zip"):
        with zipfile.ZipFile(path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        return extract_to
    return os.path.dirname(path)

def find_file(name: str, folder: str) -> str:
    """Looks for a file by name inside the given folder."""
    for root, _, files in os.walk(folder):
        for file in files:
            if file == name:
                return os.path.join(root, file)
    return ""

def build_prompt(csv_data: str, json_data: str) -> str:
    """Load base prompt and append extracted content."""
    with open(BASE_PROMPT_PATH, 'r') as f:
        base_prompt = f.read()
    
    # Combine the prompt and the loaded data
    return (
        f"{base_prompt}\n\n"
        f"---\n\n"
        f"metrics.csv:\n{csv_data}\n\n"
        f"summary.json:\n{json_data}"
   )


def main(input_path: str):
    extract_path = extract_if_zip(input_path)
    csv_file = find_file("metrics.csv", extract_path)
    json_file = find_file("summary.json", extract_path)

    if not csv_file or not json_file:
        print("Required files (metrics.csv and summary.json) not found.")
        return

    csv_data = read_metrics_csv(csv_file)
    json_data = read_summary_json(json_file)
    prompt = build_prompt(csv_data, json_data)
    response = ask_gpt(prompt)

    print("\n📊 AI Analysis Result:\n")
    print(response)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py path_to_file_or_zip")
        sys.exit(1)
    main(sys.argv[1])
