## Progress UI and Streaming Analysis Updates

### Overview
- Added real-time analysis progress support with job-based polling.
- Instrumented preprocessing and analysis steps to emit step/file/chunk progress.
- Exposed new API endpoints for progress-driven analysis.
- Added frontend progress UI overlay with per-file status, micro-logs, and animated global progress.

### Backend (AI Core)
- `app/progress.py`: In-memory `ProgressManager` to track job status, per-file progress, logs, and results.
- `app/api.py`: New endpoints:
  - `POST /analyze/progress` — starts analysis in a background thread and returns `job_id`.
  - `GET /analyze/progress/{job_id}` — polls job status/result.
- `app/analyzer.py`: Accepts optional `job_id`, emits progress at major steps (reading, prompt build, AI analysis, finalize).
- `app/preprocessing.py`: Parallel file/chunk summarization now emits progress updates per file/chunk; preserves order and falls back to sequential on failure.
- `app/ai_engine.py`: Improved retry/backoff with rate-limit detection.

### Backend (Gateway)
- `app/api/v1/endpoints/analyze.py`: Added proxy routes to AI Core progress endpoints:
  - `POST /api/analyze-with-ai/progress` — starts job, returns `job_id`.
  - `GET /api/analyze-with-ai/progress/{job_id}` — polls progress.

### Frontend
- `src/components/ReportDetailsModal.tsx`:
  - Uses new progress endpoints to start analysis and poll job status.
  - Displays modern overlay with animated global bar, current step, micro-logs, and per-file cards showing status/progress and chunk info.
  - Auto-refreshes report on completion; graceful failure handling.

### Notes
- Existing analyze endpoint remains unchanged.
- Progress is monotonic and includes human-readable messages.
- Parallel processing respects concurrency limits already in preprocessing; falls back to sequential on errors.
