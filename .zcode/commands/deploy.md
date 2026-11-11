---
description: Пошаговый деплой на VPS по deploy/DEPLOY.md §7 — с обязательной остановкой перед scp и restart
argument-hint: [что меняется, например "сценарий eva_message"]
---

Обновление боевого бота. **Правило проекта: любое изменение кода, сценариев или
конфигурации деплоится и перезапускает бота.** Сервер: `root@138.124.229.233`,
код `/opt/mf-translator`, сервис `emotion-trainer`.

Выполняй **только по явной команде владельца** и с двумя жёсткими остановками:
перед отправкой архива (шаг 5) и перед `systemctl restart` (шаг 7). До подтверждения
— только локальные шаги и чтение. `ssh`/`scp`/`tar` подтверждаются системой прав
(это нормально), `git push` запрещён правилами `AGENTS.md` — не предлагать.

## 0. Сначала прочитать

- `deploy/DEPLOY.md` §7 — единственный правильный порядок, отсюда только копии.
- Уточни у владельца, что именно меняется. Если правка только в `CLAUDE.md`,
  `.claude/`, `.zcode/`, `docs/` — **деплой не нужен**: этих путей нет в архиве,
  бот они не затрагивают.

## 1. Локальные проверки (без сети)

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest -q
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m bot.cli --provider demo --scenario <id>
```

Ожидаемо: `216 passed` и разбор доходит до конца, exit 0. Падения — стоп, деплой
не начинается.

## 2. Показать, что уходит

```bash
git status --short
git diff --stat
```

Убедись, что в изменениях нет `.env`, `data/bot.db`, токенов, `*.tgz`.

## 3. Бэкап базы на сервере (данные не трогаем)

```bash
ssh root@138.124.229.233 "bash /opt/mf-translator/deploy/backup.sh"
```

## 4. Архив только из нужных путей

```bash
mkdir -p .tmp
tar -czf .tmp/update.tgz AGENTS.md README.md PROGRESS.md pyproject.toml .env.example .gitignore run-bot.cmd run-cli.cmd sessions.cmd bot deploy heroines scenarios prompts tests
```

`.env`, `data/`, `.git`, `.venv`, `.tmp` в архив не входят — поэтому на сервере они
не перезаписываются.

## 5. СТОП — подтверждение перед отправкой

Покажи владельцу: `git status --short`, размер `.tmp/update.tgz`, что именно
меняется в поведении бота. Спроси прямо: **«Отправлять на сервер?»** Без «да»
остановись здесь.

```bash
scp .tmp/update.tgz root@138.124.229.233:/opt/update.tgz
```

## 6. Распаковка, права, зависимости (на сервере, одной командой)

```bash
ssh root@138.124.229.233 "cd /opt && tar -xzf update.tgz -C /opt/mf-translator && rm update.tgz && chown -R trainer:trainer /opt/mf-translator && chmod -R u=rwX,go=rX /opt/mf-translator/bot /opt/mf-translator/deploy /opt/mf-translator/scenarios /opt/mf-translator/heroines /opt/mf-translator/tests /opt/mf-translator/prompts && find /opt/mf-translator -maxdepth 1 -type f -exec chmod 644 {} + && chmod 600 /opt/mf-translator/.env && chmod 750 /opt/mf-translator/data && (chmod 600 /opt/mf-translator/data/bot.db 2>/dev/null || true) && sudo -u trainer -H /opt/mf-translator/.venv/bin/pip install -q -e /opt/mf-translator"
```

Если менялся `deploy/emotion-trainer.service` — дополнительно
`ssh root@138.124.229.233 "bash /opt/mf-translator/deploy/setup.sh"`.

В команде выше к списку `chmod` из §7 добавлен каталог `heroines/`: в `DEPLOY.md` его
нет (известное замечание, см. `docs/migration/deploy-and-testing.md` §9), а без него
файлы героинь могут остаться writable для всех.

## 7. СТОП — подтверждение перед перезапуском

Спроси: **«Перезапускать emotion-trainer?»** Перезапуск обрывает текущие диалоги
пользователей. Без «да» — остановись.

```bash
ssh root@138.124.229.233 "systemctl restart emotion-trainer"
```

## 8. Проверка (обязательно, не пропускать)

Старт бота занимает 5–6 с: подожди ~6 с и выполни строгую read-only проверку из
`docs/migration/deploy-and-testing.md` **§8.2**. За один заход она проверяет:
MainPID сервиса совпадает с `/opt/mf-translator/data/bot.pid`, в журнале именно
текущего процесса есть «Бот запущен» и «Run polling», и нет `Traceback`/`Conflict`.
При успехе печатает `OK: active, PID …, Бот запущен + Run polling, без
Traceback/Conflict`; при провале — exit ≠ 0. Ничего не меняет: только `systemctl
show`, `cat`, `journalctl`, `grep`.

```bash
ssh -o BatchMode=yes -o ConnectTimeout=10 root@138.124.229.233 bash -s <<'EOF'
set -e
main=$(systemctl show -p MainPID --value emotion-trainer)
test -n "$main" && test "$main" != 0
pid=$(cat /opt/mf-translator/data/bot.pid)
test "$main" = "$pid"
logs=$(journalctl -u emotion-trainer _PID="$main" --no-pager)
echo "$logs" | grep -q "Бот запущен"
echo "$logs" | grep -q "Run polling"
! echo "$logs" | grep -q "Traceback"
! echo "$logs" | grep -q "Conflict"
echo "OK: active, PID $main, Бот запущен + Run polling, без Traceback/Conflict"
EOF
```

Почему не `journalctl -n 20 | grep`: в истории сервера есть старые `Traceback`
(09.11) и `Conflict` (10.11 00:57), поэтому `-n 20` даёт ложные срабатывания, а если
бот уже обрабатывает апдейты — не видит строк старта. Фильтр `_PID=$main` даёт
журнал именно текущего процесса.

- `OK: …` — деплой прошёл, бот жив.
- Если проверка упала, потому что `Run polling` ещё нет (бот стартует) — подожди
  10 с и повтори; если через 30 с нет — `docs/migration/deploy-and-testing.md` §8.5.
- Быстрый «жив ли» без скрипта (§8.3):
  `ssh -o BatchMode=yes root@138.124.229.233 'systemctl is-active emotion-trainer; journalctl -u emotion-trainer -n 3 --no-pager'`.
- Если сервис упал: `journalctl -u emotion-trainer -n 100 --no-pager`; частая
  причина — забытая зависимость в `pyproject.toml` или ошибка загрузки сценария.
  Дальше — только факты из лога, без догадок; откат базы — `/var/backups/emotion-trainer/`
  (runbook §5.4).

## 9. Отчёт владельцу

Что изменено, команда деплоя, `is-active`, строки лога, что проверить в Telegram
(например, `/start` → анкета, `/scenario <id>`).
