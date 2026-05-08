# eval-dashboard backend

FastAPI 앱. `:8001` 에서 동작.

```bash
python3 -m virtualenv .venv
.venv/bin/pip install -e .
cp .env.example .env
.venv/bin/uvicorn eval_dashboard.main:app --reload --port 8001
# OpenAPI: http://127.0.0.1:8001/docs
```
