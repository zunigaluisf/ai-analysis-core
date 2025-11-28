# 🧠 AI Analysis Core

This is the core engine that powers the performance test analysis via AI for the **AI Performance Analyzer** platform.

It uses OpenAI models (`gpt-4.1` for final analysis and `gpt-4.1-mini` for chunk-level summarization) to interpret load test results, extract key insights, and generate recommendations based on input files like `metrics.csv`, `summary.json`, or ZIP bundles.

---

## 🔑 API Key Setup

Store your OpenAI key in `openai_api_key.txt` at the project root (this file is gitignored), or set `OPENAI_API_KEY` in your shell. You can also point to a custom location with `OPENAI_API_KEY_FILE`.

## 🚀 Quick Start (Local)

### 1. Clone the repository

```bash
git clone https://github.com/your-org/ai-analysis-core.git
cd ai-analysis-core
