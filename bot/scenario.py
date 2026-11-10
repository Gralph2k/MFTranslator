"""Сценарий: персонаж, ситуация, рубрика разбора. Данные, а не код.

Личность героини живёт отдельно — в `heroines/<slug>/heroine.json` — и одна на
все её сценарии. Сценарий хранит только сцену и ссылку `heroine`; загрузчик
собирает `Persona` и `Profile` из файла героини.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SCENARIO_DIR = ROOT / "scenarios"
SCENARIO_FILE = "scenario.json"
IMAGES_DIR = "images"


class ScenarioError(ValueError):
    """Сценарий не загрузился или в нём не хватает полей."""


@dataclass(frozen=True)
class Persona:
    name: str
    age: int
    job: str
    relation: str
    traits: list[str]
    speech: str


@dataclass(frozen=True)
class Profile:
    """Анкета из приложения знакомств: то, что игрок видит до первой реплики.

    Наличие анкеты — это признак переписки: бот показывает карточку до хода
    игрока и не предлагает описывать действия вроде «протягиваю цветок».
    """

    about: str
    hobbies: list[str]
    interests: list[str]
    photos: list[str]
    # Подписи под конкретным фото: работа и «о себе» на первом, интересы
    # на втором, чего ищет — на третьем. Так текст не дублируется блоком «О себе».
    captions: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class RubricItem:
    id: str
    label: str
    max: int
    what: str


@dataclass(frozen=True)
class Scenario:
    id: str
    title: str
    language: str
    one_liner: str
    backstory: str
    opening: str
    persona: Persona
    situation: str
    secrets: list[str]
    initial_state: dict[str, Any]
    turn_limit: int
    helps: list[str]
    hurts: list[str]
    rubric: list[RubricItem]
    debrief_tone: str
    # Рамка разговора: кто они друг другу и что это за сцена. Без неё промпт
    # описывал бы только пару, живущую вместе, и врал бы про первое свидание.
    frame: str = ""
    # Что значит «шаг к нему» именно здесь: дома это объятие, в кофейне — продолжение.
    contact_hint: str = ""
    # Навык одним предложением: что именно тренирует сценарий.
    skill: str = ""
    # Анкета из приложения знакомств. Есть анкета — значит переписка, а не встреча.
    profile: Profile | None = None
    # Красные линии: за них персонаж может оборвать разговор и уйти.
    red_flags: tuple[str, ...] = ()
    # Как идёт разговор: "in_person" (видит лицо), "chat" (только текст) или
    # "call" (только голос). В переписке и созвоне лицо показать нельзя.
    medium: str = "in_person"
    # Сценарий-продолжение: id сценария, переписка которого была до этой сцены.
    # Бот подтягивает последнюю попытку игрока, а если её нет — канон.
    continues: str = ""
    # Канонная переписка: используется, если у игрока нет прошлой попытки.
    canon_history: tuple[dict[str, str], ...] = ()
    # Папка сценария: рядом со scenario.json лежит images/ с лицом персонажа.
    dir: Path = SCENARIO_DIR
    # Порядок в меню: меньшее число — раньше. По умолчанию все равны.
    order: int = 100
    # Финал по лимиту ходов: за сколько реплик она начинает предупреждать, что пора,
    # и по каким причинам уходит (устала, метро, гости). Без этого разговор
    # обрывался бы на лимите без объяснения.
    wrap_up_at: int = 3
    wrap_up_reasons: tuple[str, ...] = ()
    # Героиня, которой принадлежит сценарий: id из heroines/<slug>/heroine.json.
    heroine: str = ""
    # Выключенный сценарий остаётся в репозитории, но не попадает в меню,
    # случайный старт и «продолжить».
    enabled: bool = True
    # Заготовки реплик для CLI-демо: у каждой героини свой голос.
    demo_replies: tuple[str, ...] = ()

    @property
    def max_score(self) -> int:
        return sum(item.max for item in self.rubric)

    @property
    def faces_dir(self) -> Path:
        return self.dir / IMAGES_DIR

    @property
    def is_correspondence(self) -> bool:
        """Переписка в приложении: карточка анкеты и только текстовые сообщения."""
        return self.medium == "chat"

    @property
    def is_call(self) -> bool:
        """Созвон: лица нет, только голос, но и анкеты уже нет."""
        return self.medium == "call"

    @property
    def shows_face(self) -> bool:
        """Можно ли показывать её лицо. В переписке и на созвоне — нет."""
        return self.medium == "in_person"


def _require(data: dict[str, Any], key: str, kind: type, where: str) -> Any:
    if key not in data:
        raise ScenarioError(f"{where}: нет поля '{key}'")
    value = data[key]
    if not isinstance(value, kind):
        raise ScenarioError(f"{where}: поле '{key}' должно быть {kind.__name__}")
    return value


def _build_persona(
    data: dict[str, Any],
    persona_raw: dict[str, Any] | None,
    heroine: Any,
) -> Persona:
    """Собирает Persona: из сценария (legacy/тесты) или из файла героини."""
    if persona_raw is not None:
        persona = Persona(
            name=_require(persona_raw, "name", str, "persona"),
            age=_require(persona_raw, "age", int, "persona"),
            job=_require(persona_raw, "job", str, "persona"),
            relation=_require(persona_raw, "relation", str, "persona"),
            traits=list(_require(persona_raw, "traits", list, "persona")),
            speech=_require(persona_raw, "speech", str, "persona"),
        )
    else:
        relation = str(data.get("relation") or "").strip()
        if not relation:
            raise ScenarioError("сценарий: нужна связь с героиней (relation)")
        persona = Persona(
            name=heroine.name,
            age=heroine.age,
            job=heroine.job,
            relation=relation,
            traits=list(heroine.traits),
            speech=heroine.speech,
        )

    speech_extra = str(data.get("speech_extra") or "").strip()
    if speech_extra:
        persona = replace(persona, speech=f"{persona.speech.rstrip()} {speech_extra}")
    return persona


def scenario_from_dict(
    data: dict[str, Any],
    directory: Path | None = None,
    heroine: Any = None,
) -> Scenario:
    """Собирает сценарий из JSON.

    `directory` — папка, где лежит его images/. `heroine` — данные из
    `heroines/<slug>/heroine.json`, если сценарий ссылается на героиню;
    без них сценарий может нести встроенную persona (выключенные старые сценарии,
    минимальные словари в тестах).
    """
    if not isinstance(data, dict):
        raise ScenarioError("сценарий должен быть объектом JSON")

    opening = data.get("opening", "")
    if not isinstance(opening, str):
        raise ScenarioError("сценарий: поле 'opening' должно быть строкой")

    persona_raw = data.get("persona")
    if persona_raw is not None and not isinstance(persona_raw, dict):
        raise ScenarioError("сценарий: поле 'persona' должно быть объектом")
    if persona_raw is None and heroine is None:
        raise ScenarioError("сценарий: нет поля 'persona' и не указана героиня")

    profile_raw = data.get("profile")
    heroine_slug = str(data.get("heroine") or "").strip()

    medium = str(data.get("medium") or "").strip().lower()
    if not medium:
        has_profile = profile_raw is not None or (
            heroine is not None and getattr(heroine, "profile", None) is not None
        )
        medium = "chat" if has_profile else "in_person"
    if medium not in {"in_person", "chat", "call"}:
        raise ScenarioError("сценарий: medium должен быть in_person, chat или call")

    profile: Profile | None = None
    if medium == "chat":
        if profile_raw is not None:
            profile = profile_from_dict(profile_raw)
        elif heroine is not None:
            profile = getattr(heroine, "profile", None)
        if profile is None:
            raise ScenarioError("chat: нужна анкета (profile)")
    # Созвон и встреча анкету не показывают: Profile остаётся None, и старые
    # контракты (у переписки анкета есть, у сцены вживую — нет) не ломаются.

    persona = _build_persona(data, persona_raw, heroine)

    levers = _require(data, "levers", dict, "сценарий")
    rubric_raw = _require(data, "rubric", list, "сценарий")
    if not rubric_raw:
        raise ScenarioError("рубрика пустая: разбор будет бессмысленным")

    rubric = [
        RubricItem(
            id=_require(item, "id", str, "rubric[]"),
            label=_require(item, "label", str, "rubric[]"),
            max=_require(item, "max", int, "rubric[]"),
            what=_require(item, "what", str, "rubric[]"),
        )
        for item in rubric_raw
    ]

    continues = str(data.get("continues") or "").strip()
    canon_history = _history(data.get("canon_history"), "canon_history")
    wrap_up_at, wrap_up_reasons = _wrap_up(data.get("wrap_up"))

    return Scenario(
        id=_require(data, "id", str, "сценарий"),
        title=_require(data, "title", str, "сценарий"),
        language=data.get("language", "ru"),
        one_liner=_require(data, "one_liner", str, "сценарий"),
        backstory=str(data.get("backstory") or data.get("situation", "")),
        opening=opening,
        persona=persona,
        situation=_require(data, "situation", str, "сценарий"),
        secrets=list(_require(data, "secrets", list, "сценарий")),
        initial_state=_require(data, "initial_state", dict, "сценарий"),
        turn_limit=_require(data, "turn_limit", int, "сценарий"),
        helps=list(_require(levers, "helps", list, "levers")),
        hurts=list(_require(levers, "hurts", list, "levers")),
        rubric=rubric,
        debrief_tone=data.get("debrief_tone", "спокойно и по делу"),
        frame=str(data.get("frame") or "").strip(),
        contact_hint=str(data.get("contact_hint") or "").strip(),
        skill=str(data.get("skill") or "").strip(),
        profile=profile,
        red_flags=tuple(_text_list(data.get("red_flags"), "сценарий")),
        medium=medium,
        continues=continues,
        canon_history=tuple(canon_history),
        dir=directory or SCENARIO_DIR / str(data.get("id") or ""),
        order=_as_int(data.get("order"), 100),
        wrap_up_at=wrap_up_at,
        wrap_up_reasons=wrap_up_reasons,
        heroine=heroine_slug,
        enabled=_as_bool(data.get("enabled"), True),
        demo_replies=tuple(_text_list(data.get("demo_replies"), "сценарий")),
    )


def _text_list(value: Any, where: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ScenarioError(f"{where}: ожидался список строк")
    return [str(item).strip() for item in value if str(item).strip()]


def _wrap_up(value: Any) -> tuple[int, tuple[str, ...]]:
    """Когда и почему персонаж начинает прощаться: лимит ходов не обрывает сцену."""
    if value is None:
        return 3, ()
    if not isinstance(value, dict):
        raise ScenarioError("сценарий: поле 'wrap_up' должно быть объектом")
    turns_left = _as_int(value.get("turns_left"), 3)
    if turns_left < 1:
        raise ScenarioError("wrap_up: turns_left должен быть положительным")
    reasons = tuple(_text_list(value.get("reasons"), "wrap_up"))
    return turns_left, reasons


def _history(value: Any, where: str) -> list[dict[str, str]]:
    """Канонная переписка: только реплики user/assistant с осмысленным текстом."""
    if value is None:
        return []
    if not isinstance(value, list):
        raise ScenarioError(f"{where}: ожидался список реплик")

    result: list[dict[str, str]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ScenarioError(f"{where}[{index}]: ожидался объект с role и content")
        role = str(item.get("role") or "").strip()
        content = str(item.get("content") or "").strip()
        if role not in {"user", "assistant"}:
            raise ScenarioError(f"{where}[{index}]: role должен быть user или assistant")
        if not content:
            raise ScenarioError(f"{where}[{index}]: пустая реплика")
        result.append({"role": role, "content": content})
    return result


def profile_from_dict(raw: Any) -> Profile:
    """Анкета: текст «о себе», увлечения и минимум три фотографии."""
    if not isinstance(raw, dict):
        raise ScenarioError("анкета: поле 'profile' должно быть объектом")

    photos = _text_list(raw.get("photos"), "profile")
    if len(photos) < 3:
        raise ScenarioError("profile: нужно минимум 3 фото анкеты")

    about = str(raw.get("about") or "").strip()
    if not about:
        raise ScenarioError("profile: нужен текст о себе (about)")

    return Profile(
        about=about,
        hobbies=_text_list(raw.get("hobbies"), "profile"),
        interests=_text_list(raw.get("interests"), "profile"),
        photos=photos,
        captions=_captions(raw.get("captions")),
    )


# Старое приватное имя оставлено, чтобы не ломать внешние вызовы.
_profile = profile_from_dict


def _captions(raw: Any) -> dict[str, str]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ScenarioError("profile: поле 'captions' должно быть объектом")
    return {
        str(name).strip(): str(text).strip()
        for name, text in raw.items()
        if str(name).strip() and str(text).strip()
    }


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() not in {"false", "0", "no", "off", "выкл"}


def _scenario_file(name_or_path: str | Path) -> Path:
    """Приводит имя, папку или путь к файлу к пути scenario.json."""
    path = Path(name_or_path)
    if path.is_dir():
        return path / SCENARIO_FILE
    if path.suffix == ".json":
        return path
    return SCENARIO_DIR / path.name / SCENARIO_FILE


def load_scenario(name_or_path: str | Path = "friday_evening") -> Scenario:
    """Загружает сценарий по id, по папке или по пути к scenario.json.

    Если сценарий ссылается на героиню, личность и анкета читаются из
    `heroines/<slug>/heroine.json` — один источник на все её сценарии.
    """
    path = _scenario_file(name_or_path)
    if not path.exists():
        raise ScenarioError(f"сценарий не найден: {name_or_path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ScenarioError(f"{path.name}: битый JSON — {exc}") from exc

    heroine = None
    heroine_slug = str(data.get("heroine") or "").strip()
    if heroine_slug:
        # Отложенный импорт: heroines.py сам импортирует scenario.py.
        from .heroines import load_heroine

        heroine = load_heroine(heroine_slug)

    return scenario_from_dict(data, path.parent, heroine=heroine)


def all_scenarios() -> list[str]:
    """Id всех сценариев, включая выключенные: нужен для контракта и CLI."""
    names = [p.parent.name for p in SCENARIO_DIR.glob(f"*/{SCENARIO_FILE}")]
    return sorted(names, key=lambda name: (load_scenario(name).order, name))


def available_scenarios() -> list[str]:
    """Id включённых сценариев: меню, случайный старт, «продолжить»."""
    scenarios = [(name, load_scenario(name)) for name in all_scenarios()]
    return [name for name, scenario in scenarios if scenario.enabled]
