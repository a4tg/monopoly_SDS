# Monopoly SDS

Pre-alpha implementation of a marketing board game platform for SDS.

## Current State

Project is DB-backed and now uses a security baseline for auth:
- JWT `access` + `refresh` tokens.
- Password hashing (`pbkdf2_sha256`).
- Registration/login by email or phone.
- PostgreSQL is the default DB target.
- Alembic migration flow is added.

Core gameplay/admin logic implemented:
- Admin creates sessions and board cells from scratch.
- Flexible roll-window schedule in session config.
- One roll per player per active slot (server-enforced).
- Shared board mode.
- Cell `buy` / `skip`, stock depletion.
- Admin manual accrual + in-app notification on login.
- Inventory + secret shop.
- Secret shop limit: `3 purchases per player per calendar month`.

## Tech Stack
- Frontend: React + TypeScript + Vite
- Backend: FastAPI + SQLAlchemy + Alembic
- DB: PostgreSQL

## Demo Accounts
- Player: `player@demo.local / player`, phone: `+79990000002`
- Admin: `admin@demo.local / admin`, phone: `+79990000001`

## Run

### Backend
```bash
cd backend
python -m pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm.cmd run dev -- --port 5175 --host localhost
```

Open: `http://localhost:5175`

## Auth API
- `POST /auth/register` (email or phone)
- `POST /auth/login` (identifier: email or phone)
- `POST /auth/refresh`
- `GET /auth/me`
- `GET /auth/notifications/unread`
- `POST /auth/notifications/read-all`

## Game API
- `GET /game/state`
- `POST /game/roll`
- `POST /game/cell/{cell_id}/purchase` with `{ "action": "buy" | "skip" }`
- `POST /game/secret-shop/purchase`

## Admin API
- `POST /admin/sessions`
- `GET /admin/sessions`
- `PATCH /admin/sessions/{session_id}/status`
- `POST /admin/sessions/{session_id}/cells`
- `GET /admin/sessions/{session_id}/cells`
- `PATCH /admin/cells/{cell_id}`
- `POST /admin/players/{player_id}/accrual`
- `GET /admin/participants`
- `GET /admin/secret-shop/items`
- `POST /admin/secret-shop/items`
- `PATCH /admin/secret-shop/items/{item_id}`

## Known Limitations
- No realtime transport yet (WebSocket planned next).
- No distributed locking layer yet (Redis planned).
- Refresh token revocation list is not implemented yet (stateless refresh flow).

## Tests
```bash
cd backend
python -m pytest -q
```

## Production
- See deployment guide: `docs/DEPLOYMENT_PROD_RU.md`
- See first-push + git-based deploy guide: `docs/GIT_BOOTSTRAP_AND_DEPLOY_RU.md`
- Production artifacts:
  - `infra/prod/docker-compose.prod.yml`
  - `infra/prod/.env.prod.example`
  - `infra/prod/.env.prod.path.example`
