# MoneyCheck — CLAUDE.md

## Деплой

### Адрес и путь на VPS
- **IP:** 45.141.78.81
- **Домен:** http://bisultoa.beget.tech
- **Путь проекта на VPS:** `/opt/moneycheck/`
- **SSH-пользователь:** root

### Сервисы docker-compose
| Сервис | Образ | Роль |
|--------|-------|------|
| `web` | `ghcr.io/altamar24/money_check:latest` | Django + Gunicorn |
| `db` | `postgres:16-alpine` | База данных PostgreSQL |
| `nginx` | `nginx:alpine` | Reverse-proxy, отдача статики |

### Env-переменные
Файл `.env` хранится только на VPS в `/opt/moneycheck/.env`. В git не попадает.

| Переменная | Где используется |
|------------|-----------------|
| `SECRET_KEY` | Django |
| `DEBUG` | Django (False на проде) |
| `ALLOWED_HOSTS` | Django |
| `CSRF_TRUSTED_ORIGINS` | Django |
| `DB_ENGINE` | Django (postgresql) |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT` | PostgreSQL |
| `TELEGRAM_BOT_TOKEN` | Telegram-авторизация |
| `TELEGRAM_BOT_NAME` | Telegram-авторизация |
| `EMAIL_BACKEND` | Django email |

### Как выкатывается
```
git push origin master
  → GitHub Actions (.github/workflows/deploy.yml)
  → docker build + push → ghcr.io/altamar24/money_check:latest
  → SSH на VPS → cd /opt/moneycheck && docker compose pull && docker compose up -d
```

### Как поменять env или добавить переменную
```bash
# SSH на VPS
ssh root@45.141.78.81

# Редактировать .env
nano /opt/moneycheck/.env

# Перезапустить web-контейнер
cd /opt/moneycheck && docker compose up -d web
```
Если переменная новая — также добавь её в `.env.example` в репозитории.

### Логи и откат

```bash
# Посмотреть логи
cd /opt/moneycheck
docker compose logs -f web      # Django
docker compose logs -f nginx    # Nginx
docker compose logs -f db       # PostgreSQL

# Откат на предыдущий образ
docker compose down
docker tag ghcr.io/altamar24/money_check:previous ghcr.io/altamar24/money_check:latest
docker compose up -d
```

### Статика и nginx
Статика собирается командой `collectstatic` при старте контейнера `web`
и кладётся в Docker volume `static_files`, откуда её отдаёт nginx напрямую
через `/static/`.

### Обновление nginx.conf
Файл лежит в репозитории `nginx/nginx.conf` и на VPS `/opt/moneycheck/nginx/nginx.conf`.
При изменении нужно вручную скопировать на VPS и перезапустить nginx:
```bash
docker compose restart nginx
```
