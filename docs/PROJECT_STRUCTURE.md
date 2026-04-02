# Базовая структура проекта

```text
Monopoly_SDS/
  backend/
    app/
      api/            # Роуты (auth, game, admin)
      core/           # Конфиг, security, роли
      db/             # Подключение БД, репозитории
      models/         # ORM модели
      schemas/        # Pydantic схемы
      services/       # Бизнес-логика (движок игры)
      main.py         # Точка входа FastAPI
    migrations/       # Alembic миграции
    requirements.txt
  frontend/
    src/
      pages/          # Страницы игрока и админа
      components/     # Переиспользуемые компоненты UI
      services/       # API клиент
      store/          # Zustand/Redux
      types/          # Типы DTO
      main.tsx
      App.tsx
    package.json
  shared/
    contracts/
      api.yaml        # API-контракт (OpenAPI/согласованные DTO)
  infra/
    docker/
      docker-compose.yml
  docs/
    IMPLEMENTATION_PLAN.md
    PROJECT_STRUCTURE.md
  tests/
    unit/
    integration/
  .env.example
  README.md
```
