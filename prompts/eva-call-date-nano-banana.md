# Промпты для Nano Banana: экран звонка и серия эмоций Евы

Модель: **Gemini 2.5 Flash Image** («Nano Banana»). Два набора для продолжения
истории Евы после переписки (`first_message/eva`):

| набор | сценарий | файлов |
|---|---|---|
| контактное фото звонка | `first_call/eva` | 1 (`call.jpg`) - **уже сгенерирован** |
| серия эмоций на свидании | `first_date/eva` | 10 (`calm`, `guarded`, `closed`, `irritated`, `hurt`, `warming`, `smiling`, `laughing`, `tired`, `tears`) |

**Стиль - фотореализм**, как во всей серии Евы. Не смешивать с референсами
Веры и Ани (аниме): модель подтянет чужой стиль, и лицо «уплывёт».

**Референс:** `prompts/reference/eva-base.jpg` - утверждённое лицо Евы (копия
утверждённого `eva_base.jpg` вне `scenarios/`; бот эту папку не читает).
Два подводных камня референса, которые нельзя забывать:

- на референсе Ева в **тёмно-зелёной футболке** - её в кадры не переносить,
  одежда берётся из промпта;
- на референсе лицо читается **старше 26** - в каждом промпте стоит усилитель
  «26 и моложе на вид»; кадр, где Ева выглядит старше 27, - брак.

## Что заморожено во всех кадрах

Один человек, а не похожие девушки. Якоря идентичности - из серии анкеты
(`prompts/eva-profile-nano-banana.md`); сверять с `eva-base.jpg`.

| | Ева (не менять) |
|---|---|
| возраст | 26, выглядит моложе своих лет: свежая гладкая кожа, без глубоких носогубных складок и «гусиных лапок» |
| лицо | овальное, высокие скулы, мягкая линия подбородка |
| кожа | светлая тёплая, лёгкие веснушки на носу и верхних щеках |
| глаза | зелёно-карие, миндалевидные, прямой спокойный взгляд |
| брови | светлые, блондинистые, на пару тонов темнее волос |
| нос и губы | небольшой прямой нос, естественные полные губы, нюдовый оттенок |
| волосы | светлый тёплый блонд, низкий свободный хвост, пряди у лица |
| примета | маленькая серебряная серьга-кольцо в левом ухе |
| макияж | почти никакого, живая кожа |
| стиль | фотореализм, 50 мм, мягкий свет, приглушённая тёплая палитра, кадр как из жизни |
| размер | 1:1, 1024×1024, по пояс или крупнее, лицо в фокусе |

Смена сцены, позы и выражения разрешена; смена человека, возраста, причёски,
цвета глаз, веснушек и серьги - брак. Фон в кадрах эмоций заморожен так же
жёстко: это одно и то же кафе во всех десяти кадрах.

## Как работать (порядок важен)

1. **`call.jpg` уже сгенерирован** - раздел оставлен для перегенерации, если
   кадр когда-нибудь поплывёт. Делается от `eva-base.jpg` за один шаг.
2. **Эталон сцены свидания - один раз.** `calm.jpg`: единственный кадр, где
   меняется сцена - от референса к кафе. Сгенерируйте 3-4 варианта
   и выберите лучший; он - основа всей серии.
3. **Остальные девять эмоций - только от эталона `calm.jpg`.** Прикрепляйте
   `calm.jpg` и меняйте только выражение лица. Фон, свет, поза, одежда и
   ракурс остаются как в эталоне. Лицо заново не создавать.
4. На каждую эмоцию генерируйте 2-4 варианта: мимика - лотерея даже у хорошей
   модели.
5. **Не прикреплять кадры Веры и Ани.** Не собирать серию «с нуля» без
   референса; не смешивать старые аниме-кадры с фотореализмом.

## Кадр для экрана звонка - `first_call/eva/images/call.jpg`

Назначение: единственная картинка созвона. `bot/call_screen.py` рисует поверх
затемнение сверху и снизу, «ИСХОДЯЩИЙ ВЫЗОВ», имя, «мобильный», «Вызов…» и
красную кнопку, поэтому лицо должно жить в верхней двух третях кадра, а низ
(плечи, грудь) спокойно уйдёт под затемнение.

```
Using the attached portrait as the reference, keep the exact same woman. Do not
redraw her face: keep the same facial features as the reference. Take her
clothing from this prompt, not from the reference image.

The same woman as in the attached reference image: 26 years old and looking
young for her age - smooth fresh skin, no deep nasolabial folds or crow's
feet. An oval face with high cheekbones, light warm skin with a light scatter
of fine freckles, green-hazel almond-shaped eyes, soft blonde eyebrows, a
small straight nose, natural full lips, a single small silver hoop earring in
her left ear, light warm honey-blonde hair in a loose low ponytail, almost no
makeup, real skin texture.

A photorealistic close-up head-and-shoulders portrait, her face large and
centred, filling the upper two thirds of the frame, eyes roughly on the upper
third line. She looks straight into the camera, the way a person looks at the
screen during a video call - direct, present, with a hint of irony, one eyebrow
raised a couple of millimetres, a small closed-lip smile.

Setting: softly blurred warm evening interior behind her - dark wood, dim amber
lights, candle glow, nothing readable, no people in focus. Warm low light from
the left, her face evenly lit and readable.

Photorealistic photograph, natural skin texture with visible pores, no beauty
retouching, 50mm lens at eye level, shallow depth of field, muted warm color
grading, candid editorial feel. 1:1 square, 1024×1024. No text, no watermark,
no logo, no hat, no sunglasses.
```

Негативные ограничения: не менять лицо, серьгу, хвост и блонд; не переносить
зелёную футболку референса; не старить - «26 и моложе на вид»; не ночник и не
неон - тёплый вечерний свет; никакого текста и логотипов; лицо не в нижней
половине кадра (уйдёт под затемнение имени); без кокетства и «взгляда из-под
ресниц» - она смотрит на экран, спокойно и прямо.

## Серия эмоций - `first_date/eva/images/`

Сцена - четверг, вечер, кафе: тёплый свет, тёмное дерево, свечи. Она в том
самом тёмно-бордовом шёлковом платье со светлым кардиганом, что на четвёртом
кадре анкеты.

### Эталон сцены - `calm.jpg`

Фон - якорь идентичности: он совпадает во всех десяти кадрах дотошно.
В кадре и остаётся на месте:

- **Стол и стена** - тёмное дерево, тёплый вечер; она сидит по свою сторону
  стола, камера на уровне её глаз.
- **Свеча** - маленькая, слева от неё, тёплое живое пятно.
- **Кафе за плечом** - мягко не в фокусе: тёмное дерево, тёплые подвесные
  лампы, окно с вечерним светом снаружи; никакого текста, никаких людей
  в фокусе.
- **Чашка** - белая керамическая чашка кофе на блюдце справа внизу, чуть
  не в фокусе; якорь: если чашка переехала, стала бокалом или бутылкой -
  кадр переснимать.
- **Свет** - свеча слева и тёплые лампы сверху: мягкий тёплый ключ на лице,
  ровная заливка, лицо читаемо.
- **Одежда** - тёмно-бордовое шёлковое платье-комбинация со светлым кремовым
  кардиганом на плечах, серьга в левом ухе. Платье - часть личности серии:
  если модель переодевает её во что-то другое или зелёное - кадр
  переснимать.

```
Using the attached portrait as the reference, keep the exact same woman. Do not
redraw her face: keep the same facial features as the reference. Take her
clothing from this prompt, not from the reference image.

The same woman as in the attached reference image: 26 years old and looking
young for her age - a fresh, youthful face, smooth firm skin, no deep
nasolabial folds or crow's feet. An oval face with high cheekbones, light warm
skin with a light scatter of fine freckles across the nose bridge and upper
cheeks, green-hazel almond-shaped eyes, soft blonde eyebrows one or two shades
darker than her hair, a small straight nose, natural full lips, a single small
silver hoop earring in her left ear, light warm honey-blonde hair in a loose
low ponytail with a few strands framing her face, almost no makeup, real skin
texture.

She sits at a dark wooden table in a small cosy café in the evening, seen from
across her side of the table, slight three-quarter turn, head facing the
viewer, head-and-shoulders framing. She wears a deep wine-red silk slip dress
with a soft cream knit cardigan over the shoulders - elegant, not revealing. A
white ceramic cappuccino cup on a saucer stands on the table to the right in
the lower foreground, slightly out of focus; a small lit candle in a glass
holder stands to the left. Far behind her shoulder, softly out of focus: warm
pendant lights, dark wood panelling, a window with soft evening light outside.
No readable text, no other people in focus.

Expression: calm, level, with a faint thread of irony - one eyebrow raised a
couple of millimetres, mouth closed in a small closed-lip smile, gaze directly
at the viewer.

Photorealistic photograph, natural skin texture with visible pores, no beauty
retouching, 50mm lens at eye level, shallow depth of field, warm low evening
light, muted warm color grading, candid editorial feel. 1:1 square, 1024×1024.
No text, no watermark, no logo.
```

**Негативные ограничения:**
- не переносить зелёную футболку референса: одежда - только бордовое платье
  с кардиганом из промпта;
- не старить: 26 и моложе на вид, свежая кожа, без глубоких складок;
- не аниме и не 3D - только фотореализм, живая кожа без ретуши;
- не менять веснушки, разрез и цвет глаз, серьгу в левом ухе, блонд и хвост;
- не менять сцену: кафе, стол, свеча слева, чашка кофе справа, тёплый
  интерьер за плечом;
- никакого текста: этикетки, меню, вывески, водяные знаки, логотипы;
- никаких людей в фокусе на фоне и второй Евы в отражениях.

### Шаблон для остальных девяти

Прикрепите эталон `calm.jpg` и используйте этот текст, подставив выражение
из таблицы ниже:

```
Using the attached portrait as the reference, keep the exact same woman, the
exact same framing, head angle, pose, lighting, hairstyle, clothing and café
background. Change ONLY her facial expression to: {выражение}.

Do not redraw the face: she is 26 and looks young for her age - smooth fresh
skin, no deep lines. Same oval face with high cheekbones, same green-hazel
almond-shaped eyes, same soft blonde eyebrows, same small straight nose, same
natural full lips, same light freckles across the nose bridge and upper
cheeks, same silver hoop earring in the left ear, same honey-blonde low
ponytail with a few strands framing her face. Same deep wine-red silk slip
dress with the cream knit cardigan over the shoulders. Same age, same
almost-no-makeup look, same real skin texture.

Keep the background exactly as in the reference: same dark wooden table, same
lit candle in the glass holder on the left, same white cappuccino cup on the
right in the lower foreground, same blurred café interior with warm pendant
lights and dark wood panelling behind her shoulder, same warm evening light.
Do not redraw the scene and do not add anything to it.

Do not beautify, do not change her age, do not change makeup, do not change
the pose. Photorealistic, natural skin texture, no beauty retouching, same
50mm lens, same soft warm light, same muted warm grading. Square 1:1,
1024×1024. No people in the background, no readable text, no watermark.
```

### Десять выражений

| файл | когда в сцене | выражение для `{выражение}` |
|---|---|---|
| `calm` | база: ещё не решила, интересно ли (эталон, промпт выше) | - |
| `guarded` | взвешивает его слова - главная эмоция сцены | `guarded and appraising, weighing him - NOT angry: head tilted two or three degrees, ONE eyebrow raised while the other stays level, eyes calm and slightly narrowed, lips closed and relaxed with a faint ironic pull at one corner. Do not pull both eyebrows down, do not frown, no vertical line between the brows` |
| `closed` | он решает за неё или соревнуется - она перестаёт вкладываться | `closed off: eyes turned away to the side, eyelids lowered, lips a flat line, face still and unrevealing, the look of a door closing mid-sentence. Shoulders slightly turned away, chin level` |
| `irritated` | на «расслабься», на снисходительный тон, на матч по остроумию | `irritated: eyebrows drawn down and slightly together, a small vertical line between them, eyes narrowed, lips pressed thin, chin lifted slightly - the face of someone about to say «так, стоп». Not shouting, not hostile` |
| `hurt` | её задели: «ты выглядишь уставшей», счёт-одолжение | `hurt and offended, holding herself upright: inner ends of the eyebrows raised, eyes wide and glossy with unshed tears, mouth small and turned down, chin level rather than lowered. Restrained, not pitiful` |
| `warming` | он не стал побеждать - и спросил про её неделю | `softening: the tension leaves her jaw, eyebrows relax, eyelids lowered a little in a warm look, a small genuine smile with lips together, faint blush on the cheeks, gaze at the viewer. The irony melts, warmth shows through` |
| `smiling` | он предложил столик у сцены - и попал | `a genuine warm smile: eyes curved with pleasure, cheeks raised, lips parted in a natural smile showing a hint of teeth, eyebrows relaxed. The irony is gone` |
| `laughing` | шутка попала в неё, а не в тему | `laughing openly: eyes closed in happy crescents, head tipped back slightly, mouth open in a real laugh, cheeks raised, faint blush` |
| `tired` | пустота после дедлайна проступила сквозь скорость | `tired and drained: upper eyelids lowered about halfway, gaze slightly unfocused and turned a little past the viewer, eyebrows flat with the inner ends slightly raised, mouth slightly open as if exhaling, faint shadows under the eyes` |
| `tears` | редко и поздно: вечер тронул её сильнее, чем она планировала | `crying quietly, not hiding it: eyes wet and shining, one tear on her cheek, inner eyebrows raised, lips pressed and slightly parted, chin steady. Restrained - no sobbing, no exaggerated drama` |

**Важно про `guarded`.** Главная эмоция сцены, и её легко перепутать со злостью:
настороженность - одна поднятая бровь и спокойные глаза. Если модель свела обе
брови и поджала губы - кадр переснять: злость - это `irritated`, и она для
набора нужна отдельно.

## Настройки и запреты

- Соотношение сторон: **1:1**, размер 1024×1024.
- Стиль - фотореализм на все кадры: живая кожа, мягкий тёплый свет,
  приглушённая палитра, ощущение candid-кадра. Никакого аниме, 3D, живописи
  и «пластикового» глянца.
- Лицо, веснушки, глаза, светлый блонд и хвост, серьга, возраст («26 и моложе
  на вид») - идентичность. В кадрах эмоций меняется только выражение; фон,
  свет, поза, одежда и ракурс - как в эталоне.
- Тёмно-бордовое платье со светлым кардиганом - часть серии: переодела -
  кадр переснимать. Зелёную футболку референса не переносить.
- Фон эмоций всегда один и тот же: кафе, тёмное дерево, свеча слева, чашка
  кофе справа внизу, тёплый интерьер за плечом.
- Запрещено: читаемый текст, этикетки, логотипы, водяные знаки; люди в фокусе;
  вторая чашка или бокал на столе; смена цвета волос и глаз; макияж ярче
  «почти никакого»; другая одежда; другая причёска; смена возраста.
- Никакой пошлости: ракурс на уровне глаз, платье закрытое, кардиган на
  плечах, никакой сексуализации позы и взгляда.
- Рамку анкеты, сердечки, кнопки и экран звонка модель не рисует - это делает
  бот.

## Если лицо или фон «плывут»

- Прикрепите эталон ещё раз и добавьте: `Do not redraw the face. Keep the
  exact same facial features as the reference; only the expression may change.`
- Если Ева вышла старше своих лет, добавьте: `She is 26 and looks young for
  her age. Do not age her face: smooth fresh skin, no deep lines.`
- Если поехал фон, добавьте отдельно: `Keep the background identical to the
  reference: same table, same candle, same cup, same café interior, same
  bokeh. Change only the expression.`
- Уменьшите формулировку эмоции до одной-двух фраз: длинное описание модель
  понимает как разрешение переписать человека.
- Сгенерируйте 3-4 варианта и выберите тот, где совпадают форма глаз, линия
  бровей, губы, веснушки и серьга в левом ухе.
- Если поплыли веснушки, блонд стал русым или уехал хвост - вернитесь к
  `eva-base.jpg`: это якоря, по которым видно, что кадр остался тем же
  человеком.
- Если чашка превратилась в бокал или бутылку, свеча погасла или кафе стало
  другим заведением - это не мелочь, а другой кадр: переснять с эталоном.
- Если модель тащит одежду или фон из референса, добавьте: `Keep the face and
  hair from the reference; take the outfit and the background from the prompt,
  do not copy them from the reference image.`

## Имена файлов и связка с ботом

```
prompts/reference/eva-base.jpg                 эталон лица, бот его не читает

scenarios/first_call/eva/images/call.jpg       - экран звонка (bot/call_screen.py)

scenarios/first_date/eva/images/calm.jpg       - эталон сцены и базовая эмоция
scenarios/first_date/eva/images/guarded.jpg
scenarios/first_date/eva/images/closed.jpg
scenarios/first_date/eva/images/irritated.jpg
scenarios/first_date/eva/images/hurt.jpg
scenarios/first_date/eva/images/warming.jpg
scenarios/first_date/eva/images/smiling.jpg
scenarios/first_date/eva/images/laughing.jpg
scenarios/first_date/eva/images/tired.jpg
scenarios/first_date/eva/images/tears.jpg
```

Бот сам подставляет кадры: экран звонка - перед первой репликой созвона,
кадры эмоций - к репликам на свидании (`bot/faces.py` по `mood`/шкалам из
наблюдателя). Пока какого-то кадра нет, бот не отправляет картинку и сцена не
ломается; после генерации файлы просто кладутся в папку `first_date/eva/images/`,
правок кода не нужно.

Приоритет для `first_date/eva`: `guarded`, `closed`, `irritated`, `warming`,
`smiling`, `laughing`. `calm`, `tired` и `tears` нужны реже, но пусть будут:
состояние зависит от хода игрока, а не от сценария.
