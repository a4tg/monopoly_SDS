# Production Deployment (Monopoly SDS)

Дата: 2026-04-01

## 1. Как разграничить CRM и Monopoly без домена

У вас уже есть CRM на `http://31.130.135.202/`.
Без покупки домена есть 2 рабочих варианта:

1. По портам (самый простой и безопасный):
- CRM: `http://31.130.135.202/`
- Monopoly: `http://31.130.135.202:8081/`

2. По пути (если хотите на 80 порту):
- CRM: `http://31.130.135.202/`
- Monopoly: `http://31.130.135.202/monopoly/`

Для варианта 2 нужен доступ к nginx-конфигу CRM (добавить `location /monopoly/ ...`).

## 2. Что уже подготовлено в репозитории

- Production compose: `infra/prod/docker-compose.prod.yml`
- Prod env шаблон (портовый вариант): `infra/prod/.env.prod.example`
- Prod env шаблон (path-вариант): `infra/prod/.env.prod.path.example`
- Nginx snippet для path-варианта: `infra/prod/nginx/monopoly_path_location.conf`
- Frontend Dockerfile + nginx inside container:
  - `frontend/Dockerfile`
  - `frontend/nginx/default.conf`
- Backend: отключаем demo-seed в prod через `SEED_DEMO_DATA=false`.

## 3. Быстрый деплой (рекомендуется, вариант по порту)

1. На сервере:
```bash
cd /opt/monopoly-sds
git pull
cp infra/prod/.env.prod.example infra/prod/.env.prod
```

2. Отредактируйте `infra/prod/.env.prod`:
- `POSTGRES_PASSWORD`
- `JWT_SECRET`
- `PASSWORD_RESET_LINK_BASE_URL` (например `http://31.130.135.202:8081/auth/reset`)

3. Запуск:
```bash
cd infra/prod
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
```

4. Проверка:
```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml ps
curl http://31.130.135.202:8081/
```

## 4. Path-вариант (`/monopoly/`) рядом с CRM

1. Подготовьте env:
```bash
cp infra/prod/.env.prod.path.example infra/prod/.env.prod
```

2. Запустите Monopoly:
```bash
cd infra/prod
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
```

3. В nginx CRM добавьте snippet из:
- `infra/prod/nginx/monopoly_path_location.conf`

4. Перезагрузите nginx:
```bash
sudo nginx -t && sudo systemctl reload nginx
```

5. Проверка:
- `http://31.130.135.202/` -> CRM
- `http://31.130.135.202/monopoly/` -> Monopoly

## 5. Обновление приложения

```bash
cd /opt/monopoly-sds
git pull
cd infra/prod
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
```

## 6. Rollback (быстрый)

1. Вернуться на предыдущий commit:
```bash
cd /opt/monopoly-sds
git checkout <PREVIOUS_COMMIT>
```

2. Пересобрать:
```bash
cd infra/prod
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
```

## 7. Обязательные пункты безопасности перед боевым тестом

1. Сильные пароли/секреты в `.env.prod`.
2. `SEED_DEMO_DATA=false` в production.
3. Не публиковать Postgres порт наружу.
4. Регулярный backup тома Postgres.
5. Добавить SMTP для реального восстановления пароля (сейчас ссылка логируется в backend-логи).
