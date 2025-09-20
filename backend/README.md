# Backend (FastAPI)

- Create venv and install requirements:

```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r backend/requirements.txt
```

- Run server:

```bash
uvicorn backend.app.main:app --reload --port 8000
```
