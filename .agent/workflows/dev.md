---
description: Development workflow with auto-confirm for all commands
---

// turbo-all

## Standard Ports (ne pas changer)

- **Backend API**: `8000`
- **Frontend Dashboard**: `3000`

## Start Commands

1. Kill any existing processes on these ports (if needed):

```bash
lsof -ti:8000 | xargs kill -9 2>/dev/null; lsof -ti:3000 | xargs kill -9 2>/dev/null
```

2. Start Backend:

```bash
cd /Users/cube/Documents/00-code/0xBot/backend && source venv/bin/activate && python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

3. Start Frontend:

```bash
cd /Users/cube/Documents/00-code/0xBot/frontend && npx -y serve -l 3000 .
```

4. Access Dashboard: http://localhost:3000/dashboard.html

## Notes

- Backend MUST run on port 8000 (configured in dashboard.html)
- Frontend serves static files on port 3000
