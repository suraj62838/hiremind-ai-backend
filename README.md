# HireMind AI Backend

A simple FastAPI backend for resume analysis, interview question generation, answer evaluation, and reporting using the Groq AI API.

## Features

- Upload PDF or DOCX resumes for analysis
- Calculate an ATS-style score
- Generate interview questions based on resume content
- Evaluate candidate answers
- Create a final report from evaluation data

## Requirements

- Python 3.10+ recommended
- `fastapi`
- `uvicorn`
- `python-dotenv`
- `pdfplumber`
- `python-docx`
- `groq`

## Environment

Create a `.env` file in the repository root with:

```env
GROQ_API_KEY=your_groq_api_key_here
```

## Installation

1. Create a virtual environment:

```bash
python -m venv venv
```

2. Activate the virtual environment:

- PowerShell:
  ```powershell
  .\venv\Scripts\Activate.ps1
  ```
- Command Prompt:
  ```cmd
  .\venv\Scripts\activate.bat
  ```

3. Install dependencies:

```bash
pip install fastapi uvicorn python-dotenv pdfplumber python-docx groq
```

## Running the app

```bash
uvicorn main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

## API Endpoints

### `GET /`

Returns a simple health check message.

### `POST /upload`

Upload a resume file and get resume analysis.

Form fields:
- `file` (file): PDF or DOCX resume
- `role` (string)
- `level` (string)
- `experience` (string)
- `technologies` (string)

### `POST /interview`

Upload a resume and generate interview questions.

Form fields:
- `file` (file): PDF or DOCX resume
- `role` (string)
- `level` (string)
- `experience` (string)

### `POST /evaluate`

Evaluate a candidate answer using JSON payload.

JSON body:

```json
{
  "question": "What is your biggest strength?",
  "answer": "My biggest strength is..."
}
```

### `POST /final-report`

Create a final report from evaluation results.

JSON body:

```json
{
  "evaluations": [
    {
      "question": "...",
      "answer": "...",
      "score": 8,
      "feedback": "...",
      "improvements": "...",
      "confidence": "high"
    }
  ]
}
```

## Notes

- The `uploads/` folder is used to store uploaded resume files.
- The repository includes a `.gitignore` entry for `uploads/` and keeps the folder via `uploads/.gitkeep`.
- Only `.pdf` and `.docx` resume formats are supported.

## License

This project is provided as-is.
