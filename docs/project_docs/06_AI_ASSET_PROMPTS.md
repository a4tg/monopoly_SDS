# 06. AI Asset Prompts

Use official SDS logo only. Generate all other assets with AI.

## 1. Global Style Prompt
`corporate board game UI, clean b2b visual style, SDS-inspired blue palette, light background, high readability, geometric modern shapes, premium minimal look, vector clarity, production-ready web game assets`

## 2. Palette
- Primary: `#1557B0`
- Accent: `#11A7D9`
- Background: `#F4F8FF`
- Text dark: `#0E1A2B`

## 3. Board Background
Prompt:
`top-down board game background, perimeter cells, subtle tech pattern, clean white center zone, SDS blue gradients, high contrast, 4k`

Negative:
`no text, no logo, no watermark, no fantasy style, no purple dominance`

## 4. Cell Icon Pack
Prompt:
`set of board game cell icons, reward, empty, depleted, timer, lock, bonus, penalty, inventory, clean minimal vector style, transparent background`

Negative:
`no text labels, no photorealism, no noise`

## 5. Player Tokens (multi-player)
Prompt:
`set of 12 distinct board game player tokens, unique silhouettes, polished 3d-like style, top-down and isometric variants, SDS blue-cyan compatible accents, transparent background`

Negative:
`no faces, no mascots, no weapons, no logo`

## 6. Dice Assets
Prompt:
`dice animation sprite sheet, white dice with blue pips, 16 frames, transparent background, consistent lighting`

Alternative:
`single high-quality white dice with blue pips, soft shadow, transparent background`

## 7. Reward Card Templates
Prompt:
`web game reward card template set, title area, price area, stock badge, clean corporate style, light theme, SDS colors, transparent background variants`

## 8. Cell State Overlays
- Active:
`board cell active state overlay, subtle blue glow, clean UI`
- Low stock:
`board cell low stock overlay, mild warning amber marker, clean UI`
- Depleted:
`board cell depleted overlay, desaturated disabled state, clear visual lockout`

## 9. Secret Shop Screen Visual
Prompt:
`secret shop ui mockup for enterprise web game, small reward catalog grid, point prices, stock indicators, clean white panels, SDS blue-cyan accents, responsive layout`

Negative:
`no medieval market, no neon, no clutter`

## 10. Admin Manual Accrual Visual
Prompt:
`admin dashboard screen for manual points accrual, player table, accrual modal with amount and reason, audit log panel, enterprise UI, SDS style`

## 11. Effects Pack
Prompt:
`ui effects pack for board game, token trail, purchase glow, subtle confetti, path highlight, transparent png sequence`

Negative:
`no heavy particles, no over-saturated neon`

## 12. Prompt Templates by Model
- Midjourney:
`/imagine prompt: [GLOBAL_STYLE], [ASSET_PROMPT] --ar 1:1 --v 6 --stylize 120`
- SDXL/Flux:
`[GLOBAL_STYLE], [ASSET_PROMPT], transparent background, ui asset`

## 13. Export Rules
- Use `png` for transparent assets.
- Use `webp` for backgrounds.
- Prepare `1x` and `2x` variants.
- Keep consistent naming:
- `board_bg_v01.webp`
- `token_set_v01.png`
- `cell_icons_v01.svg`
- `dice_sprite_16f_v01.png`
- `secret_shop_ui_ref_v01.png`
