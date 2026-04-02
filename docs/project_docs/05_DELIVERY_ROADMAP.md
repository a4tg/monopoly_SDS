# 05. Delivery Roadmap

## Phase 1: Product and UX (1-2 weeks)
- Lock game rules and economy.
- Approve SDS-style UI tokens and core layouts.
- Finalize screens: Auth, Board, Inventory, Secret Shop, Admin.

## Phase 2: Backend Foundation (2 weeks)
- Move from in-memory to PostgreSQL.
- Implement sessions, boards, cells, balances, inventory, secret shop models.
- Implement auth, roles, admin manual accrual API.

## Phase 3: Core Gameplay (1-2 weeks)
- Implement global board mode.
- Implement one-roll-per-window rule.
- Implement cell purchase and depletion logic.
- Implement inventory flows.

## Phase 4: Realtime Multiplayer (1 week)
- Live positions for all players on same board.
- Live cell stock and depletion updates.
- Live balance and inventory updates.

## Phase 5: SDS Visual Polish (2 weeks)
- Introduce SDS brand styling.
- Add multiple token types.
- Add smooth dice and movement animations.
- Add cell state visuals: active, low, depleted.

## Phase 6: Admin Console Complete (1 week)
- Board-from-scratch editor.
- Roll-window scheduling tools.
- Manual points accrual panel.
- Secret-shop management panel.

## Phase 7: Hardening and Launch (1-2 weeks)
- Integration and e2e tests.
- Observability and audit.
- Load testing for simultaneous players.
- UAT and production release.

## Milestones
- `M1`: Admin creates board and launches session.
- `M2`: Player roll window rule works end-to-end.
- `M3`: Cell and secret-shop purchases work in one shared economy.
- `M4`: Realtime multi-player experience is stable.
