# 01. Brand and UX Direction (SDS-Inspired)

## 1. Objective
Create a polished, business-grade game interface with strong SDS-style identity: clean, reliable, modern, and technology-oriented.

## 2. Visual Direction
- Corporate B2B aesthetic.
- Light surfaces with strong blue accents.
- Clear hierarchy, low visual noise.
- Geometric shapes and subtle tech patterns.

## 3. Working Design Tokens (v1 draft)
- `--sds-primary-700: #0A3F8A`
- `--sds-primary-600: #1557B0`
- `--sds-primary-500: #1F6BD6`
- `--sds-accent-cyan: #11A7D9`
- `--sds-bg-100: #F4F8FF`
- `--sds-surface: #FFFFFF`
- `--sds-text-900: #0E1A2B`
- `--sds-text-600: #4B5D79`
- `--sds-success: #1F9D55`
- `--sds-warning: #D38B10`
- `--sds-danger: #C53A3A`

## 4. Typography
- Headings: `Manrope` or `Montserrat`.
- Body: `Inter`.
- Numeric counters: `Space Grotesk`.

## 5. Core Screens
- Auth page.
- Shared game board with multi-player tokens.
- Inventory tab.
- Secret shop.
- Admin panel with board editor and manual points accrual.

## 6. Motion Principles
- Dice roll: 600-900 ms.
- Token movement: step-by-step, 140-200 ms per cell.
- Reward purchase feedback: short glow + card popup.
- Depleted cell transition: desaturation and disabled marker.

## 7. UX Requirements
- One-roll-per-window status must be clear.
- Cell stock visibility must be clear.
- Purchase actions must show resulting balance before confirm.
- Realtime updates should not interrupt active user input.

## 8. Accessibility
- WCAG AA contrast.
- Statuses must not rely on color only.
- Reduced-motion mode support.
