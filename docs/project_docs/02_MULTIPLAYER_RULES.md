# 02. Multiplayer Rules (Locked)

## 1. Core Rules
- All players are on one shared board.
- No board exists by default; admin creates it from scratch.
- Each cell has limited reward stock (`stock`).
- A player can buy a cell reward using points and store it in inventory.
- When `stock = 0`, the cell is depleted and gives nothing.

## 2. Turn Mode
- Global shared mode only.
- One dice roll per player inside the admin-defined roll window.
- Roll window is fully configurable in admin panel (calendar-based schedule, multiple time slots).

## 3. Business/Game Loop
1. Manager makes a real-world sale.
2. Admin manually grants points in admin panel.
3. During active roll window, player rolls once.
4. Player lands on a cell.
5. If cell is active and player has enough points, player chooses `buy` or `skip`.
6. Points are deducted, inventory item is created, cell `stock` decreases.
7. If cell is depleted, no reward is granted.

## 4. Cell States
- `ACTIVE`: `stock > 0`
- `DEPLETED`: `stock = 0`

## 5. Inventory
- Separate tab for each player.
- Each item stores reward, source cell, price, and timestamp.

## 6. Secret Shop
- Separate section on the site.
- Player can spend remaining balance on small rewards.
- Secret shop has its own catalog and stock.
- Secret shop stock is independent from board cells.
- Secret shop has a hard purchase limit: max `3 items per player per calendar month`.

## 7. Concurrency
- Reward purchase from cell is atomic on server.
- If multiple players target last stock at same time, only first committed tx wins.
- Others get `depleted` or `insufficient_points`.

## 8. Server Authority
- One-roll-per-window check is server-side only.
- Balance checks and point deduction are server-side only.
- Client only renders returned state.

## 9. Audit
- Log all manual accruals, rolls, purchases, deductions, cell depletion events, and secret-shop purchases.
