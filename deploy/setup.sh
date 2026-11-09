#!/usr/bin/env bash
# Установка тренажёра на Ubuntu 22.04: Python 3.12, venv, зависимости, systemd.
#
# Запуск на сервере, уже с распакованным кодом:
#   sudo bash /opt/mf-translator/deploy/setup.sh
#
# Переопределить пути/имена можно переменными окружения:
#   APP_DIR=/srv/trainer SERVICE_USER=trainer SERVICE_NAME=emotion-trainer sudo -E bash deploy/setup.sh
#
# Скрипт идемпотентен: повторный запуск доставит зависимости и перезапустит сервис.
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/mf-translator}"
SERVICE_NAME="${SERVICE_NAME:-emotion-trainer}"
SERVICE_USER="${SERVICE_USER:-trainer}"

if [ "$(id -u)" -ne 0 ]; then
    echo "Запускай через sudo: sudo bash deploy/setup.sh" >&2
    exit 1
fi

if [ ! -f "$APP_DIR/deploy/emotion-trainer.service" ]; then
    echo "В $APP_DIR нет кода: сначала распакуй проект туда (см. deploy/DEPLOY.md)." >&2
    exit 1
fi

echo "[1/6] Пакеты и Python 3.12"
# В Ubuntu 22.04 по умолчанию Python 3.10, а проекту нужно >= 3.12:
# берём 3.12 из deadsnakes. Альтернатива без PPA — uv, см. deploy/DEPLOY.md.
export DEBIAN_FRONTEND=noninteractive
apt-get update -q
apt-get install -y -q python3 software-properties-common ca-certificates sqlite3 sudo fonts-dejavu-core
add-apt-repository -y ppa:deadsnakes/ppa >/dev/null
apt-get update -q
apt-get install -y -q python3.12 python3.12-venv

echo "[2/6] Пользователь $SERVICE_USER"
if ! getent group "$SERVICE_USER" >/dev/null 2>&1; then
    groupadd --system "$SERVICE_USER"
fi
if ! id -u "$SERVICE_USER" >/dev/null 2>&1; then
    # Домашний каталог уже существует — создавать его useradd не нужно.
    useradd --system --home-dir "$APP_DIR" --shell /usr/sbin/nologin \
        --no-create-home --gid "$SERVICE_USER" "$SERVICE_USER"
fi
chown -R "$SERVICE_USER:$SERVICE_USER" "$APP_DIR"
chmod 750 "$APP_DIR"
# Архив, собранный на Windows, приносит файлы с правами 666 — код стал бы доступен
# на запись всем. Нормализуем; .venv и data не трогаем, у них свои права.
for folder in bot deploy scenarios tests prompts; do
    if [ -d "$APP_DIR/$folder" ]; then
        chmod -R u=rwX,go=rX "$APP_DIR/$folder"
    fi
done
find "$APP_DIR" -maxdepth 1 -type f -exec chmod 644 {} +
if [ -f "$APP_DIR/.env" ]; then
    chmod 600 "$APP_DIR/.env"
fi
if [ -d "$APP_DIR/data" ]; then
    chmod 750 "$APP_DIR/data"
fi
if [ -f "$APP_DIR/data/bot.db" ]; then
    chmod 600 "$APP_DIR/data/bot.db"
fi

echo "[3/6] Виртуальное окружение и зависимости"
if [ ! -x "$APP_DIR/.venv/bin/python" ]; then
    sudo -u "$SERVICE_USER" -H python3.12 -m venv "$APP_DIR/.venv"
fi
sudo -u "$SERVICE_USER" -H "$APP_DIR/.venv/bin/python" -m pip install -q --upgrade pip
sudo -u "$SERVICE_USER" -H "$APP_DIR/.venv/bin/python" -m pip install -q -e "$APP_DIR"

echo "[4/6] Файл .env"
if [ ! -f "$APP_DIR/.env" ]; then
    sudo -u "$SERVICE_USER" -H cp "$APP_DIR/.env.example" "$APP_DIR/.env"
    chmod 600 "$APP_DIR/.env"
    chown "$SERVICE_USER:$SERVICE_USER" "$APP_DIR/.env"
    echo "    Создан $APP_DIR/.env — впиши TELEGRAM_BOT_TOKEN, DEEPSEEK_API_KEY,"
    echo "    SAFETY_RESOURCES: nano $APP_DIR/.env"
fi

echo "[5/6] systemd-юнит $SERVICE_NAME"
sed "s|__APP_DIR__|$APP_DIR|g; s|__SERVICE_USER__|$SERVICE_USER|g" \
    "$APP_DIR/deploy/emotion-trainer.service" \
    > "/etc/systemd/system/$SERVICE_NAME.service"
systemctl daemon-reload
# Включаем и запускаем только после проверки ключей, иначе сервис уйдёт в цикл рестартов.

echo "[6/6] Проверка окружения (токен, прокси, ключ модели)"
if ! sudo -u "$SERVICE_USER" -H "$APP_DIR/.venv/bin/python" -m bot.doctor; then
    echo
    echo "Не готово: заполни $APP_DIR/.env и запусти:"
    echo "  sudo -u $SERVICE_USER $APP_DIR/.venv/bin/python -m bot.doctor"
    echo "  sudo systemctl restart $SERVICE_NAME"
    exit 1
fi

if grep -q '^TELEGRAM_BOT_TOKEN=.\+' "$APP_DIR/.env" \
    && grep -q '^DEEPSEEK_API_KEY=.\+' "$APP_DIR/.env"; then
    systemctl enable "$SERVICE_NAME" >/dev/null
    systemctl restart "$SERVICE_NAME"
    echo
    echo "Бот запущен. Статус: systemctl status $SERVICE_NAME"
    echo "Логи:              journalctl -u $SERVICE_NAME -f"
else
    echo "Ключи в $APP_DIR/.env пока пустые — сервис не включаю."
    echo "Впиши ключи и запусти скрипт ещё раз."
fi
