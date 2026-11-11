# Промпты для Nano Banana: фотореалистичная Вера (весь набор)

Модель: **Gemini 2.5 Flash Image** (в обиходе «Nano Banana»).
Задача: перегенерировать **все** фотографии Веры в фотореализме — эталон, три кадра
анкеты, десять эмоций и фото для экрана звонка. Вера остаётся той же женщиной: 30 лет,
редактор, медное каре, серая родинка на левой скуле, оливковая льняная рубашка.
Меняется стиль: вместо аниме/вебтуна — фотореалистичная съёмка.

Это осознанная смена визуального языка: Ева уже фотореалистичная, Вера теперь тоже.
Аня (выключенный сценарий) остаётся в старой аниме-серии и в этот набор не входит.

## Что нужно получить

| набор | куда | файлы | сколько |
|---|---|---|---|
| эталон | вне `scenarios/` | `prompts/reference/vera-cafe-base.jpg` | 1 (из 3–4 попыток) |
| анкета | `scenarios/first_message/vera/images/` | `profile_1..3.jpg` | 3 |
| эмоции | `scenarios/first_date/vera/images/` | `calm` … `tears` | 10 |
| звонок | `scenarios/first_call/vera/images/` | `call.jpg` | 1 |

Итого 14 кадров для бота. Старые аниме-файлы заменяются файлами с теми же именами —
код и сценарии менять не нужно.

## Что заморожено во всех кадрах

| | Вера (не менять) |
|---|---|
| возраст | 30 |
| лицо | круглее среднего, мягкие полные щёки, заметные скулы |
| кожа | светлая тёплая, живая: поры, мелкие линии, без ретуши |
| глаза | серо-зелёные, чуть прищуренные, внимательные |
| брови | тонкие, прямые, на тон темнее волос |
| нос и губы | маленький прямой нос, естественные розовые губы с полной нижней |
| примета | маленькая тёмная родинка на левой скуле |
| макияж | почти никакого |
| волосы | медно-каштановое каре до подбородка с ровным срезом, прядь за правым ухом, несколько прядей у виска |
| одежда | оливковая льняная рубашка с открытым воротом, рукава подвёрнуты; в танце — платье-рубашка в той же палитре |
| стиль | фотореализм, 50 мм, естественная кожа, мягкий свет, приглушённая тёплая палитра, ощущение живого кадра |
| размер | 1:1, 1024×1024, по пояс или крупнее, лицо в фокусе |

Смена сцены, позы и выражения разрешена; смена человека, возраста, причёски, цвета
глаз и родинки — брак. Фон в кадрах эмоций заморожен так же жёстко: это одно и то же
летнее кафе во всех десяти кадрах.

## Как работать (порядок важен)

1. **Эталон — один раз.** Сгенерируйте 3–4 варианта портрета в кафе (шаг 1), выберите
   лучший. Это единственный раз, когда лицо создаётся с нуля.
2. **Сохраните утверждённый эталон вне сценариев** — `prompts/reference/vera-cafe-base.jpg`.
   Бот эту папку не читает; если положить эталон в `scenarios/`, `bot/faces.py` может
   принять его за кадр настроения.
3. **Сначала десять эмоций.** Все десять делаются от эталона: прикрепляйте
   `vera-cafe-base.jpg` и меняйте только выражение лица. Фон, свет, поза и одежда
   остаются как на эталоне.
4. **Потом три кадра анкеты.** Сначала `profile_1.jpg` (город), он утверждается; для
   `profile_2..3.jpg` прикрепляйте эталон **и** `profile_1.jpg`.
5. **Последним — `call.jpg`.** Домашний вечерний портрет от эталона.
6. **Старые аниме-кадры не прикрепляйте как референс.** Модель подтянет плоскую
   заливку и линию — фотореализм не получится. Референс — только новые
   фотореалистичные кадры.
7. **Не смешивайте с Евой.** Её фотореалистичные кадры — другая женщина; прикрепите
   их случайно — получится третье лицо.
8. На каждую эмоцию и кадр генерируйте 2–4 варианта: мимика и лицо — лотерея даже
   у хорошей модели.

## Шаг 1. Эталонный портрет — кафе

```
A photorealistic portrait photograph of one woman: 30 years old, a rounder face with
soft full cheeks and noticeable cheekbones, warm light skin with real texture — visible
pores, fine lines, no retouching. Grey-green eyes, slightly narrow and observant, thin
straight eyebrows a shade darker than her hair, a small straight nose, natural rose lips
with a fuller lower lip, almost no makeup. Copper-auburn hair in a chin-length bob with
a blunt edge, the right side tucked behind her ear, a few strands falling forward across
the temple. A small dark mole on her left cheekbone. She wears an olive-green linen
shirt with an open collar, sleeves rolled to the elbow.

Expression: calm and level with the faintest thread of irony — one eyebrow raised by
a couple of millimetres, eyelids slightly narrowed, mouth closed, a small smile that
lives in the eyes more than on the lips. She looks directly into the lens. Not flirting,
not posing, not a wide beauty-pageant smile.

Setting: she sits at a light wooden table in a small café on a bright summer day, near
a tall window with sheer white linen curtains. Summer sunlight pours in from the left;
behind her shoulder, blurred green trees and warm stone houses outside. In the lower
foreground, softly out of focus, a white ceramic cappuccino cup on a saucer and a small
glass of water on the wooden table. A strip of pale wall with sun patches behind her.
Soft warm bokeh in cream, honey and sage; background lower in contrast than her face.

Photorealistic photograph, natural skin texture with visible pores and fine lines, no
beauty retouching, 50mm lens at eye level, shallow depth of field, soft natural light,
muted warm color grading, candid editorial feel. 1:1 square, 1024×1024. No text, no
watermark, no logo, no other people, no jewelry, no glasses.
```

**Негативные ограничения:**
- не аниме, не вебтун, не 3D-рендер, не живопись — только фотореализм;
- не «пластиковая» кожа и не ретушь для журнала: поры, линии, живой свет;
- не менять возраст: 30, а не 24 и не 38;
- не менять родинку на левой скуле, разрез и цвет глаз, линию бровей, полную нижнюю
  губу, срез каре и прядь за правым ухом;
- не менять одежду на свитер, пальто или платье — оливковая рубашка остаётся, иначе
  кадр тянет к Ане;
- никакого текста: меню, вывески, надписи на чашке, водяные знаки, логотипы;
- никаких людей и официантов в фоне и в отражениях, никаких украшений и очков;
- не рекламный глянец: без студийного света и идеальной позы.

**Что проверить после генерации:**
- лицо читается как живое: форма, скулы, серо-зелёные глаза, брови, губы, родинка
  на левой скуле на своём месте;
- возраст 30, кожа с текстурой, а не «отфотошопленная»;
- каре с ровным срезом, прядь за правым ухом, медный оттенок не ушёл в рыжий;
- оливковая рубашка, ворот открыт, рукава подвёрнуты;
- кафе: окно с занавесками, зелень и камень за стеклом, деревянный стол, белая чашка
  и стакан воды, мягкое боке; свет с окна слева;
- взгляд в камеру, ирония в глазах, а не пустая приветливая улыбка;
- кадр годится как эталон: лицо крупно, макушка и плечи не обрезаны;
- в кадре нет текста, чужих людей и рекламного глянца.

## Шаг 2. Десять эмоций — `scenarios/first_date/vera/images/`

### Общий шаблон: меняется только выражение

Прикрепите `vera-cafe-base.jpg` и используйте этот текст, подставив выражение из
таблицы ниже:

```
Using the attached portrait as the reference, keep the exact same woman, the exact same
framing, head angle, pose, lighting, hairstyle, clothing and café background. Change
ONLY her facial expression to: {выражение}.

Do not redraw the face: same rounder face with soft full cheeks and noticeable
cheekbones, same grey-green eyes, same thin straight eyebrows, same small straight
nose, same fuller lower lip, same small dark mole on the left cheekbone, same
copper-auburn chin-length bob with a blunt edge and the right side tucked behind the
ear. Same olive-green linen shirt with an open collar, sleeves rolled to the elbow.
Same age, same almost-no-makeup look, same real skin texture.

Keep the background exactly as in the reference: same tall window with sheer white linen
curtains, same summer sunlight from the left, same blurred green trees and warm stone
houses outside, same light wooden table edge, same white ceramic cappuccino cup on
a saucer and the small glass of water in the lower foreground, same pale wall with sun
patches, same soft warm bokeh. Do not add people, text, signage or new objects.

Photorealistic, natural skin texture, no beauty retouching, same 50mm lens, same soft
natural light, same muted warm grading. 1:1 square, 1024×1024.
```

### Десять выражений

| файл | когда в сцене | выражение для `{выражение}` |
|---|---|---|
| `calm` | базовое, ещё не решила, интересно ли | `a calm, level expression with a faint thread of irony: eyebrows relaxed, one raised a couple of millimetres, eyelids slightly observant, mouth closed with a small closed-lip smile, gaze directly at the viewer` |
| `guarded` | взвешивает, верить ли (главная эмоция) | `guarded and watchful, weighing him — appraising, NOT angry: head tilted two or three degrees, ONE eyebrow raised while the other stays level, eyes calm and slightly narrowed, lips closed and relaxed with a faint downward pull at one corner` |
| `closed` | давит или оценивает — она перестаёт вкладываться | `closed off: eyes turned away to the side, eyelids lowered, lips a flat line, face still and unrevealing, the look of a door closing mid-sentence, shoulders slightly turned away` |
| `irritated` | штамп, «расслабься», грубая шутка | `irritated, the wince of someone who edits for a living: eyebrows drawn down and slightly together, a small vertical line between them, eyes narrowed, lips pressed thin, one nostril flared a little, chin lifted slightly` |
| `hurt` | её задели, но она держится прямо | `hurt and offended, holding herself upright: inner ends of the eyebrows raised, eyes wide and glossy with unshed tears, mouth small and turned down, chin lifted slightly rather than lowered, restrained, not pitiful` |
| `warming` | он не стал давить и попал в тему | `softening: the tension leaves her jaw, eyebrows relax, eyelids lowered a little in a warm look, a small genuine smile with lips together, faint blush on the cheeks, gaze at the viewer` |
| `smiling` | вспомнил про караоке — и это не приём | `a genuine warm smile: eyes curved with happiness, cheeks raised, lips parted in a natural smile showing a hint of teeth, eyebrows relaxed, the irony gone` |
| `laughing` | стало легко; шутка попала в неё | `laughing openly: eyes closed in happy crescents, head tipped back slightly, mouth open in a real laugh, cheeks raised, faint blush` |
| `tired` | пришла через силу, конец недели | `tired and drained: upper eyelids lowered about halfway, gaze slightly unfocused, eyebrows flat with the inner ends a little raised, mouth slightly open as if exhaling, faint shadows under the eyes` |
| `tears` | редко и поздно: рассказала о прошлом свидании | `crying quietly, not hiding it: eyes wet and shining, one tear on her cheek, inner eyebrows raised, lips pressed and slightly parted, chin steady, restrained — no sobbing, no exaggerated drama` |

**Важно про `guarded`.** Это главная эмоция сценария, и её легко перепутать со злостью.
Настороженность — одна поднятая бровь и спокойные глаза; если модель свела обе брови
и поджала губы, кадр переснять: злость — это `irritated`, и она для набора нужна
отдельно.

## Шаг 3. Три кадра анкеты — `scenarios/first_message/vera/images/`

### 1. Главное фото, город — `profile_1.jpg`

Назначение: первое, что видит игрок в карточке и по чему запоминает Веру. Лицо крупно,
взгляд в камеру, спокойная ирония вместо приветливой маски. Сцена — город днём.

```
Using the attached portrait as the reference, keep the exact same woman and change
only the scene, the framing and her expression. Do not redraw her face.

Change the background completely: she is outdoors on a quiet city street on an
early-afternoon weekday, not in the café from the reference. Do not copy the café window,
the wooden table, the white cup, the glass of water or the curtains from the attached
image — the reference is only for her face.

The same woman as in the attached reference: a 30-year-old woman with a rounder face,
soft full cheeks and noticeable cheekbones, warm light skin with real texture, a small
dark mole on her left cheekbone. Grey-green eyes, slightly narrow and observant, thin
straight eyebrows a shade darker than her hair, small straight nose, natural rose lips
with a fuller lower lip, almost no makeup. Copper-auburn hair in a chin-length bob with
a blunt edge, the right side tucked behind her ear, a few strands falling forward across
the temple. She wears her olive-green linen shirt with an open collar, sleeves rolled
to the elbow.

Framing: head-and-shoulders, chest-up, centred, camera at her eye level, 1:1 square.
Her shoulders are turned slightly, the head faces the camera. She stands unhurried on
the pavement, arms relaxed, no cup in her hands and no table in front of her.

Expression: calm and level with the faintest hint of irony — one eyebrow raised by
a couple of millimetres, eyelids slightly narrowed, mouth closed, a small smile that
lives in the eyes more than on the lips. Gaze directly at the viewer. No coyness, no
flirting, no head tilt.

Setting: a quiet city street in early afternoon. She stands on the pavement, chest-up,
and the street behind her is clearly out of focus: warm stone facades, shop fronts with
blank unreadable windows, green street trees, a strip of sunlit pavement and the soft
shapes of a pedestrian crossing. No table, no cup, no café terrace, no window with
curtains, no indoor interior — she is outdoors, on the street, and the background is
a blurred city, not a room. Background lower in contrast than her face, soft warm bokeh
in cream, honey and sage. Early-afternoon sun from the left gives a soft rim light on
her hair while a broad soft fill keeps her face evenly lit and readable.

Photorealistic photograph, natural skin texture with visible pores and fine lines, no
beauty retouching, 50mm lens at eye level, shallow depth of field, soft natural light,
muted warm color grading, candid editorial feel. 1:1 square, 1024×1024. No other people
in the background, no readable text or signage, no watermark, no logo, no jewelry, no
glasses, no bicycle or car in the foreground.
```

**Негативные ограничения:**
- не менять лицо, причёску, цвет глаз, родинку, возраст и «почти без макияжа»;
- не кафе и не интерьер: никакого стола, чашки, террасы, окна со шторами;
- не менять одежду на свитер, пальто или вечернее платье;
- не фотореализм → только фотореализм: без аниме, 3D, живописи и рекламного глянца;
- никакого текста: вывески, меню, надписи, водяные знаки, логотипы;
- никаких людей в фоне и в отражениях, никаких украшений и очков.

**Что проверить:** лицо совпадает с эталоном (родинка, глаза, губы, каре); возраст 30;
взгляд в камеру и ирония в глазах; фон читается как улица, а не кафе; кожа живая;
кадр годится как аватарка — лицо крупно, макушка и плечи не обрезаны.

### 2. Сальса — `profile_2.jpg`

Назначение: вторая сторона — занятие, в котором она разбирается и которое любит.
В переписке она упомянула сальсу по вторникам; кадр должен совпадать с её словами:
живой зал, движение, удовольствие от того, что получается. На кадре — танец, не тело.

```
Using the attached portrait as the reference, keep the exact same woman and change
only the scene, the pose, the clothing and her expression. Do not redraw her face.

The same woman as in the reference: a 30-year-old woman with a rounder face, soft full
cheeks and noticeable cheekbones, warm light skin with real texture, a small dark mole
on her left cheekbone. Grey-green eyes, slightly narrow and observant, thin straight
eyebrows, small straight nose, natural rose lips with a fuller lower lip, almost no
makeup. Copper-auburn chin-length bob with a blunt edge, the right side tucked behind
her ear, a few strands loose. She wears a simple olive-sage wrap dress in the same muted
palette as her linen shirt, knee-length, sleeves rolled, with simple ballet flats.

Framing: three-quarter length, waist-up or a little lower, camera at her eye level,
1:1 square. She is caught mid-movement as if the music just pulled her into a step:
shoulders turned, one arm raised in a frame, chin lifted, weight on one leg, the skirt
swinging slightly. The pose reads as dancing, not as a pose for a photo.

Expression: focused and pleased — eyes open and bright, a small confident smile with
lips together or slightly parted, eyebrows relaxed, a faint flush from the movement.
She is doing something she is good at and enjoys it; she is not performing for the camera.

Setting: a small salsa studio in warm evening light — pale wooden floor, a wall of
mirrors softly blurred behind her, warm practical lamps, a strip of sage-green wall,
a blurred row of chairs. Mirrors stay vague and out of focus: no clear reflection of her
face and no doubled figure. At most one or two blurred dancers far in the background,
out of focus, with no readable faces. Warm light from the side and slightly above, soft
shadow under the chin, no harsh flash.

Photorealistic photograph, natural skin texture, no beauty retouching, 50mm lens at eye
level, shallow depth of field, warm low evening light, muted warm color grading, candid
editorial feel. 1:1 square, 1024×1024. No vulgarity: the camera does not look up or down
at her body, the dress is modest, no close-up on hips or chest, no arched-back pin-up
pose. No other person in focus, no readable text or signage, no watermark, no logo, no
jewelry, no glasses.
```

**Негативные ограничения:** не менять лицо и причёску; не менять возраст; без
вульгарности (ракурс на уровне глаз, акцент на лице и движении, одежда не сползает);
не менять платье на купальник/латекс/сценический костюм; зеркала размыты и не
показывают вторую Веру; никакого текста; фотореализм, а не аниме.

**Что проверить:** лицо как в эталоне; поза читается как танец, а не «стоит и
улыбается»; руки и пальцы целые; вульгарности нет; балетки, а не каблуки; зеркала
размыты; свет тёплый, лицо читаемо.

### 3. Караоке — `profile_3.jpg`

Назначение: третья сторона — та, где она не «редактор и умная женщина», а человек,
с которым можно смеяться. В переписке она рассказывала про караоке с подругами;
кадр про вечер, а не про сцену и не про алкоголь.

```
Using the attached portrait as the reference, keep the exact same woman and change
only the scene, the pose and her expression. Do not redraw her face.

The same woman as in the reference: a 30-year-old woman with a rounder face, soft full
cheeks and noticeable cheekbones, warm light skin with real texture, a small dark mole
on her left cheekbone. Grey-green eyes, slightly narrow and observant, thin straight
eyebrows, small straight nose, natural rose lips with a fuller lower lip, almost no
makeup. Copper-auburn chin-length bob with a blunt edge, the right side tucked behind
her ear. She wears her olive-green linen shirt, sleeves rolled to the elbow — this is
a small private karaoke room with friends, not a stage.

Framing: chest-up or waist-up, she is clearly the main subject, 1:1 square, camera at
her eye level. She holds a black handheld microphone in one hand near her mouth, the
other hand free or half-raised. A slight three-quarter turn; her head is toward the
screen but her eyes come back to the camera.

Expression: an ironic half-smile, mouth open mid-phrase, eyes narrowed with amusement,
one eyebrow slightly raised — she knows this is a little ridiculous and enjoys it
anyway. Not drunk, not silly, not a staged wide grin.

Setting: a small private karaoke room at night — a glowing screen behind her shoulder
with blurred, unreadable abstract light (no letters), pink and teal neon strips along
the wall, a low table edge in soft bokeh. Two friends at the edge of the frame, from
behind or in profile, softly blurred and clearly secondary: they are not looking at the
camera and their faces are not readable. Neon light does not turn her skin green or
pink — her face stays warm and readable.

Photorealistic photograph, natural skin texture, no beauty retouching, 50mm lens at eye
level, shallow depth of field, neon-lit evening scene with a warm key light on her face,
candid editorial feel. 1:1 square, 1024×1024. No readable text anywhere: screen lyrics,
signs, captions, watermark, logo. No jewelry, no glasses. No alcohol bottles in the
foreground, no raised glasses, no cigarettes, no party clichés. No other person in focus.
```

**Негативные ограничения:** не менять лицо и причёску; неон не перекрашивает волосы;
не «веселить» её (без пьяной улыбки и постановочной гримасы); на экране только
размытый свет, без слов; подруги — размытый фон; без бутылок и бокалов на переднем
плане; не менять одежду; микрофон в руке — не телефон и не бутылка; фотореализм.

**Что проверить:** лицо как в эталоне; улыбка ироничная и живая; микрофон читается как
микрофон и не закрывает лицо; на экране нет читаемых букв; подруги размыты и вторичны;
неон не убил тёплый тон кожи; кроп удачный.

## Шаг 4. Фото для экрана звонка — `scenarios/first_call/vera/images/call.jpg`

Назначение: единственная картинка сцены-созвона. По сюжету четверг, вечер, она дома
и ждёт звонка. Интерфейс звонка (имя, «мобильный», «Вызов…») рисует код — модель его
не рисует.

```
Using the attached portrait as the reference, keep the exact same woman and change
only the scene, the pose and her expression. Do not redraw her face.

The same woman as in the reference: a 30-year-old woman with a rounder face, soft full
cheeks and noticeable cheekbones, warm light skin with real texture, a small dark mole
on her left cheekbone. Grey-green eyes, slightly narrow and observant, thin straight
eyebrows, small straight nose, natural rose lips with a fuller lower lip, almost no
makeup. Copper-auburn chin-length bob with a blunt edge, the right side tucked behind
her ear. She wears her olive-green linen shirt with an open collar, sleeves rolled to
the elbow.

Setting: her flat in the evening. She sits in a worn armchair by a warm floor lamp,
knees up, a mug of tea on the small table beside her, a bookshelf and a soft blanket
blurred behind her. The room is warm, lived-in, slightly dim; the lamp is the key light,
a cool window glow is only a soft rim from the side. Background clearly out of focus.

Framing: head-and-shoulders, chest-up, centred, camera at her eye level, 1:1 square.
A slight three-quarter turn, head facing the camera, shoulders relaxed.

Expression: expectant and warm with a thin layer of tension — she is waiting for the
call and does not want to admit she is waiting. A small closed-lip smile, eyebrows
slightly raised, eyes direct and alive. Not flirting, not posing, not a glamour shot;
she looks like a real woman at home in the evening.

Photorealistic photograph, natural skin texture with visible pores and fine lines, no
beauty retouching, 50mm lens at eye level, shallow depth of field, warm low evening
light, muted warm color grading, candid editorial feel. 1:1 square, 1024×1024. No text,
no watermark, no logo, no phone in her hands, no other people.
```

**Негативные ограничения:** не менять лицо и причёску; не вечернее платье и не
«свидание» — домашняя рубашка; никакого текста и интерфейса звонка на картинке;
не рекламный глянец; без бокалов и алкоголя; телефон не в руках; никаких чужих людей.

**Что проверить:** лицо как в эталоне; кадр читается как «дома, вечер, ждёт звонка»;
тёплый свет, лицо читаемо; фон размыт; нет текста и интерфейса; кроп по плечи.

## Настройки и запреты (общие)

- Соотношение сторон: **1:1**, размер 1024×1024.
- Стиль один на все 14 кадров и на все сцены: фотореализм, естественная кожа,
  мягкий свет, приглушённая тёплая палитра. Никакого аниме, вебтуна, 3D, живописи
  и «пластикового» глянца.
- Лицо, причёска, цвет глаз, родинка, возраст и «почти без макияжа» — идентичность.
  Меняются только сцена, поза и выражение лица.
- Оливковая льняная рубашка — часть личности; платье-рубашка в той же палитре
  допустима только в танце. Свитер, пальто, вечернее платье, купальник и сценический
  костюм запрещены: они тянут к Ане.
- Фон эмоций — одно и то же летнее кафе: окно с занавесками, зелень и тёплый камень
  за стеклом, деревянный стол, белая чашка кофе, стакан воды, мягкое боке.
- Запрещено: читаемый текст, вывески, меню, надписи на экране, водяные знаки,
  логотипы, украшения, очки; люди в фокусе на фоне; вульгарность, эротика, акцент на
  теле; смена возраста, цвета глаз и причёски; второй экземпляр Веры в отражении;
  смешивание с наборами Ани и Евы.
- Рамку анкеты, сердечки, кнопки и экран звонка модель не рисует — это делает бот.

## Если лицо или фон «плывут»

- Прикрепите эталон ещё раз и добавьте: `Do not redraw the face. Keep the exact same
  facial features as the reference; only the expression may change.`
- Если поехал фон, добавьте отдельно: `Keep the background identical to the reference:
  same window, same curtains, same table, same cup, same bokeh. Change only the
  expression.`
- Уменьшите формулировку эмоции до одной фразы — длинные описания модель часто
  трактует как разрешение менять внешность.
- Сгенерируйте 4 варианта и выберите тот, где совпадают форма глаз, линия бровей,
  полная нижняя губа, родинка на левой скуле и белая чашка на столе.
- Если поплыла родинка или чашка — вернитесь к эталону: это якоря, по которым видно,
  что кадр остался тем же человеком и тем же кафе.
- Если после смены сцены уехало лицо, сократите описание сцены до одной–двух фраз.
- Для кадров `profile_2..3` прикрепляйте два референса: эталон (лицо) и утверждённый
  `profile_1.jpg` (как Вера выглядит на улице). Если модель копирует фон из
  `profile_1.jpg`, добавьте: `Keep the face from the first reference and the new scene
  from the prompt; do not copy the background of the reference.`

## Имена файлов и связка с ботом

```
prompts/reference/vera-cafe-base.jpg          эталон, бот его не читает

scenarios/first_message/vera/images/profile_1.jpg  анкета: город, работа и «о себе»
scenarios/first_message/vera/images/profile_2.jpg  анкета: сальса
scenarios/first_message/vera/images/profile_3.jpg  анкета: караоке

scenarios/first_date/vera/images/calm.jpg          эмоции для сцены вживую
scenarios/first_date/vera/images/guarded.jpg
scenarios/first_date/vera/images/closed.jpg
scenarios/first_date/vera/images/irritated.jpg
scenarios/first_date/vera/images/hurt.jpg
scenarios/first_date/vera/images/warming.jpg
scenarios/first_date/vera/images/smiling.jpg
scenarios/first_date/vera/images/laughing.jpg
scenarios/first_date/vera/images/tired.jpg
scenarios/first_date/vera/images/tears.jpg

scenarios/first_call/vera/images/call.jpg           фото для экрана звонка
```

Старые файлы с этими именами заменяются новыми — код не меняется. Кеш карточек анкеты
и экрана звонка обновляется по времени файлов: после замены кадров вёрстка
перерисуется сама, перезапуск нужен только чтобы подхватить файлы на VPS.

`profile_*` — намеренный префикс: имена кадров анкеты не должны совпадать с именами
эмоций, иначе `bot/faces.py` примет их за кадры диалога. `call.jpg` читает
`bot/call_screen.py`; если файла нет, бот пришлёт только текст.

Старые аниме-промпты (`prompts/vera-nano-banana.md`, `prompts/vera-profile-nano-banana.md`)
остаются как история прежнего набора; для перегенерации используйте этот файл.
