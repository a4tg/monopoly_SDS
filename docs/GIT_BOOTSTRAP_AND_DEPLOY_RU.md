# Git Bootstrap + Deploy From Git (Ubuntu server)

Дата: 2026-04-02

## 1) Первый push проекта в Git

Выполните локально в корне проекта:

```bash
cd C:\Users\artem\Desktop\projects\Monopoly_SDS
git init
git branch -M main
git add .
git commit -m "chore: initial commit for monopoly sds"
git remote add origin <YOUR_REMOTE_GIT_URL>
git push -u origin main
```

Если remote уже есть:
```bash
git remote set-url origin <YOUR_REMOTE_GIT_URL>
git push -u origin main
```

## 2) Что важно НЕ заливать

Уже настроено в `.gitignore`:
- `backend/venv`, `.venv`
- `frontend/node_modules`
- `frontend/dist`
- локальные `.env*` (кроме `.env.example`)
- логи/кеши

## 3) Деплой на сервер из Git (path-вариант `/monopoly/`)

На сервере (root):

```bash
mkdir -p /opt
cd /opt
git clone <YOUR_REMOTE_GIT_URL> monopoly-sds
cd /opt/monopoly-sds/infra/prod
cp .env.prod.path.example .env.prod
nano .env.prod
```

После настройки `.env.prod`:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
```

## 4) Обновление версии на сервере

```bash
cd /opt/monopoly-sds
git pull origin main
cd /opt/monopoly-sds/infra/prod
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
```

## 5) Проверка текущего ревизионного коммита на сервере

```bash
cd /opt/monopoly-sds
git rev-parse --short HEAD
```

## 6) Быстрый rollback

```bash
cd /opt/monopoly-sds
git log --oneline -n 10
git checkout <COMMIT_HASH>
cd /opt/monopoly-sds/infra/prod
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
```
