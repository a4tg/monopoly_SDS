# 03. Product Requirements (MVP to Production)

## 1. Product Goal
Build a marketing web game with one shared board where managers spend admin-granted points on rewards from board cells and from a secret shop.

## 2. Roles
- `player`: rolls in allowed window, buys rewards, manages inventory.
- `admin`: creates board from scratch, configures cells, grants points, manages secret shop.

## 3. Critical User Flow
1. Real sale happens.
2. Admin grants points manually.
3. Player receives on-login site notification about new accrual.
4. Player makes one roll in active window.
5. Player chooses `buy` or `skip` on active cell.
6. Player can spend remaining points in secret shop.

## 4. MVP Scope
- Auth with role separation.
- Admin board builder (create board from zero).
- Limited-stock cells with point prices.
- One roll per active window.
- Roll window is configured in admin panel (flexible schedule).
- Cell reward purchase + player inventory.
- Manual point accrual in admin panel.
- On-login in-app notification for manual accrual events.
- Secret shop with separate stock and monthly limit.
- Realtime multi-player state on one board.

## 5. Post-MVP
- Seasonal campaigns.
- Advanced analytics.
- Notifications.
- Fraud monitoring.

## 6. KPI
- Active players per period.
- Roll-window usage rate.
- Points-to-purchase conversion.
- Cell depletion speed.
- API and realtime error rate.

## 7. MVP Acceptance
- Admin can create board and open session.
- Player can roll only once per active window.
- Depleted cell cannot sell reward.
- Cell purchase is optional (`buy/skip`) and, when bought, deducts points, decreases stock, creates inventory item.
- Secret shop purchase works with same player balance and max `3 items per player per month`.
- Physical reward fulfillment workflow is out of scope for MVP.
