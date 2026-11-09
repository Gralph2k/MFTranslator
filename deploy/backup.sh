#!/usr/bin/env bash
# Резервная копия базы тренажёра. Безопасна на работающем боте:
# sqlite3 .backup снимает консистентный снимок, в отличие от copy bot.db.
#
# Запуск:   sudo bash /opt/mf-translator/deploy/backup.sh
# Хранение: 14 дней, меняется переменной KEEP_DAYS.
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/mf-translator}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/emotion-trainer}"
KEEP_DAYS="${KEEP_DAYS:-14}"

DB="$APP_DIR/data/bot.db"
if [ ! -f "$DB" ]; then
    echo "Базы пока нет: $DB — бэкапить нечего."
    exit 0
fi

mkdir -p "$BACKUP_DIR"
STAMP="$(date +%F_%H%M)"
TARGET="$BACKUP_DIR/bot-$STAMP.db"

sqlite3 "$DB" ".backup '$TARGET'"
# Старые копии чистим, чтобы диск не забился.
find "$BACKUP_DIR" -name 'bot-*.db' -mtime +"$KEEP_DAYS" -delete

echo "Готово: $TARGET"
