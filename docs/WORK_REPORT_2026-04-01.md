# Work Report (2026-04-01)

## Done

1. Reliability and security baseline:
- JWT access + refresh flow.
- Password hashing and legacy password compatibility.
- Postgres-first local setup and Alembic migration flow.

2. Auth UX:
- Register/login with email or phone.
- Frontend auth forms aligned with backend contracts.

3. Alpha UI base:
- RU-oriented UI structure for Auth/Game/Admin.
- Dice UI and token rendering placeholders.
- Token asset pool support (`token-01.png` ... `token-08.png`).

4. Session roll governance:
- `game_sessions.max_rolls_per_window`.
- Backend enforcement of per-window roll limits.

5. Session lifecycle and admin controls (new):
- Session schedule fields added: `starts_at`, `ends_at`, `ended_at`.
- Manual immediate finish endpoint: `POST /admin/sessions/{session_id}/end`.
- Session schedule update endpoint: `PATCH /admin/sessions/{session_id}/schedule`.
- Player assignment endpoint: `POST /admin/sessions/{session_id}/participants`.
- Assigned player listing endpoint: `GET /admin/sessions/{session_id}/participants`.
- Results export endpoint (JSON/CSV): `GET /admin/sessions/{session_id}/results?format=json|csv`.

6. Gameplay guardrails (new):
- Active session now checks schedule boundaries and end marker.
- Player actions require assignment when participant list exists.
- Backward compatibility: if a session has no assigned participants, all players are allowed.

7. Token rendering fix (new):
- Fixed broken token preview where fallback symbol was visible through transparent PNG.
- Added client-side transparent-boundary trim for token PNGs to keep piece visually centered and readable.
- Added cache for processed token images to avoid repeated canvas processing.

8. Admin UI v2 for session operations (new):
- Added session schedule management in UI (`starts_at`, `ends_at`, roll window time, max rolls per window).
- Added player assignment UI with checkbox selector per session.
- Added manual session finish action from UI.
- Added results export from UI (JSON preview + CSV download).
- Extended frontend API client with session participants/schedule/results endpoints.

9. Monopoly board renderer update (new):
- Replaced simple grid with a Monopoly-like perimeter board (11x11 layout, 40 perimeter slots).
- Added center zone for company branding with logo placeholder.
- Added optional center logo image loading from `/assets/logo/company-logo.png`.
- Kept token movement animation compatible with the new board coordinates.

10. Cell details and media (new):
- Added optional fields for board cells: `description` and `image_url`.
- Added migration `20260401_000005_cell_description_and_image`.
- Added click-to-open detail card on game board cells (Monopoly-style field card).
- Added admin UI support for cell image attachment (URL/Data URL and local file upload helper).
- Added admin UI cell editing for title/description/reward/image/price/stock.

11. Dynamic board size and sparse cells (new):
- Added `game_sessions.board_size` (migration `20260401_000006_session_board_size`).
- Board size is now configurable from admin UI at session create/update.
- Movement logic now uses `board_size` instead of number of created cards.
- Sparse board is supported: unfilled indices are valid empty cells (player can get no reward).
- Added backend validation: created cell index must be `< board_size`.

12. Player marketplace (new):
- Added player-to-player marketplace offers with statuses (`pending/accepted/rejected/canceled`).
- Added migration `20260401_000007_player_trade_offers` and `market_trade` balance source.
- Added API endpoints:
  - list session players and their balances,
  - view another player inventory,
  - create offer for specific inventory item,
  - list incoming/outgoing offers,
  - accept/reject incoming offer.
- Accept flow now transfers inventory ownership and points between players atomically.
- Added game UI marketplace section: send offer, incoming/outgoing lists, accept/reject actions.

13. Marketplace routing + auth recovery (new):
- Marketplace moved from the game screen to a dedicated frontend page: `/market`.
- Navigation updated: added direct "Торговля" link in the top bar.
- `GamePage` now focuses only on core gameplay and board interactions.
- Added password reset flow:
  - `POST /auth/password-reset/request` (email-based request),
  - `POST /auth/password-reset/confirm` (set new password by token).
- Added DB table `password_reset_tokens` with migration `20260401_000008_password_reset_tokens`.
- Added frontend pages:
  - `/auth/forgot` (request reset link),
  - `/auth/reset` (set new password using token).
- Auth page now includes a direct "Забыли пароль?" link.
- Fixed mojibake issue in key frontend pages (`App.tsx`, `AuthPage.tsx`) and restored readable Russian text.

14. Marketplace v2: auctions + live sidebars (new):
- Added auction domain with auto-close mechanics:
  - seller opens lot from own inventory item with duration,
  - players place bids until `ends_at`,
  - on expiry lot is finalized automatically by backend on market API access,
  - winner is chosen by highest valid bid (with sufficient balance at close time),
  - item ownership transfers to winner,
  - winner balance decreases, seller balance increases.
- Added backend entities and migration:
  - `auction_lots`, `auction_bids`, `session_activity_events`,
  - migration `20260401_000009_auction_and_session_activity`.
- Added market activity event logging for:
  - direct offers created/accepted/rejected,
  - auction opened,
  - auction bid placed,
  - auction closed/closed without winner.
- Added new API endpoints:
  - `POST /game/market/auctions`
  - `POST /game/market/auctions/{lot_id}/bid`
  - `GET /game/market/auctions`
  - `GET /game/market/activity`
  - `GET /game/market/rating`
- Added session rating calculation:
  - `total_score = player_balance + sum(inventory_item.paid_points in session)`.
- Reworked frontend `/market` page:
  - left sidebar: live rating list,
  - center: direct offers + auction creation + open/closed lots + bidding,
  - right sidebar: live activity feed (polling every 5 seconds).

15. Global player sidebars (new):
- Moved live sidebars from market-only view to shared app shell.
- Activity feed and rating are now shown on all player pages (e.g. `/game`, `/market`).
- Sidebars are hidden on `/auth*` and `/admin` routes as requested.

16. UI localization + responsive shell fix (new):
- Restored Russian labels in global header and shared player sidebars.
- Reworked page shell sizing so sidebars no longer overlap main content.
- Increased max layout width and switched sidebar columns to adaptive `clamp(...)` widths.
- Added breakpoint (`<= 1420px`) where sidebars move below the main content to preserve usable game area.

17. Production readiness package (new):
- Added production deployment compose:
  - `infra/prod/docker-compose.prod.yml`
- Added production env templates:
  - `infra/prod/.env.prod.example` (separate port mode),
  - `infra/prod/.env.prod.path.example` (path mode `/monopoly/`).
- Added frontend production containerization:
  - `frontend/Dockerfile`,
  - `frontend/nginx/default.conf` (SPA serving + `/api` reverse proxy to backend container).
- Added backend production config controls:
  - `APP_ENV`, `SEED_DEMO_DATA`, `CORS_ORIGINS`.
- Updated app startup behavior:
  - demo data seeding can now be disabled in production (`SEED_DEMO_DATA=false`).
- Added deployment guide:
  - `docs/DEPLOYMENT_PROD_RU.md`
- Added nginx path-routing snippet for coexistence with CRM on same IP:
  - `infra/prod/nginx/monopoly_path_location.conf`

## Database changes

1. Existing migrations:
- `20260401_000001_initial_schema`
- `20260401_000002_user_token_asset`
- `20260401_000003_session_max_rolls_per_window`

2. Added migration:
- `20260401_000004_session_schedule_and_participants`
  - Adds `starts_at`, `ends_at`, `ended_at` to `game_sessions`
  - Creates `session_participants`

3. Added migration:
- `20260401_000008_password_reset_tokens`
  - Creates `password_reset_tokens` with TTL/used markers and token hash index

## Validation

1. Backend tests:
- `PYTHONPATH=. venv\Scripts\pytest.exe -q` -> `5 passed`

2. Backend import check:
- `PYTHONPATH=. venv\Scripts\python.exe -c "from app.main import app; print(app.title)"` -> OK

3. Alembic head check:
- `PYTHONPATH=. venv\Scripts\alembic.exe heads` -> `20260401_000004 (head)`

4. Frontend build:
- `npm run build` -> success

5. Backend tests:
- `$env:PYTHONPATH='backend'; backend\venv\Scripts\pytest.exe -q backend/tests` -> `5 passed`

6. Backend syntax check:
- `python -m py_compile backend/app/api/auth.py ...` -> success

7. Additional validation for marketplace v2:
- `python -m py_compile backend/app/api/game.py backend/app/models/entities.py ...` -> success
- `pytest backend/tests` -> `5 passed`
- `npm run build` -> success

## Next steps

1. Wire admin UI for:
- Session schedule editing.
- Participant assignment picker per session.
- Results export buttons (JSON/CSV).

2. Add API tests for:
- Assignment enforcement.
- Schedule boundary behavior.
- Manual end behavior.

3. Run docker migration on local environment:
- `docker compose up -d db backend`
- Verify session endpoints from UI.

4. Apply new migration and validate reset flow:
- `docker compose exec backend alembic upgrade head`
- Open `/auth/forgot`, request reset for a known email, then open `/auth/reset?token=...` from backend logs.

5. Apply auction migration:
- `docker compose exec backend alembic upgrade head`
- Verify `/market`:
  - create direct offer,
  - create auction lot,
  - place bids from another player,
  - ensure auto-close updates balances and inventory after lot expiration.
