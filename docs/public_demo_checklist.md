# Public Demo Checklist

Use this checklist before publishing RepoPilot on GitHub, recording a demo, or
showing the project in an interview.

## Local Run Steps

1. Open a terminal in the repository:

   ```powershell
   cd D:\RepoPilot
   ```

2. Create and activate a virtual environment if needed:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Install the project with demo dependencies:

   ```powershell
   python -m pip install --upgrade pip
   python -m pip install -e ".[dev]"
   ```

4. Start FastAPI:

   ```powershell
   uvicorn repopilot.main:app --reload
   ```

5. Confirm the API is reachable:

   ```text
   http://127.0.0.1:8000/docs
   ```

## Streamlit Demo Steps

1. Open a second terminal:

   ```powershell
   cd D:\RepoPilot
   streamlit run frontend/streamlit_app.py
   ```

2. Keep `use_llm=false` for the default public demo. RepoPilot works in
   deterministic mode without OpenAI, OpenRouter, or any API key.

3. Click these buttons in order:

   - Overview -> Check API Health
   - Demo Workflow -> Run Safe Demo Workflow
   - Agent Preview -> Run Agent Preview
   - Repository Context -> Retrieve Context
   - Plan Preview -> Generate Deterministic Plan
   - Patch Preview -> Generate Patch Preview

## Screenshots To Capture

- Streamlit Overview tab with the safety principles visible.
- Demo Workflow tab after a successful in-memory workflow run.
- Agent Preview tab with `use_llm=false` and a plan visible.
- Repository Context tab showing retrieved chunks.
- Patch Preview tab showing bounded original/proposed previews.
- FastAPI `/docs` page showing the available endpoint groups.
- README top section and Quickstart if presenting the repository itself.

## What To Avoid Showing Publicly

- Real API keys or local `.env` values.
- OpenAI or OpenRouter billing/account pages.
- Personal paths if you do not want them visible.
- Mutating endpoints on real repositories.
- Patch apply or apply-and-validate endpoints unless using a disposable demo
  repository.
- Raw command output that includes machine-specific or private information.

## Optional LLM Demo Notes

LLM provider integration is optional and may require valid credits/model access.
If you enable it, configure the provider only in the FastAPI server environment.
Do not paste keys into Streamlit.

Use direct OpenAI with:

```powershell
$env:REPOPILOT_LLM_PROVIDER = "openai"
$env:OPENAI_API_KEY = "your-new-openai-key"
$env:OPENAI_MODEL = "gpt-5.5"
```

Use OpenRouter with:

```powershell
$env:REPOPILOT_LLM_PROVIDER = "openrouter"
$env:OPENROUTER_API_KEY = "your-openrouter-key"
$env:OPENROUTER_MODEL = "~openai/gpt-latest"
```

OpenAI and OpenRouter are different providers. Do not send an `OPENAI_API_KEY`
to OpenRouter. If a key was pasted, shared, or committed, revoke it and generate
a new one.
