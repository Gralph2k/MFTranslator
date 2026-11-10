@AGENTS.md

# CLAUDE.md — тренажёр эмоционального интеллекта

Проектная память Claude Code. Правила и запреты — в `AGENTS.md` (подключён первой
строкой и здесь не дублируется). Этот файл: стек, команды, карта кода, жёсткие
правила и то, что легко забыть.

## Что за проект

Telegram-бот: пользователь переписывается с героиней — виртуальной женщиной
с характером, настроением и памятью о разговоре — и после диалога получает разбор
своих ходов по рубрике. Тренируется эмпатия: заметить состояние, спросить вместо
догадки, выдержать чужое чувство. Это тренажёр, а не симулятор отношений: рамка
проговаривается в первом сообщении бота.

Сейчас в проде две героини — Вера (переписка → созвон → свидание) и Ева
(переписка); меню «героиня → её сценарии», случайный `/start` с антиповтором.
«Локально работает» ничего не доказывает: пользователи ходят через VPS.

## Стек

- Python 3.13 локально (на VPS 3.12), aiogram 3, SQLite, DeepSeek API, Pillow.
- Зависимости — `pyproject.toml`, lock-файла нет; `[dev]` — pytest + pytest-asyncio.
- Окружение — `.venv` в корне. Windows: PowerShell, venv-питон вызывается напрямую,
  активация не нужна.
- Кэш pytest отключён (`addopts = "-p no:cacheprovider"` в `pyproject.toml`), тесты
  создают файлы в `.tmp/` внутри проекта — ограничение среды разработки. Не включать
  обратно без проверки, что `%TEMP%` действительно доступен.
- Если `uv` не пишет кэш в `%LOCALAPPDATA%` — `$env:UV_CACHE_DIR="$PWD\.uv-cache"`
  (в `.claude/settings.json` уже выставлено).
- Telegram с рабочей машины обычно недоступен (`ConnectTimeout`) — это сеть, не код.
  E2E проверяется только в проде, локально — тесты и demo-режим.

## Команды (из корня проекта, PowerShell)

```powershell
# тесты; ожидаемый baseline на 10.11.2026 — 216 passed, ~3.5 с
.\.venv\Scripts\python.exe -m pytest -q

# demo-прогон сценария без сети и ключей; интерактивно: реплики в консоль,
# /finish — разбор, /state — состояние персонажа
.\.venv\Scripts\python.exe -m bot.cli --provider demo --scenario eva_message

# то же неинтерактивно (stdin закрывается — CLI сам печатает разбор)
@('Привет, как ты?','Понимаю, что устала.') | .\.venv\Scripts\python.exe -m bot.cli --provider demo --scenario first_message

# проверка окружения: токен, прокси, ключ модели
.\.venv\Scripts\python.exe -m bot.doctor

# запущен ли локальный бот и какой PID (диалоги в базе не трогает)
.\.venv\Scripts\python.exe -m bot.launcher status

# оператор: последние сессии и стенограммы (локальная база + свежая копия серверной)
.\sessions.cmd

# запуск бота на этой машине: остановит предыдущий, проверит окружение
.\run-bot.cmd
```

Доступные сценарии: `first_message`, `first_call`, `first_date`, `eva_message`.
`friday_evening` и `reunion_call` выключены (`enabled: false`) — не «чинить».
Новый сценарий — только по скилу `writing-scenarios` (`.claude/skills/`).

## Карта кода

```
bot/scenario.py      загрузка scenarios/<id>/scenario.json, слияние с личностью героини, контракт
bot/heroines.py      каталог героинь: порядок, «продолжить», случайный старт с антиповтором
bot/state.py         состояние: mood + trust/openness/energy в 0..1, notes
bot/prompts.py       вся педагогика: промпт персонажа, наблюдатель состояния, промпт разбора
bot/engine.py        ход диалога, обновление состояния, финальный разбор и его рендер
bot/llm.py           DeepSeek-клиент с повторами + FakeLLM/DemoLLM для тестов
bot/storage.py       SQLite: пользователи, сессии, разборы, миграции схемы
bot/config.py        Settings из окружения и .env
bot/doctor.py        python -m bot.doctor: токен, прокси, ключ, сеть
bot/launcher.py      остановка предыдущего бота и PID-файл
bot/menus.py         клавиатуры: героини → сценарии → «продолжить» после разбора
bot/faces.py         выбор кадра эмоции по состоянию (scenarios/<id>/images/)
bot/profile_card.py  карточка анкеты: UI рисуется кодом поверх фото
bot/call_screen.py   экран исходящего звонка: тоже код поверх фото
bot/safety.py        кризисные темы → реальные каналы помощи, сцена обрывается
bot/session_view.py  список сессий и стенограмма для оператора
bot/session_sync.py  объединение локальной базы с копией серверной (read-only)
bot/cli.py           игра в терминале: --provider demo|deepseek, --scenario <id>
bot/telegram_bot.py  aiogram 3: команды, диалог, разбор
bot/tls.py           корни TLS из хранилища Windows (truststore), чтобы httpx не падал на VPN/антивирусе
```

```
heroines/<slug>/heroine.json   личность: имя, возраст, профессия, traits, speech, profile
scenarios/<id>/scenario.json   сцена: heroine, relation, secrets, levers, rubric, frame, red_flags
scenarios/<id>/images/         фотографии именно этой сцены
prompts/                       промпты для генерации фото (кадры генерирует владелец)
tests/                         pytest: контракт, героини, сценарии, faces, storage, trainer
deploy/                        DEPLOY.md (§7 — деплой), setup.sh, backup.sh, systemd-юнит
docs/superpowers/specs/        дизайн-спеки итераций
docs/migration/                пакет передачи в Claude Code: статус, runbook, эта инструкция
.claude/                       конфигурация Claude Code: skills/, commands/, settings.json
.dsh/skills/                   исходная копия скила для DSH (в Claude Code — .claude/skills/)
```

## Жёсткие правила

1. **Любое изменение кода, сценариев или конфигурации деплоится на VPS и
   перезапускает бота.** Сервер: `root@138.124.229.233`, код в `/opt/mf-translator`,
   сервис `emotion-trainer`. Порядок строго по §7 `deploy/DEPLOY.md`: тесты →
   бэкап `deploy/backup.sh` → архив → `scp` → `chown`/`chmod` → `pip install -e .` →
   `systemctl restart emotion-trainer` → `systemctl is-active` и `journalctl`
   («Бот запущен», «Run polling», без `Traceback` и `Conflict`).
2. **`git push` — только по явной команде владельца.** Локальные коммиты можно.
   `git push` в этой конфигурации запрещён правилами прав.
3. **Секреты только в `.env`** (в `.gitignore`): не читать, не печатать, не
   коммитить, не подставлять в сценарии. `.env` и `data/bot.db` на сервере при
   деплое не перезаписываются — их нет в архиве.
4. **Сценарии — данные, а не код.** Контракт — `tests/test_scenarios_contract.py`
   (6 пунктов рубрики, `turn_limit` 8–12, стартовая `openness` ≤ 0.25, у каждой
   ловушки объяснение, у включённого сценария есть героиня). Личность героини —
   `heroines/<slug>/heroine.json`, фотографии — в папке сцены; в `scenario.json`
   нет `persona` и `profile`.
5. **Перед сдачей:** `pytest -q` и demo-прогон изменённого сценария.
6. **Прод-база — единственная копия диалогов.** Не копировать живой файл
   (`sqlite3 .backup` / `deploy/backup.sh`), не править базу на сервере руками, не
   удалять `data/bot.db`.
7. Правила меняются в `AGENTS.md` (один источник), а не в этом файле. Поправка
   поведения Claude Code — здесь; расхождения между файлами — баг.

## Чего в проекте нет / не делать

- Нет CI и нет lock-файла: тесты только вручную, зависимости — из `pyproject.toml`.
- `SAFETY_RESOURCES` пуст и локально, и в проде (в `.env` значение из пробела →
  `Settings.safety_resources is None`; бот отвечает fallback-текстом с 112). Для
  публичного запуска его вписывает владелец. **Не выдумывать контакты помощи** и не
  подставлять правдоподобные номера.
- Не переписывать `.env`, не печатать его значения, не «проверять» токены
  посторонними запросами; для проверки есть `bot.doctor`.
- Не деплоить и не перезапускать сервис без явного подтверждения владельца,
  не менять `deploy/*.sh` под задачи, не трогать `/opt/mf-translator/.env`.
- Не делать `git push`, не переписывать историю, не удалять незакоммиченную работу
  (она сейчас единственная копия итерации героинь).
- Не «оживлять» выключенные сценарии и не менять существующие под новый замысел:
  для нового сценария — скил и отдельная папка.
- Не читать `.env` и его локальные варианты (`.env.local`, `.env.production`):
  правила прав запрещают. `.env.example` — можно, там нет секретов. Не менять
  `run-*.cmd` на не-ASCII: cmd.exe читает их в OEM-кодировке и ломает UTF-8.
- `.dsh/`, `^dsh/`, `.tmp-dsh-ui*` — служебные каталоги окружения разработки;
  не удалять и не переносить.

## Где читать дальше

- `AGENTS.md` — правила (канон). `README.md` — как устроен бот и команды бота.
- `PROGRESS.md` — история решений и «Следующие шаги» (хвост файла — самое свежее).
- `deploy/DEPLOY.md` §7 — единственный правильный порядок деплоя.
- `docs/migration/README.md` — пакет передачи в Claude Code: статус одним экраном,
  что читать, главные риски.
- `docs/migration/project-status.md` — где проект сейчас, инвентарь героинь и
  сценариев, git-состояние, открытые вопросы.
- `docs/migration/deploy-and-testing.md` — runbook: локальные проверки, деплой,
  бэкапы, типовые поломки, read-only проверка прода.
- `docs/migration/claude-code-setup.md` — как устроена эта конфигурация Claude Code.
- `docs/superpowers/specs/2026-11-10-heroines-eva-design.md` — дизайн текущей итерации.
