# Передача проекта в Claude Code

Пакет для продолжения работы над тренажёром в Claude Code вместо DSH.
Дата снимка: **10.11.2026, 13:40 МСК**. Проект: `C:\Projects\MFTranslator`.

Бот **работает в проде**, последняя итерация («Героини: Вера и Ева») задеплоена
сегодня в 13:32 МСК. Всё, что нужно новому агенту, — в этом каталоге и в
[CLAUDE.md](../../CLAUDE.md).

---

## Статус одним экраном

| Что | Состояние | Подтверждение |
|---|---|---|
| Бот в проде | работает, long polling | `systemctl is-active emotion-trainer` → `active`; журнал: «Бот запущен» + «Run polling», без `Traceback`/`Conflict` |
| Код на сервере | **совпадает с локальным** | sha256 `bot/engine.py`, `bot/heroines.py`, `bot/scenario.py`, `bot/prompts.py` совпали |
| Тесты | **216 passed** (3.3 с) | `.\.venv\Scripts\python.exe -m pytest -q` |
| Demo-прогоны | `eva_message` и `first_message` доходят до разбора, exit 0 | `-m bot.cli --provider demo --scenario <id>` |
| Модель (DeepSeek) | ключ работает | `python -m bot.doctor` → `[OK] DeepSeek` |
| Telegram с рабочей машины | **недоступен** (ConnectTimeout) — это сеть, не код | `python -m bot.doctor`; прод ходит в Telegram из Германии нормально |
| Git | `main`, впереди `origin/main` на 1 коммит; **незакоммичено** 31 файл (+1406/−354) и 12 untracked путей | `git status`, `git diff --shortstat` |
| Прод-база | 80 КБ, бэкап перед деплоем есть | `/opt/mf-translator/data/bot.db`; `/var/backups/emotion-trainer/bot-2026-11-10_1131.db` |
| `SAFETY_RESOURCES` | **пусто и локально, и в проде** (на сервере `SAFETY_RESOURCES=` + пробел → `None`) | `load_settings()` на сервере: `safety_resources is None`; бот отдаёт fallback-текст с 112 |

Что сделано: две героини (Вера — переписка → созвон → свидание; Ева — переписка),
меню «героиня → сценарии», случайный `/start` с антиповтором, разбор по рубрике,
safety-слой, `bot.doctor`, `launcher`, `sessions.cmd` с синхронизацией с VPS,
деплой через systemd. Подробности и хвост истории — [project-status.md](project-status.md)
и [PROGRESS.md](../../PROGRESS.md).

---

## Что читать и в каком порядке

**Агент (Claude Code):** `CLAUDE.md` подхватывается автоматически из корня; он
импортирует `AGENTS.md`. Дальше: [project-status.md](project-status.md) —
где проект сейчас; [deploy-and-testing.md](deploy-and-testing.md) — как проверять
и деплоить; [claude-code-setup.md](claude-code-setup.md) — как устроена
конфигурация Claude Code в этом проекте.

**Человек (владелец):** `CLAUDE.md` → этот файл → [project-status.md](project-status.md).
Если что-то из «Следующих шагов» ниже хочется начать сразу — так и надо.

---

## Состав пакета

| Файл | Что внутри |
|---|---|
| [CLAUDE.md](../../CLAUDE.md) | Проектная память Claude Code: стек, команды, карта кода, жёсткие правила. Первой строкой `@AGENTS.md` — правила не дублируются. |
| [.claude/settings.json](../../.claude/settings.json) | Права: тесты/чтение разрешены, `git push` и чтение `.env` запрещены, деплой — только осознанно. |
| [.claude/skills/writing-scenarios/SKILL.md](../../.claude/skills/writing-scenarios/SKILL.md) | Перенесённый скил написания сценариев (из `.dsh/skills/`). |
| [.claude/commands/](../../.claude/commands/) | Слэш-команды `/test`, `/smoke`, `/deploy` — типовые операции проекта. |
| [project-status.md](project-status.md) | Снимок статуса: инвентарь героинь/сценариев, что готово, git-состояние, открытые вопросы, риски. |
| [deploy-and-testing.md](deploy-and-testing.md) | Runbook: локальная установка, проверки, деплой на VPS, бэкапы/восстановление, типовые поломки, read-only проверка прода. |
| [claude-code-setup.md](claude-code-setup.md) | Как Claude Code читает эту конфигурацию, что перенесено из DSH, чего нет, чек-лист первого запуска. |
| [.zcode/](../../.zcode/) | Конфигурация ZCode (добавлена 11.11.2026): `skills/writing-scenarios` (копия), `commands/` — `/test`, `/smoke`, `/deploy` под Git Bash. Правила — те же `AGENTS.md`, ZCode читает их напрямую, без импорта. |

Исходные документы проекта остаются главными: [AGENTS.md](../../AGENTS.md)
(правила), [README.md](../../README.md) (как устроено), [PROGRESS.md](../../PROGRESS.md)
(история решений и следующих шагов), [deploy/DEPLOY.md](../../deploy/DEPLOY.md)
(деплой), [docs/superpowers/specs/2026-11-10-heroines-eva-design.md](../superpowers/specs/2026-11-10-heroines-eva-design.md)
(дизайн текущей итерации).

---

## Чек-лист первого запуска в Claude Code

1. Открыть в Claude Code папку `C:\Projects\MFTranslator` и проверить, что
   `CLAUDE.md` подхватился: спросить «какие правила проекта и как запускать
   тесты?» — ответ должен ссылаться на агентов, деплой и `.venv`.
2. `.\.venv\Scripts\python.exe -m pytest -q` → ждём `216 passed`.
3. `.\.venv\Scripts\python.exe -m bot.cli --provider demo --scenario eva_message`
   (и `--scenario first_message`) → анкета/сцена, реплики, разбор, exit 0.
4. `.\.venv\Scripts\python.exe -m bot.doctor` → DeepSeek `OK`; Telegram
   `ConnectTimeout` с этой машины **ожидаем** (нужен VPN/прокси, прод живёт отдельно).
5. Продакшен read-only:
   `ssh -o BatchMode=yes root@138.124.229.233 "systemctl is-active emotion-trainer; journalctl -u emotion-trainer -n 5 --no-pager"`
   → `active` и свежие строки без `Traceback`/`Conflict`.
6. Убедиться, что защита работает: попросить агента прочитать `.env` и запушить —
   оба должны быть отклонены конфигурацией прав.
7. `git status` — работать, не теряя незакоммиченное (см. следующий раздел).

---

## Незакоммиченная работа — главный риск

Вся текущая итерация (героини, Ева, меню, `session_sync`, тесты, дизайн-док,
`spike/`) лежит **только в рабочей копии**. Правила проекта разрешают локальные
коммиты (`git push` — только по команде владельца), поэтому перед переключением
инструментов разумно закоммитить всё локально одним коммитом. Это не сделано
специально: миграционный пакет не трогает историю git.

Что именно не закоммичено:

- изменены: `AGENTS.md`, `PROGRESS.md`, `README.md`, `.dsh/skills/...`,
  `bot/{call_screen,cli,engine,menus,profile_card,prompts,scenario,session_view,storage,telegram_bot}.py`,
  `deploy/DEPLOY.md`, `run-cli.cmd`, `sessions.cmd`, все `scenarios/*/scenario.json`,
  фото `scenarios/first_message/images/profile_*.jpg`, 6 файлов `tests/`;
- untracked: `bot/heroines.py`, `bot/session_sync.py`, `tests/test_eva.py`,
  `tests/test_heroines.py`, `tests/test_session_sync.py`, `heroines/`,
  `scenarios/eva_message/`, `prompts/eva-profile-nano-banana.md`, `docs/`, `spike/`
  — плюс уже созданные в рамках миграции `CLAUDE.md` и `.claude/` (итого 12 путей).

---

## Следующие шаги (из PROGRESS.md и дизайн-спеки, по приоритету)

1. **Доделать фото Евы** по `prompts/eva-profile-nano-banana.md`: локально готов
   1 кадр из 4 (`scenarios/eva_message/images/profile_1.jpg`, рядом референс
   `eva_base.jpg`), `profile_2..4` ещё нет; в проде лежит только `eva_base.jpg` v1,
   поэтому бот присылает текстовую карточку (это не ошибка). Какая версия кадров
   утверждена — знает только владелец.
2. **`SAFETY_RESOURCES` пуст и локально, и в проде** (в серверном `.env` значение из
   пробела → `Settings.safety_resources is None`; бот подставляет fallback-текст с
   112). Реальные контакты помощи вписывает только владелец — из кода их взять
   нельзя. Без этого публичный запуск не начинать.
3. Живая проверка героинь в Telegram: `/start` (случайная героиня), `/menu`,
   «Продолжить» после разбора, отсутствие `friday_evening`/`reunion_call` в меню.
4. Дальше: прогресс между сессиями, созвон/свидание Евы, третья героиня.
5. `spike/` — эксперименты с оценкой разбора (судья, пробы), в прод не входит;
   `docs/superpowers/` — спеки, тоже не код.

---

## Правила, которые нельзя потерять при смене инструмента

- **Любое изменение кода, сценариев или конфигурации → деплой на VPS и перезапуск
  бота.** «Локально работает» ничего не доказывает. Порядок — §7
  [deploy/DEPLOY.md](../../deploy/DEPLOY.md), кратко: тесты → бэкап → архив → `chown`
  → `pip install -e .` → `systemctl restart emotion-trainer` → `is-active` + журнал.
  `.env` и `data/bot.db` на сервере не перезаписываются.
- **`git push` — только по явной команде владельца.** Коммиты локально можно.
- **Секреты только в `.env`** (файл в `.gitignore`): не печатать значения, не
  коммитить, не подставлять в сценарии.
- **Сценарии — данные**, контракт — `tests/test_scenarios_contract.py`; личность
  героини — `heroines/<slug>/heroine.json`; фотографии — в `scenarios/<id>/images/`.
  Перед новым сценарием — скил `writing-scenarios`.
- **Перед сдачей:** `pytest -q` и demo-прогон изменённого сценария.

---

## Риски и особенности, которые всплывут

- **Telegram с рабочей машины заблокирован** — это нормальный фон, не баг. E2E
  проверяется только на проде (`/start` в Telegram), локально — тесты и demo-режим.
- **Локальный `run-bot.cmd` не запускать, пока прод работает** с тем же токеном:
  получится `Conflict: terminated by other getUpdates`, и один из экземпляров
  перестанет получать апдейты. Локально — только `bot.cli --provider demo`.
- **Сервер живёт в `Europe/Berlin` (CET), в МСК — +2 ч зимой.** `journalctl`,
  `cron`, `systemctl` показывают серверное время; деплой 10.11 записан в
  `PROGRESS.md` как «11:32 МСК», а это `11:32 CET` = 13:32 МСК. При сверке времени
  не путать (прочие найденные расхождения в документации — `project-status.md` §9).
- **Два источника правил**: `AGENTS.md` (DSH/Codex) остаётся каноном, `CLAUDE.md`
  импортирует его. Правки правил — только в `AGENTS.md`, чтобы не разошлись.
- **DSH-специфичное не нужно Claude Code**: `.dsh/`, `^dsh/`-каталоги, `run-*.cmd`
  остаются как есть; удалять их перед миграцией не стоит (это рабочие скрипты
  владельца, а не конфиг DSH).
- **Нет CI и нет lock-файла** — тесты гоняются вручную, зависимости ставятся из
  `pyproject.toml` (`pip install -e .`), на сервере Python 3.12.16, локально 3.13.
- **Прод-база — единственная копия диалогов** на сервере; локальный `data/bot.db`
  отстаёт. `sessions.cmd` сводит обе; живую базу не копировать файлом — только
  `sqlite3 .backup` / `deploy/backup.sh`.
- **Git-клона на сервере нет, known-good архива тоже нет** — откат кода возможен
  только из локальной копии (поэтому незакоммиченную работу нельзя терять). Перед
  следующим деплоем разумно сохранить текущий рабочий архив как rollback-точку.
- **Миграционный пакет ничего не деплоит**: `CLAUDE.md`, `.claude/`, `docs/migration/`
  в боевой архив не входят, на работу бота не влияют. Правки в них деплоя не требуют.

---

## Инициализация в ZCode (сделано 11.11.2026)

Пакет адаптирован под ZCode: `AGENTS.md` подхватывается автоматически (без
`CLAUDE.md`-импорта), скил и команды скопированы в `.zcode/`. Команды переведены
с PowerShell на Git Bash (`PYTHONIOENCODING=utf-8`, `printf`-пайп, heredoc для ssh).
Отличие от Claude Code: у ZCode нет проектного `settings.json` с правами — запреты
на чтение `.env` и `git push` держатся только на правилах `AGENTS.md` и режиме
разрешений сессии.

Проверено 11.11.2026: `pytest -q` → **216 passed**; demo-прогоны `eva_message` и
`first_message` → разбор, exit 0; `bot.doctor` → DeepSeek `OK`, Telegram
`ConnectTimeout` (ожидаемо). **SSH до VPS из этой сети с 11.11 не проходит**
(`connect to host 138.124.229.233 port 22: Connection timed out`) — read-only
проверку прода и деплой делать только когда сеть снова пропускает (VPN); пока не
проверено, что прод жив.

## Откат к DSH

Ничего не удалено: `.dsh/skills/writing-scenarios/SKILL.md`, `AGENTS.md`, все
скрипты и `PROGRESS.md` на месте. Claude Code-файлы (`CLAUDE.md`, `.claude/`)
добавлены рядом и DSH не мешают. Вернуться — просто открыть папку в DSH, как раньше.

---

## Проверено (evidence, 10.11.2026)

```
$ .\.venv\Scripts\python.exe -m pytest -q            → 216 passed in 3.33s
$ ... -m bot.cli --provider demo --scenario eva_message   → разбор «9 из 12», exit 0
$ ... -m bot.cli --provider demo --scenario first_message → разбор, exit 0
$ ... -m bot.doctor    → [OK] DeepSeek; [ОШИБКА] Telegram ConnectTimeout (сеть)
$ ssh root@138.124.229.233 "systemctl is-active emotion-trainer" → active
$ ssh ... "journalctl -u emotion-trainer -n 5" → «Бот запущен», «Run polling», без Traceback
$ ssh ... "sha256sum bot/engine.py ..." → совпадает с локальным
```
