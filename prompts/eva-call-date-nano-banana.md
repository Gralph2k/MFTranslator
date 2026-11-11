# Промпты для Nano Banana: экран звонка и серия эмоций Евы

Модель: **Gemini 2.5 Flash Image** («Nano Banana»). Два набора для продолжения
истории Евы после переписки (`eva_message`):

| набор | сценарий | файлов |
|---|---|---|
| контактное фото звонка | `eva_call` | 1 (`call.jpg`) |
| серия эмоций на свидании | `eva_date` | 10 (`calm`, `guarded`, `closed`, `irritated`, `hurt`, `warming`, `smiling`, `laughing`, `tired`, `tears`) |

**Стиль — фотореализм**, как во всей серии Евы. Не смешивать с референсами
Веры и Ани (аниме): модель подтянет чужой стиль, и лицо «уплывёт».

## Что заморожено во всех кадрах

Один человек, а не похожие девушки. Якоря идентичности — из серии анкеты
(`prompts/eva-profile-nano-banana.md`): сверять с
`scenarios/eva_message/images/profile_1.jpg`.

| | Ева (не менять) |
|---|---|
| возраст | 26 |
| лицо | овальное, высокие скулы, мягкая линия подбородка |
| кожа | светлая тёплая, лёгкие веснушки на носу и верхних щеках |
| глаза | зелёно-карие, миндалевидные, прямой спокойный взгляд |
| брови | светлые, блондинистые, на пару тонов темнее волос |
| нос и губы | небольшой прямой нос, естественные полные губы, нюдовый оттенок |
| волосы | светлый тёплый блонд, низкий свободный хвост, пряди у лица |
| примета | маленькая серебряная серьга-кольцо в левом ухе |
| макияж | почти никакого, живая кожа |
| стиль | фотореализм, 50 мм, мягкий свет, приглушённая тёплая палитра, кадр как из жизни |

## Как работать (порядок важен)

1. **Сначала `call.jpg`** — с референсом `profile_1.jpg` (или текущим
   `eva_base.jpg`). Один кадр, проверили якоря — готово.
2. **Потом эталон сцены свидания** — `calm.jpg` — с тем же референсом лица:
   появляется фон винного бара, он описан ниже построчно и дальше не меняется.
3. **Остальные девять эмоций** — только с эталоном `calm.jpg` как референсом:
   меняется одно — выражение лица. Фон, свет, одежда, поза и ракурс — как
   в эталоне.
4. Не прикреплять кадры Веры и Ани. Не собирать серию «с нуля» без референса.

## Кадр для экрана звонка — `eva_call/images/call.jpg`

Назначение: единственная картинка созвона. `bot/call_screen.py` рисует поверх
затемнение сверху и снизу, «ИСХОДЯЩИЙ ВЫЗОВ», имя, «мобильный», «Вызов…» и
красную кнопку, поэтому лицо должно жить в верхней двух третях кадра, а низ
(плечи, грудь) спокойно уйдёт под затемнение.

```
Using the attached portrait as the reference, keep the exact same woman. Do not
redraw her face: keep the same facial features as the reference.

The same woman as in the attached reference image: 26 years old, an oval face
with high cheekbones, light warm skin with a light scatter of fine freckles,
green-hazel almond-shaped eyes, soft blonde eyebrows, a small straight nose,
natural full lips, a single small silver hoop earring in her left ear, light
warm honey-blonde hair in a loose low ponytail, almost no makeup, real skin
texture.

A photorealistic close-up head-and-shoulders portrait, her face large and
centred, filling the upper two thirds of the frame, eyes roughly on the upper
third line. She looks straight into the camera, the way a person looks at the
screen during a video call — direct, present, with a hint of irony, one eyebrow
raised a couple of millimetres, a small closed-lip smile.

Setting: softly blurred warm evening interior behind her — dark wood, dim amber
lights, candle glow, nothing readable, no people in focus. Warm low light from
the left, her face evenly lit and readable.

Photorealistic photograph, natural skin texture with visible pores, no beauty
retouching, 50mm lens at eye level, shallow depth of field, muted warm color
grading, candid editorial feel. 1:1 square, 1024×1024. No text, no watermark,
no logo, no hat, no sunglasses.
```

Негативные ограничения: не менять лицо, серьгу, хвост и блонд; не ночник и не
неон — тёплый вечерний свет; никакого текста и логотипов; лицо не в нижней
половине кадра (уйдёт под затемнение имени); без кокетства и «взгляда из-под
ресниц» — она смотрит на экран, спокойно и прямо.

## Серия эмоций — `eva_date/images/`

### Эталон сцены — `calm.jpg`

Фон — якорь идентичности, как родинка: он совпадает во всех десяти кадрах
дотошно. В кадре и остаётся на месте:

- **Стол и стена** — тёмное дерево, тёплый вечер; она сидит по свою сторону
  стола, камера на уровне её глаз.
- **Свеча** — маленькая, слева от неё, тёплое живое пятно.
- **Сцена** — далеко слева за её плечом, мягко не в фокусе: тёмный силуэт
  микрофона, смутные инструменты, никакого текста.
- **Бокал** — один бокал тёмного-красного вина справа внизу, чуть не в фокусе;
  якорь: если бокал переехал или стал бутылкой — кадр переснимать.
- **Свет** — свеча слева и тёплые лампы сверху: мягкий тёплый ключ на лице,
  ровная заливка, лицо читаемо.
- **Одежда** — чёрная кожаная косуха поверх простой белой футболки (приехала
  на мотоцикле), серьга в левом ухе. Косуха — часть личности серии: если
  модель переодевает её в платье — кадр переснимать.

```
Using the attached portrait as the reference, keep the exact same woman. Do not
redraw her face: keep the same facial features as the reference.

The same woman as in the attached reference image: 26 years old, an oval face
with high cheekbones, light warm skin with a light scatter of fine freckles
across the nose bridge and upper cheeks, green-hazel almond-shaped eyes, soft
blonde eyebrows one or two shades darker than her hair, a small straight nose,
natural full lips, a single small silver hoop earring in her left ear, light
warm honey-blonde hair in a loose low ponytail with a few strands framing her
face, almost no makeup, real skin texture.

She sits at a dark wooden table in a small wine bar in the evening, seen from
across her side of the table, slight three-quarter turn, head facing the
viewer, head-and-shoulders framing. She wears a black leather biker jacket over
a plain white t-shirt. A single glass of dark red wine stands on the table to
the right in the lower foreground, slightly out of focus; a small lit candle in
a glass holder stands to the left. Far behind her shoulder, softly out of
focus: the dark shapes of a small stage with a microphone stand and dim
instruments, warm pendant lights, dark wood panelling. No readable text, no
other people in focus.

Expression: calm, level, with a faint thread of irony — one eyebrow raised a
couple of millimetres, mouth closed in a small closed-lip smile, gaze directly
at the viewer.

Photorealistic photograph, natural skin texture with visible pores, no beauty
retouching, 50mm lens at eye level, shallow depth of field, warm low evening
light, muted warm color grading, candid editorial feel. 1:1 square, 1024×1024.
No text, no watermark, no logo.
```

### Шаблон для остальных девяти

Прикрепите эталон `calm.jpg` и напишите:

```
Using the attached portrait as the reference, change ONLY her facial expression
to: {описание эмоции}

Keep her identity exactly the same: same oval face, same green-hazel eyes, same
blonde eyebrows, same nose and lips, same freckles, same silver hoop in the left
ear, same honey-blonde low ponytail, same black leather jacket over the white
t-shirt, same head angle, same lighting.

And keep the background exactly as in the reference: same dark wooden table,
same candle on the left, same glass of red wine on the right in the lower
foreground, same blurred stage with the microphone stand behind her shoulder,
same warm evening light. Do not redraw the scene and do not add anything to it.

Do not beautify, do not change her age, do not change makeup, do not change the
pose. Square 1:1. No people in the background, no readable text, no watermark.
```

### 1. Спокойно — `calm`
База: она ещё не решила, интересно ли ей. (Эталон; см. промпт выше.)

### 2. Насторожена — `guarded`
Главная эмоция сцены: он сказал что-то — и она взвешивает.
```
guarded and appraising, weighing him — NOT angry: head tilted two or three
degrees, ONE eyebrow raised while the other stays level, eyes calm and slightly
narrowed, lips closed and relaxed with a faint ironic pull at one corner. Do
not pull both eyebrows down, do not frown, no vertical line between the brows.
```
Если вышло «злая» (обе брови сведены, губы поджаты) — переснять: настороженность
здесь в одной поднятой брови и спокойных глазах.

### 3. Закрылась — `closed`
Он начал решать за неё или соревноваться; она перестала вкладываться.
```
closed off: eyes turned away to the side, eyelids lowered, lips a flat line,
face still and unrevealing, the look of a door closing mid-sentence. Shoulders
slightly turned away, chin level.
```

### 4. Раздражена — `irritated`
На «расслабься», на «мотоцикл — опасно», на матч по остроумию.
```
irritated: eyebrows drawn down and slightly together, a small vertical line
between them, eyes narrowed, lips pressed thin, chin lifted slightly — the face
of someone about to say «так, стоп». Not shouting, not hostile.
```

### 5. Обижена — `hurt`
Её задели — например, «ты выглядишь уставшей» или счёт-одолжение.
```
hurt and offended, holding herself upright: inner ends of the eyebrows raised,
eyes wide and glossy with unshed tears, mouth small and turned down, chin
level rather than lowered. Restrained, not pitiful.
```

### 6. Теплеет — `warming`
Он не стал побеждать — и спросил про её неделю.
```
softening: the tension leaves her jaw, eyebrows relax, eyelids lowered a little
in a warm look, a small genuine smile with lips together, faint blush on the
cheeks, gaze at the viewer. The irony melts, warmth shows through.
```

### 7. Улыбается — `smiling`
Он предложил столик у сцены — и попал.
```
a genuine warm smile: eyes curved with pleasure, cheeks raised, lips parted in
a natural smile showing a hint of teeth, eyebrows relaxed. The irony is gone.
```

### 8. Смеётся — `laughing`
Шутка попала в неё, а не в тему.
```
laughing openly: eyes closed in happy crescents, head tipped back slightly,
mouth open in a real laugh, cheeks raised, faint blush.
```

### 9. Устала — `tired`
Пустота после дедлайна проступила сквозь скорость.
```
tired and drained: upper eyelids lowered about halfway, gaze slightly unfocused
and turned a little past the viewer, eyebrows flat with the inner ends slightly
raised, mouth slightly open as if exhaling, faint shadows under the eyes.
```

### 10. Слёзы — `tears`
Редко и поздно: если вечер тронул её сильнее, чем она планировала.
```
crying quietly, not hiding it: eyes wet and shining, one tear on her cheek,
inner eyebrows raised, lips pressed and slightly parted, chin steady.
Restrained — no sobbing, no exaggerated drama.
```

## Настройки и запреты

- Соотношение сторон: **1:1**, размер 1024×1024.
- Стиль — фотореализм на все одиннадцать кадров: живая кожа, мягкий тёплый
  свет, приглушённая палитра, ощущение candid-кадра. Никакого аниме, 3D,
  живописи и «пластикового» глянца.
- Фон свидания всегда один и тот же: тёмное дерево, свеча слева, бокал справа
  внизу, размытая сцена за плечом. Сцена и свет — как в эталоне.
- Косуха поверх белой футболки — часть серии: переодела — кадр переснимать.
- Запрещено: читаемый текст, этикетки, логотипы, водяные знаки; люди в фокусе;
  второй бокал или бутылка на столе; смена цвета волос и глаз; макияж ярче
  «почти никакого»; другая одежда; другая причёска; смена возраста.
- Никакой пошлости: ракурс на уровне глаз, косуха застёгнута или распахнута
  поверх футболки, никакой сексуализации позы и взгляда.

## Если лицо или фон «плывут»

- Прикрепите `profile_1.jpg` и повторите: `Do not redraw the face. Keep the
  exact same facial features as the reference; only the expression may change.`
- Сократите описание эмоции до одной-двух фраз: длинное описание модель
  понимает как разрешение переписать человека.
- Сгенерируйте 3–4 варианта и выберите тот, где совпадают форма глаз, линия
  бровей, губы, веснушки и серьга в левом ухе.
- Если бокал превратился в бутылку, свеча погасла или сцена сменилась баром
  «получше» — это не мелочь, а другой кадр: переснять с эталоном.

## Имена файлов и связка с ботом

```
scenarios/eva_call/images/call.jpg        — экран звонка (bot/call_screen.py)
scenarios/eva_date/images/calm.jpg        — и ещё 9 кадров эмоций
```

Бот сам подставляет кадры: экран звонка — перед первой репликой созвона,
кадры эмоций — к репликам на свидании (`bot/faces.py` по `mood`/шкалам из
наблюдателя). Пока кадров нет, бот не отправляет картинку и сцена не ломается;
после генерации файлы просто кладутся в папки, правок кода не нужно.
