# 04. System Architecture

## 1. Recommended Stack
- Frontend: React + TypeScript + Vite + Zustand + Framer Motion.
- Backend: FastAPI + PostgreSQL + SQLAlchemy + Alembic.
- Realtime: WebSocket.
- Cache/locking: Redis.

## 2. Main Data Model
- `users`
- `game_sessions`
- `boards`
- `cells`
- `player_session_state`
- `player_balance_events`
- `inventory_items`
- `player_notifications`
- `secret_shop_items`
- `secret_shop_purchases`
- `move_events`

## 3. Required Fields
- `game_sessions.roll_window_config` (flexible admin schedule with multiple slots)
- `player_session_state.last_roll_at`, `rolls_in_window`
- `cells.stock`, `cells.price_points`, `cells.status`
- `player_balance_events.source`: `admin_manual`, `cell_purchase`, `secret_shop_purchase`
- `player_notifications.type`: `manual_accrual`
- `secret_shop_purchases.purchase_month`, `monthly_count` (limit enforcement)

## 4. Roll Endpoint Flow
1. Validate active session.
2. Validate current time is inside roll window.
3. Validate player has not rolled in this window.
4. Server rolls dice.
5. Server updates player position.
6. Return landed cell state.
7. Return action mode for landed cell: `buy` or `skip`.

## 5. Cell Purchase Flow
1. Open DB transaction.
2. Lock target cell row (`FOR UPDATE`).
3. Check `stock > 0`.
4. Check player balance.
5. Deduct points.
6. Insert inventory item.
7. Decrease cell stock.
8. Commit and publish realtime event.

## 6. Admin Manual Accrual Flow
1. Admin inputs amount and reason.
2. Insert `player_balance_events`.
3. Insert `player_notifications` item for target player.
4. Recompute player balance.
5. Push realtime balance update.

## 6.1 Player Login Notification Flow
1. Player authenticates.
2. Backend fetches unread `player_notifications`.
3. Frontend shows notification center/toast.
4. Backend marks shown notifications as read (or acknowledged).

## 7. Secret Shop
- Separate catalog and stock.
- Uses same player balance.
- Own purchase history table.
- Enforce limit: max `3 purchases per player per calendar month`.

## 8. Realtime Events
- `session:state_updated`
- `player:moved`
- `cell:stock_changed`
- `cell:depleted`
- `balance:changed`
- `inventory:changed`
- `secret_shop:changed`

## 9. Reliability
- Idempotency keys for purchases.
- Rate limiting for roll endpoint.
- Full admin audit trail.
- Client state updates only after server ack.
- Physical prize fulfillment statuses are not implemented in MVP.
