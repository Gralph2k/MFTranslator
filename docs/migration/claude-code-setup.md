# Claude Code: как устроена конфигурация в этом проекте

Дата: 10.11.2026. Проект: `C:\Projects\MFTranslator`. Задача этого документа —
объяснить, как Claude Code получает контекст и правила проекта, что взято из DSH,
чего нет, и как проверить, что всё подхватилось.

## Коротко: что где лежит

```
CLAUDE.md                                  память проекта для Claude Code; первая строка — @AGENTS.md
AGENTS.md                                  канон правил (деплой, секреты, сценарии)
.claude/settings.json                      права: что можно без спроса, что запрещено, env
.claude/skills/writing-scenarios/SKILL.md  скил написания сценариев (копия из .dsh/skills/)
.claude/commands/test.md                   /test   — pytest
.claude/commands/smoke.md                  /smoke  — demo-прогон сценария
.claude/commands/deploy.md                 /deploy — деплой по §7 с остановками
.dsh/skills/writing-scenarios/SKILL.md     исходная копия скила для DSH (Claude Code её не читает)
docs/migration/                            пакет передачи: README, project-status, deploy-and-testing, этот файл
```

## 1. Память проекта: CLAUDE.md и `@AGENTS.md`

- Claude Code при старте сессии в папке проекта читает `CLAUDE.md` из корня (также
  допустимы `.claude/CLAUDE.md` и `CLAUDE.local.md`; файлы в подкаталогах читаются
  по требованию). Содержимое попадает в контекст как инструкции, а не как
  принудительная настройка.
- **Первая строка `@AGENTS.md` — импорт.** Claude Code разворачивает импортированный
  файл на месте; относительные пути считаются от файла, который импортирует;
  глубина — до 4 уровней. Так правила живут в одном месте (`AGENTS.md`), а второй
  копии нет.
- По умолчанию (Project instructions = `claude-md-or-agents-md`) при наличии
  `CLAUDE.md` Claude Code не читает `AGENTS.md` сам — импорт это закрывает, двойной
  загрузки не происходит. На версиях до 2.1.277 или с выключенным встроенным
  плагином `AGENTS.md` импорт работает так же — это страховка для старых сборок.
- Рекомендация Claude Code — держать каждый файл памяти меньше ~200 строк: длинные
  файлы хуже соблюдаются. `CLAUDE.md` — около 160 строк, поэтому в нём только стек,
  команды, карта кода и правила; длинные процедуры вынесены в скил и команды.
- Почему не симлинк `CLAUDE.md` → `AGENTS.md`: на Windows симлинк требует прав
  администратора или Developer Mode, а Edit/Write отказываются писать сквозь
  симлинк. Импорт переносим и работает в git-клоне без настроек.
- Проверка в сессии: `/context all` → раздел **Memory files** (там видно `CLAUDE.md`
  и импорт), `/memory` — список файлов памяти с возможностью открыть.

## 2. Скилы: `.claude/skills/`

- `.claude/skills/writing-scenarios/SKILL.md` — побайтовая копия
  `.dsh/skills/writing-scenarios/SKILL.md` (sha256 совпадает на 10.11.2026).
  Frontmatter не менялся: `name: writing-scenarios`, `description:` про разработку
  сценариев — это стандартные поля Agent Skills, Claude Code их понимает.
- Вызов: `/writing-scenarios` вручную или автоматически — Claude загружает скил,
  когда задача совпадает с `description`. Тело скила грузится только в момент
  использования, поэтому 300 строк инструкции не занимают контекст постоянно.
- **Правится в двух местах.** DSH читает `.dsh/`, Claude Code — только
  `.claude/skills/`. После правки скила синхронизируйте копию:
  ```powershell
  Copy-Item .dsh\skills\writing-scenarios\SKILL.md .claude\skills\writing-scenarios\SKILL.md -Force
  ```
- Каталог скила может быть симлинком на другой проект, но для Windows-совместимости
  здесь копия, а не ссылка.
- Новые скилы: `.claude/skills/<имя>/SKILL.md` (папка = имя команды). Личные скилы
  не для всех — `~/.claude/skills/`, они применяются во всех проектах.

## 3. Слэш-команды: `.claude/commands/`

| Файл | Команда | Что делает |
|---|---|---|
| `.claude/commands/test.md` | `/test` | pytest в `.venv`, разбор падений, отчёт |
| `.claude/commands/smoke.md` | `/smoke <id>` | demo-прогон сценария без сети и ключей |
| `.claude/commands/deploy.md` | `/deploy` | деплой на VPS по §7 с остановками перед `scp` и `restart` |

- Формат — markdown с YAML-frontmatter. Используются поля `description` (видно
  в списке команд) и `argument-hint` (подсказка аргументов); `allowed-tools` не
  задавался: права берутся из `settings.json`, а `deny`/`ask` всё равно главнее
  `allowed-tools`.
- `$ARGUMENTS` — подстановка всех аргументов команды (в `/smoke` — id сценария;
  в `/test` — путь/фильтр pytest). `$ARGUMENTS[0]` — первый аргумент по индексу.
- В актуальных версиях Claude Code пользовательские команды — частный случай
  скилов (`.claude/commands/foo.md` и `.claude/skills/foo/SKILL.md` дают одинаковый
  `/foo`); файлы в `.claude/commands/` продолжают работать. Для новых операций
  предпочтительнее скил — у него могут быть вспомогательные файлы.
- `/deploy` намеренно ничего не выполняет сам: это чек-лист с двумя остановками на
  подтверждение владельца.

## 4. Права: `.claude/settings.json`

Файл проектный (коммитится и действует на всех, кто работает в папке). Личные
исключения — `.claude/settings.local.json` (его Claude Code не коммитит).

**Логика оценки:** `deny` → `ask` → `allow`, первое совпадение решает; `deny`
нельзя перекрыть более узким `allow`. Проектные `allow`-правила включаются после
разового подтверждения доверия папке (trust dialog), `deny`/`ask` — сразу.

Что настроено и почему:

- `defaultMode: "default"` — Manual: незнакомый инструмент спрашивает один раз.
  Режимы `auto`/`bypassPermissions` в проектном файле не применяются, так что
  случайно «разрешить всё» отсюда нельзя.
- **`allow`** — рутина, которая не меняет прод и не раскрывает секреты:
  `pytest` в `.venv` и через `python`, `bot.cli`, `bot.doctor`, `bot.launcher`,
  read-only git (`status`, `diff`, `log`, `show`, `branch`, `rev-parse`, `ls-files`),
  `Get-ChildItem`. Правила продублированы для `Bash` и `PowerShell`: на Windows
  Claude Code может работать через PowerShell-инструмент, и правила одного
  инструмента не матчатся на другой.
- **`ask`** — всё, что трогает сервер или систему: `ssh`, `scp`, `rsync`, `tar`,
  `systemctl`, `chown`, `chmod`, `pip install`, `sudo` (в обеих оболочках). Деплой
  остаётся возможным, но каждое такое действие подтверждается владельцем. В `allow`
  их сознательно нет.
- **`deny`** — необратимое и секретное:
  - `Read(./.env)`, `Read(./.env.local)`, `Read(./.env.production)` — файлы
    секретов. `Read`-запрет также блокирует `cat`/`head` по этому пути и
    Edit/Write по нему.
  - `Bash(git push *)`, `Bash(git push)`, `PowerShell(git push *)` — пуш только по
    явной команде владельца.
- **`env`** — переменные для всех команд: `PYTHONIOENCODING=utf-8` (кириллица в
  консоли) и `UV_CACHE_DIR=C:\Projects\MFTranslator\.uv-cache` (`uv` не может
  писать кэш в `%LOCALAPPDATA%`). Claude Code не раскрывает `~` и `$VAR` в `env` —
  путь абсолютный; при переносе проекта его нужно поправить.

Ограничения, о которых стоит знать:

- Запреты точечные, без шаблона `.env.*`: `.env.example` — это пример окружения,
  он в git и секретов не содержит, поэтому читать его можно (агенту он нужен, чтобы
  понимать переменные и добавлять новые). Локальные варианты, которые обычно
  содержат те же секреты, запрещены явно: `.env.local`, `.env.production`. Если у
  вас появится другой локальный файл с секретами — добавьте его отдельной строкой.
- `Bash(git push *)` не ловит запуск в обход, например `git -C . push`: правила
  прав — не граница безопасности. Запрет пуша держится ещё и на `AGENTS.md`.
- Пути в правилах: `./.env` — относительно рабочей директории сессии (корень
  проекта), `Read`-правила используют gitignore-синтаксис.
- Правила прав проверяет Claude Code, а не модель: инструкция в `CLAUDE.md` не
  может разрешить то, что запрещено здесь.
- Проверка: `/permissions` — все правила и файлы, откуда они взяты; `/status` —
  какие settings-файлы загружены.

## 5. Что перенесено из DSH, а чего нет

| DSH | Claude Code | Как |
|---|---|---|
| Скил `.dsh/skills/writing-scenarios/` | `.claude/skills/writing-scenarios/` | побайтовая копия, frontmatter сохранён |
| Правила в `AGENTS.md` | `AGENTS.md` + импорт `@AGENTS.md` | единый источник, без второй копии |
| Правила деплоя и секретов | `AGENTS.md` + краткая выжимка в `CLAUDE.md` | не дублируются целиком |
| Слэш-операции «прогнать тесты/деплой» | `.claude/commands/` | написаны заново под Claude Code |

Чего в Claude Code нет и не переносилось:

- каталога `.dsh/` как настроек (Claude Code его не читает; удалять не нужно —
  он остаётся для DSH и как исходник скила);
- служебных каталогов окружения разработки (`.tmp-dsh-ui*`, `^dsh`) — на работу
  бота не влияют;
- команды DSH-тиммейтов, задач и воркфлоу — в Claude Code другие механизмы; для
  этого проекта они не нужны;
- истории сессий DSH. История проекта — в `PROGRESS.md` и `docs/migration/`.

Остальные рабочие скрипты (`run-bot.cmd`, `run-cli.cmd`, `sessions.cmd`) — это
инструменты владельца, а не конфиг DSH, они остаются как есть.

## 6. Особенности Windows / PowerShell

- venv-питон вызывать напрямую: `.\.venv\Scripts\python.exe` — активация не нужна.
- Batch-файлы `run-bot.cmd`, `run-cli.cmd`, `sessions.cmd` — **только ASCII**:
  cmd.exe читает их в OEM-кодировке и ломает UTF-8. Русский текст печатает Python.
- Кэш pytest отключён (`addopts = "-p no:cacheprovider"` в `pyproject.toml`), тесты
  создают файлы в `.tmp/` внутри проекта. Это ограничение среды разработки
  (в DSH `%TEMP%` был закрыт песочницей); в Claude Code оно обычно не мешает, но
  включать кэш обратно не нужно без проверки, что `%TEMP%` доступен.
- `uv` в этой среде не может писать кэш в `%LOCALAPPDATA%` — выручает
  `UV_CACHE_DIR` (уже прописан в `env`); вреда от него нет и там, где проблема не
  проявляется.
- Telegram с рабочей машины обычно недоступен (`ConnectTimeout`): это сеть, а не
  код. E2E — только в проде; локально тесты и `--provider demo`.
- Claude Code на Windows может выполнять команды через PowerShell-инструмент,
  поэтому разрешения заданы для `Bash` и `PowerShell` отдельно. Формы вызова
  `.venv\Scripts\python.exe` и `.\.venv\Scripts\python.exe` покрыты обе.
- JSON настроек строгий: без комментариев и висячих запятых, иначе Claude Code
  покажет Settings Error и не применит файл. Проверка:
  ```powershell
  .\.venv\Scripts\python.exe -c "import json,pathlib; json.loads(pathlib.Path('.claude/settings.json').read_text(encoding='utf-8')); print('JSON OK')"
  ```

## 7. Чего Claude Code делать не будет

- Не читает `.env` и его локальные варианты (`.env.local`, `.env.production`) —
  запрет прав; секреты не печатает. `.env.example` читать можно. Для проверки
  окружения есть `bot.doctor`.
- Не пушит в git (запрет прав) и не трогает историю.
- Не деплоит сам: `/deploy` — чек-лист с обязательными подтверждениями.
- Не подхватывает `docs/migration/*` автоматически: они попадают в контекст только
  по ссылкам из `CLAUDE.md` (по требованию).

## 8. Как проверить, что всё подхватилось

В сессии Claude Code в папке `C:\Projects\MFTranslator`:

1. `/context all` — в **Memory files** есть `CLAUDE.md` (и `AGENTS.md` через
   импорт); в списке скилов — `writing-scenarios`.
2. `/memory` — список файлов памяти и их расположение.
3. `/status` — в **Setting sources** есть `Project settings` (значит,
   `.claude/settings.json` прочитан).
4. `/permissions` — правила `allow`/`ask`/`deny` из проектного файла.
5. Начните вводить `/` — в списке видны `test`, `smoke`, `deploy`,
   `writing-scenarios`.
6. Спросите: «какие правила проекта и как запускать тесты?» — ответ должен
   ссылаться на деплой на VPS, запрет `git push`, `.env`, `.venv`, контракт
   сценариев.
7. Попросите прочитать `.env` — отказ из-за `deny`.
8. Попросите `git push` — отказ из-за `deny`.
9. `/test` — `216 passed`, exit 0.
10. `/smoke eva_message` — разбор доходит до конца, exit 0.
11. В терминале вне сессии: `claude doctor` — проверка установки и настроек.

## 9. Чек-лист первого запуска

1. Открыть `C:\Projects\MFTranslator` в Claude Code, подтвердить доверие папке
   (это включит проектные `allow`-правила).
2. Проверить загрузку памяти: `/context all`, `/memory`.
3. Проверить настройки: `/status`, `/permissions`.
4. `.\.venv\Scripts\python.exe -m pytest -q` → `216 passed`.
5. `.\.venv\Scripts\python.exe -m bot.cli --provider demo --scenario eva_message`
   (и `first_message`) → анкета, реплики, разбор, exit 0.
6. `.\.venv\Scripts\python.exe -m bot.doctor` → DeepSeek `OK`; Telegram
   `ConnectTimeout` с этой машины — ожидаемо.
7. Убедиться, что защита работает: чтение `.env` и `git push` отклоняются.
8. `git status` — работать, не теряя незакоммиченную итерацию героинь
   (см. `docs/migration/README.md` и `project-status.md`).
9. Прочитать `AGENTS.md`, затем `docs/migration/deploy-and-testing.md` перед первым
   деплоем.

## 10. Что менять и где

- **Правила поведения** — в `AGENTS.md` (канон, его читают и DSH, и Claude Code
  через импорт). В `CLAUDE.md` — только то, что относится к работе Claude Code:
  стек, команды, карта кода, ссылки.
- **Поведение прав, env** — `.claude/settings.json`.
- **Скил** — `.dsh/skills/...` и `.claude/skills/...` вместе (копия).
- **Типовые операции** — `.claude/commands/*.md`.
- **Документы миграции** — `docs/migration/`: `README.md` (обзор пакета),
  `project-status.md` (снимок состояния), `deploy-and-testing.md` (runbook),
  `claude-code-setup.md` (этот файл).
- **Известные расхождения** (аудит 10.11.2026, полный список — `project-status.md` §9;
  в этой конфигурации учтены): `SAFETY_RESOURCES` пуст и локально, и в проде — бот
  отвечает fallback-текстом с 112, реальные контакты вписывает только владелец;
  `/start` в `deploy/DEPLOY.md` §6 описан старой логикой (сейчас — случайная героиня);
  список `chmod` в §7 не содержит `heroines/` — в `/deploy` каталог добавлен; время
  деплоя в `PROGRESS.md` — серверное (CET), к МСК прибавлять 2 часа зимой.

## 11. Что проверено, а что нет

Проверено 10.11.2026:

- формат и поля сверены с актуальной документацией `docs.claude.com` (страницы
  memory, settings, permissions, skills, tools reference);
- `.claude/settings.json` — валидный JSON (`json.loads`), правила разобраны:
  `deny` → `ask` → `allow`, пути и оболочки совпадают с командной строкой из
  `CLAUDE.md`; запреты на `.env` точечные (`.env`, `.env.local`, `.env.production`) —
  `.env.example` читается свободно;
- `.claude/skills/writing-scenarios/SKILL.md` побайтово равен исходнику (sha256);
- все пути, упомянутые в `CLAUDE.md` и командах, существуют в проекте;
- `.\.venv\Scripts\python.exe -m pytest -q` → `216 passed`;
- неинтерактивный demo-прогон (`@('...') | ... -m bot.cli --provider demo
  --scenario eva_message`) доходит до разбора, exit 0.

Не проверено (выполняет владелец при первом запуске):

- фактическая загрузка файлов в живой сессии Claude Code — пункты 8.1–8.5 и шаги
  1–3 чек-листа выше;
- поведение прав в конкретной версии Claude Code: имена полей и правил взяты из
  документации, но версии отличаются (например, `AGENTS.md` напрямую читается
  начиная с 2.1.277; в этой конфигурации он подключён импортом, что работает и
  раньше);
- интерактивный режим `/test`, `/smoke`, `/deploy` в Claude Code: команды
  написаны как чек-листы, но не запускались моделью изнутри Claude Code.
