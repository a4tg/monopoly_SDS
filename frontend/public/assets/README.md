# Assets map (alpha)

## Куда класть 2D фигурки игроков

Папка: `frontend/public/assets/tokens/`

Имена файлов для автоподбора:
- `token-01.png`
- `token-02.png`
- `token-03.png`
- `token-04.png`
- `token-05.png`
- `token-06.png`
- `token-07.png`
- `token-08.png`

Рекомендация по файлам:
- формат: PNG или WebP (лучше PNG с прозрачным фоном);
- размер: 256x256 или 512x512;
- одинаковая композиция/масштаб между всеми фигурками.

## Кубик и поле

- Кубик: `frontend/public/assets/dice/`
- Элементы поля: `frontend/public/assets/board/`

## Как работает выбор фигурки

При регистрации backend случайно выбирает одну фигурку из списка `token-01.png ... token-08.png`
и сохраняет ее в профиле пользователя (`users.token_asset`).
