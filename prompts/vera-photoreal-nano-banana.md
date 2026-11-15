# Промпты для Nano Banana: фотореалистичная Вера (весь набор)

Модель: **Gemini 2.5 Flash Image** (в обиходе «Nano Banana»).
Задача: перегенерировать **все** фотографии Веры в фотореализме — эталон, три кадра
анкеты, десять эмоций и фото для экрана звонка. Вера остаётся той же женщиной:
30 лет, редактор, медное каре, серая родинка на левой скуле, белая гладкая блуза.
**На фотографиях она выглядит моложе своих лет — около 27**; стройная, милая и
симпатичная, без «усталой серьёзности».

Это осознанная смена визуального языка: Ева уже фотореалистичная, Вера теперь тоже.
Аня (выключенный сценарий) остаётся в старой аниме-серии и в этот набор не входит.

## Что нужно получить

| набор | куда | файлы | сколько |
|---|---|---|---|
| эталон | вне `scenarios/` | `prompts/reference/vera-cafe-base.jpg` | 1 (из 3–4 попыток) |
| анкета | `scenarios/first_message/vera/images/` | `profile_1..4.jpg` | 4 |
| эмоции | `scenarios/first_date/vera/images/` | `calm` … `tears` | 10 |
| звонок | `scenarios/first_call/vera/images/` | `call.jpg` | 1 |

Итого 15 кадров для бота. Старые файлы заменяются файлами с теми же именами —
код и сценарии менять не нужно.

## Что заморожено во всех кадрах

| | Вера (не менять) |
|---|---|
| возраст | 30, но **выглядит около 27**: свежая гладкая кожа, без глубоких носогубных складок и «гусиных лапок»; кадр, где она выглядит на 32+, — брак |
| лицо | милое и симпатичное: мягкий овал, плавные скулы, лёгкие черты, тёплое дружелюбное обаяние — не «тяжёлое» и не полное |
| кожа | светлая тёплая, живая: поры, мелкие линии, без ретуши |
| глаза | серо-зелёные, чуть прищуренные, внимательные |
| брови | тонкие, прямые, на тон темнее волос |
| нос и губы | маленький прямой нос, естественные розовые губы с полной нижней |
| примета | маленькая тёмная родинка на левой скуле |
| макияж | почти никакого; **на `profile_1` и `profile_2` — лёгкий естественный** (нюдовые тона, чуть туши, намёк на румяна) |
| волосы | медно-каштановое каре до подбородка с ровным срезом, прядь за правым ухом, несколько прядей у виска |
| телосложение | стройная, лёгкая фигура; грудь второго–третьего размера — естественная, без преувеличения |
| одежда | **белая гладкая блуза** с мягким открытым воротом — на эталоне, в эмоциях и на звонке; в анкете у каждого кадра свой наряд и свой цвет |
| стиль | фотореализм, 50 мм, естественная кожа, мягкий свет, приглушённая тёплая палитра, ощущение живого кадра |
| размер | 1:1, 1024×1024, по пояс или крупнее, лицо в фокусе |

Смена сцены, позы и выражения разрешена; смена человека, возраста-на-вид,
причёски, цвета глаз и родинки — брак. Фон в кадрах эмоций заморожен так же
жёстко: это одно и то же летнее кафе во всех десяти кадрах.

## Как работать (порядок важен)

1. **Эталон — один раз.** Сгенерируйте 3–4 варианта портрета в кафе (шаг 1), выберите
   лучший. Это единственный раз, когда лицо создаётся с нуля.
2. **Сохраните утверждённый эталон вне сценариев** — `prompts/reference/vera-cafe-base.jpg`.
   Бот эту папку не читает; если положить эталон в `scenarios/`, `bot/faces.py` может
   принять его за кадр настроения.
3. **Сначала десять эмоций.** Все десять делаются от эталона: прикрепляйте
   `vera-cafe-base.jpg` и меняйте только выражение лица. Фон, свет, поза и одежда
   остаются как на эталоне.
4. **Потом четыре кадра анкеты.** Сначала `profile_1.jpg` (парк), он утверждается; для
   `profile_2..4.jpg` прикрепляйте эталон **и** `profile_1.jpg`.
5. **Последним — `call.jpg`.** Домашний вечерний портрет от эталона.
6. **Старые кадры (в оливковой рубашке, «полнее и старше») не прикрепляйте как
   референс.** Модель вернёт прежнее лицо и оливку — фотореализм не получится.
   Референс — только новые кадры в белой блузе.
7. **Не смешивайте с Евой.** Её фотореалистичные кадры — другая женщина; прикрепите
   их случайно — получится третье лицо.
8. На каждую эмоцию и кадр генерируйте 2–4 варианта: мимика и лицо — лотерея даже
   у хорошей модели.

## Шаг 1. Эталонный портрет — кафе

```
A photorealistic portrait photograph of one woman: 30 years old but looks young
for her age — around 27, a fresh smooth face with no deep nasolabial folds or
crow's feet. A sweet, pretty face with a soft oval, gently defined cheekbones
and light delicate features, a warm friendly charm. Light warm skin with real
texture — visible pores, fine lines, no retouching. Grey-green eyes, slightly
narrow and observant, thin straight eyebrows a shade darker than her hair, a
small straight nose, natural rose lips with a fuller lower lip. A small dark
mole on her left cheekbone. Copper-auburn hair in a chin-length bob with a
blunt edge, the right side tucked behind her ear, a few strands falling forward
across the temple. Slim, graceful build with a medium, naturally proportioned
bust. She wears a white smooth blouse with a soft open collar, clean and
simple, no patterns.

Expression: calm and level with the faintest thread of irony — one eyebrow raised
by a couple of millimetres, eyelids slightly narrowed, mouth closed, a small smile
that lives in the eyes more than on the lips. She looks directly into the lens.
Not flirting, not posing, not a wide beauty-pageant smile.

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
- не старить: выглядит около 27, а не на 30–35 — без глубоких складок и тяжёлого
  зрелого лица;
- не делать лицо полным и тяжёлым: лицо лёгкое, милое; фигура стройная;
- грудь — естественная, второго–третьего размера: без преувеличения, без
  сексуализации кадра;
- не менять родинку на левой скуле, разрез и цвет глаз, линию бровей, полную нижнюю
  губу, срез каре и прядь за правым ухом;
- не менять одежду на свитер, пальто или платье — белая блуза остаётся, иначе
  кадр тянет к Ане;
- никакого текста: меню, вывески, надписи на чашке, водяные знаки, логотипы;
- никаких людей и официантов в фоне и в отражениях, никаких украшений и очков;
- не рекламный глянец: без студийного света и идеальной позы.

**Что проверить после генерации:**
- лицо читается как живое и милое: мягкий овал, лёгкие черты, серо-зелёные глаза,
  брови, губы, родинка на левой скуле на своём месте;
- выглядит около 27, кожа с текстурой, а не «отфотошопленная»;
- фигура стройная, силуэт лёгкий; грудь второго–третьего размера, без
  преувеличения;
- каре с ровным срезом, прядь за правым ухом, медный оттенок не ушёл в рыжий;
- белая гладкая блуза, ворот открыт, без узоров;
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

Do not redraw the face: she looks young for her age, around 27 — smooth fresh skin,
no deep lines. Same sweet pretty face with a soft oval and gently defined cheekbones,
same grey-green eyes, same thin straight eyebrows, same small straight nose, same
fuller lower lip, same small dark mole on the left cheekbone, same copper-auburn
chin-length bob with a blunt edge and the right side tucked behind the ear. Slim,
graceful build with a medium, naturally proportioned bust. Same white smooth
blouse with a soft open collar. Same age, same real skin texture.

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

У каждого кадра свой наряд и свой доминирующий цвет: **белый → пыльно-розовый →
горчичный → морской** (на море Вера в белом, но доминируют голубая волна и небо).
Одинаковый наряд на кадрах читается как одно и то же фото.
На `profile_1` и `profile_2` — лёгкий естественный макияж.

### 1. Главное фото, город — `profile_1.jpg`

Назначение: первое, что видит игрок в карточке и по чему запоминает Веру. Лицо крупно,
взгляд в камеру, спокойная ирония вместо приветливой маски. Сцена — парк днём.
Наряд — та же белая блуза, что на эталоне; цвет кадра — **белый**.

```
Using the attached portrait as the reference, keep the exact same woman and change
only the scene, the framing and her expression. Do not redraw her face; she looks
young for her age, around 27 — smooth fresh skin, no deep lines.

The same woman as in the attached reference: a sweet pretty face with a soft oval,
gently defined cheekbones and light delicate features, light warm skin with real
texture, a small dark mole on her left cheekbone. Grey-green eyes, slightly narrow
and observant, thin straight eyebrows a shade darker than her hair, small straight
nose, natural rose lips with a fuller lower lip. Copper-auburn hair in a chin-length
bob with a blunt edge, the right side tucked behind her ear, a few strands falling
forward across the temple. Slim, graceful build with a medium, naturally
proportioned bust. She wears her white smooth blouse with a soft open collar.
Light natural makeup: soft nude tones, a touch of mascara,
a hint of blush — fresh, not heavy.

Framing: head-and-shoulders, chest-up, centred, camera at her eye level, 1:1 square.
Her shoulders are turned slightly, the head faces the camera. She stands unhurried on
a wide walking path, arms relaxed, no cup in her hands and no table in front of her.

Expression: calm and level with the faintest hint of irony — one eyebrow raised by
a couple of millimetres, eyelids slightly narrowed, mouth closed, a small smile that
lives in the eyes more than on the lips. Gaze directly at the viewer. No coyness, no
flirting, no head tilt.

Setting: a quiet green park in early afternoon. She stands on a walking path, chest-up,
and the park behind her is clearly out of focus: tall summer trees with soft foliage,
bushes and a flowerbed, dappled sunlight on the path, a strip of lawn and the faint
shape of a bench far behind her. No buildings, no roads with cars, no playgrounds,
no café terrace — she is outdoors in a park, and the background is blurred greenery,
not a street and not a room. Background lower in contrast than her face, soft warm
bokeh in cream, honey and sage. Early-afternoon sun from the left gives a soft rim
light on her hair while a broad soft fill keeps her face evenly lit and readable.

Photorealistic photograph, natural skin texture with visible pores and fine lines, no
beauty retouching, 50mm lens at eye level, shallow depth of field, soft natural light,
muted warm color grading, candid editorial feel. 1:1 square, 1024×1024. No other people
in the background, no readable text or signage, no watermark, no logo, no jewelry, no
glasses, no bicycle or car in the foreground.
```

**Негативные ограничения:**
- не менять лицо, причёску, цвет глаз, родинку и возраст-на-вид (около 27);
- не делать лицо полным: черты лёгкие, силуэт стройный;
- не утяжелять макияж: только лёгкий естественный, без стрелок и яркой помады;
- не кафе, не интерьер и не улица с домами: только парк — деревья, дорожка, зелень;
- не менять одежду на свитер, пальто или вечернее платье — белая блуза;
- не фотореализм → только фотореализм: без аниме, 3D, живописи и рекламного глянца;
- никакого текста: вывески, меню, надписи, водяные знаки, логотипы;
- никаких людей в фоне и в отражениях, никаких украшений и очков.

**Что проверить:** лицо совпадает с эталоном (родинка, глаза, губы, каре); выглядит
около 27, кожа живая; лёгкий макияж читается, но не «нарисованный»; взгляд в камеру
и ирония в глазах; фон читается как парк (деревья, дорожка), а не кафе и не улица;
силуэт стройный; грудь естественная, второго–третьего размера, без преувеличения;
кадр годится как аватарка — лицо крупно, макушка и плечи не обрезаны.

### 2. Сальса — `profile_2.jpg`

Назначение: вторая сторона — занятие, в котором она разбирается и которое любит.
В переписке она упомянула сальсу по вторникам; кадр должен совпадать с её словами:
живой зал, движение, удовольствие от того, что получается. На кадре — танец, не тело.
Наряд — пыльно-розовое платье; цвет кадра — **пыльно-розовый**.

```
Using the attached portrait as the reference, keep the exact same woman and change
only the scene, the pose, the clothing and her expression. Do not redraw her face;
she looks young for her age, around 27 — smooth fresh skin, no deep lines.

The same woman as in the reference: a sweet pretty face with a soft oval, gently
defined cheekbones and light delicate features, light warm skin with real texture,
a small dark mole on her left cheekbone. Grey-green eyes, slightly narrow and
observant, thin straight eyebrows, small straight nose, natural rose lips with a
fuller lower lip. Copper-auburn chin-length bob with a blunt edge, the right side
tucked behind her ear, a few strands loose. Slim, graceful build with a medium,
naturally proportioned bust. She wears a simple dusty-rose wrap dress, knee-length,
sleeves rolled, with simple ballet flats.
Light natural makeup: soft nude tones, a touch of mascara, a hint of blush —
a little more than on the street photo, still fresh and light.

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

**Негативные ограничения:** не менять лицо и причёску; не старить — выглядит около 27;
не делать фигуру полной: она стройная, грудь естественная второго–третьего размера,
без преувеличения; без вульгарности (ракурс на уровне глаз, акцент
на лице и движении, одежда не сползает); не менять платье на купальник/латекс/сценический
костюм; макияж не утяжелять — лёгкий; зеркала размыты и не показывают вторую Веру;
никакого текста; фотореализм, а не аниме.

**Что проверить:** лицо как в эталоне; выглядит молодо, фигура стройная; пыльно-розовое
платье читается (не красное и не бордо); поза читается как танец, а не «стоит и
улыбается»; руки и пальцы целые; вульгарности нет; балетки, а не каблуки; зеркала
размыты; свет тёплый, лицо читаемо.

### 3. Караоке — `profile_3.jpg`

Назначение: третья сторона — та, где она не «редактор и умная женщина», а человек,
с которым можно смеяться. В переписке она рассказывала про караоке с подругами;
кадр про вечер, а не про сцену и не про алкоголь. Наряд — горчичный трикотажный
топ; цвет кадра — **горчичный**.

```
Using the attached portrait as the reference, keep the exact same woman and change
only the scene, the pose and her expression. Do not redraw her face; she looks young
for her age, around 27 — smooth fresh skin, no deep lines.

The same woman as in the reference: a sweet pretty face with a soft oval, gently
defined cheekbones and light delicate features, light warm skin with real texture,
a small dark mole on her left cheekbone. Grey-green eyes, slightly narrow and
observant, thin straight eyebrows, small straight nose, natural rose lips with a
fuller lower lip. Copper-auburn chin-length bob with a blunt edge, the right side
tucked behind her ear. Slim, graceful build with a medium, naturally proportioned
bust. She wears a soft mustard-yellow knit top — this is a small private karaoke
room with friends, not a stage.

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

**Негативные ограничения:** не менять лицо и причёску; не старить; не делать фигуру
полной, грудь естественная без преувеличения; неон не перекрашивает волосы; не «веселить» её (без пьяной улыбки и
постановочной гримасы); на экране только размытый свет, без слов; подруги — размытый
фон; без бутылок и бокалов на переднем плане; топ горчичный, не белый и не розовый;
микрофон в руке — не телефон и не бутылка; фотореализм.

**Что проверить:** лицо как в эталоне; выглядит молодо, силуэт стройный; горчичный топ
читается; улыбка ироничная и живая; микрофон читается как микрофон и не закрывает лицо;
на экране нет читаемых букв; подруги размыты и вторичны; неон не убил тёплый тон кожи;
кроп удачный.

### 4. Море — `profile_4.jpg`

Назначение: четвёртая сторона — отпуск, единственное время, когда она не редактор.
Пляж, море, белый отель и бассейн с зонтиками на фоне. Наряд — белые шорты и лёгкая
рубашка; цвет кадра — **морской**. Без тёмных очков: глаза — главный якорь кадра.

```
Using the attached portrait as the reference, keep the exact same woman and change
only the scene, the pose, the clothing and her expression. Do not redraw her face;
she looks young for her age, around 27 — smooth fresh skin, no deep lines.

The same woman as in the reference: a sweet pretty face with a soft oval, gently
defined cheekbones and light delicate features, light warm skin with real texture,
a small dark mole on her left cheekbone. Grey-green eyes, slightly narrow and
observant, thin straight eyebrows, small straight nose, natural rose lips with a
fuller lower lip. Copper-auburn chin-length bob with a blunt edge, the right side
tucked behind her ear, a few strands moved by a light sea breeze. Slim, graceful
build with a medium, naturally proportioned bust. She wears white summer shorts
and a light, airy shirt in pale cream with a soft open collar, sleeves rolled —
light summer clothes, not swimwear. No sunglasses, no hat.

Framing: chest-up or three-quarter, centred, camera at her eye level, 1:1 square.
She stands relaxed, weight on one leg, arms loose — an easy vacation pose, not
a staged glamour shot.

Expression: calm happiness — a soft genuine smile with lips together or just
parted, relaxed eyes looking at the viewer, shoulders at ease. The face of someone
on vacation with nowhere to be in a hurry. Not excitement, not a wide tourist grin.

Setting: a seafront on a bright summer day. Behind her, softly out of focus: the sea
with gentle waves, a strip of sandy beach, a white hotel building in warm sunlight
and a swimming pool with sun umbrellas between the hotel and the beach. The hotel
and the umbrellas are readable as shapes but stay blurred: no readable signs, logos
or text on them. Bright natural sunlight from the left, a soft fill from the sky
keeps her face evenly lit and readable; the sea and sky stay lower in contrast than
her face. No people in focus, no crowds on the beach.

Photorealistic photograph, natural skin texture, no beauty retouching, 50mm lens at
eye level, shallow depth of field, soft natural light, warm airy color grading, candid
editorial feel. 1:1 square, 1024×1024. No sunglasses, no hat, no jewelry, no glasses.
No swimwear: shorts and shirt only. No other people in focus, no readable text or
signage anywhere, no watermark, no logo.
```

**Негативные ограничения:** не менять лицо и причёску; не старить — выглядит около 27;
не делать фигуру полной, грудь естественная без преувеличения; не купальник и не
бикини — только шорты и рубашка; не «пляжный гламур»: камера на уровне глаз, поза
обычная; тёмные очки и шляпа запрещены; море, отель и бассейн — фон, а не главный
план; никакого текста на здании и зонтиках; никаких людей в фокусе; медное каре не
выгорает в жёлтый; фотореализм.

**Что проверить:** лицо как в эталоне; выглядит около 27; выражение — спокойное
счастье, а не туристический восторг; тёмных очков нет, серо-зелёные глаза читаются;
наряд — белые шорты и светлая рубашка; фон: море, пляж, белый отель, бассейн с
зонтиками — размыты, без надписей; силуэт стройный, грудь естественная; волосы
растрёпаны ветром, но каре и медный оттенок читаются; кроп удачный.

## Шаг 4. Фото для экрана звонка — `scenarios/first_call/vera/images/call.jpg`

Назначение: единственная картинка сцены-созвона. По сюжету четверг, вечер, она дома
и ждёт звонка. Интерфейс звонка (имя, «мобильный», «Вызов…») рисует код — модель его
не рисует.

```
Using the attached portrait as the reference, keep the exact same woman and change
only the scene, the pose and her expression. Do not redraw her face; she looks young
for her age, around 27 — smooth fresh skin, no deep lines.

The same woman as in the reference: a sweet pretty face with a soft oval, gently
defined cheekbones and light delicate features, light warm skin with real texture,
a small dark mole on her left cheekbone. Grey-green eyes, slightly narrow and
observant, thin straight eyebrows, small straight nose, natural rose lips with a
fuller lower lip. Copper-auburn chin-length bob with a blunt edge, the right side
tucked behind her ear. Slim, graceful build with a medium, naturally proportioned
bust. She wears her white smooth blouse with a soft open collar.

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

**Негативные ограничения:** не менять лицо и причёску; не старить; не вечернее платье
и не «свидание» — домашняя белая блуза; никакого текста и интерфейса звонка на
картинке; не рекламный глянец; без бокалов и алкоголя; телефон не в руках; никаких
чужих людей.

**Что проверить:** лицо как в эталоне; выглядит около 27; кадр читается как «дома,
вечер, ждёт звонка»; тёплый свет, лицо читаемо; фон размыт; нет текста и интерфейса;
кроп по плечи.

## Настройки и запреты (общие)

- Соотношение сторон: **1:1**, размер 1024×1024.
- Стиль один на все 14 кадров и на все сцены: фотореализм, естественная кожа,
  мягкий свет, приглушённая тёплая палитра. Никакого аниме, вебтуна, 3D, живописи
  и «пластикового» глянца.
- Лицо, причёска, цвет глаз, родинка, возраст-на-вид («выглядит около 27»),
  стройность и грудь второго–третьего размера — идентичность. Меняются только
  сцена, поза, одежда и выражение.
- Белая гладкая блуза — часть личности (эталон, эмоции, звонок); в танце —
  пыльно-розовое платье, в караоке — горчичный топ. Свитер, пальто, вечернее платье,
  купальник и сценический костюм запрещены: они тянут к Ане.
- Цвета кадров анкеты не повторяются: белый → пыльно-розовый → горчичный →
  морской. На море белая одежда допустима: доминирует голубой фон моря и неба.
- Лёгкий макияж — только на `profile_1` и `profile_2`; на остальных кадрах почти
  никакого. Яркая помада, стрелки и «вечерний» макияж запрещены.
- Фон эмоций — одно и то же летнее кафе: окно с занавесками, зелень и тёплый камень
  за стеклом, деревянный стол, белая чашка кофе, стакан воды, мягкое боке.
- Запрещено: читаемый текст, вывески, меню, надписи на чашке, водяные знаки,
  логотипы, украшения, очки; люди в фокусе на фоне; вульгарность, эротика, акцент на
  теле; смена возраста-на-вид, цвета глаз и причёски; полные тяжёлые черты лица;
  второй экземпляр Веры в отражении; смешивание с наборами Ани и Евы.
- Рамку анкеты, сердечки, кнопки и экран звонка модель не рисует — это делает бот.

## Если лицо или фон «плывут»

- Прикрепите эталон ещё раз и добавьте: `Do not redraw the face. Keep the exact same
  facial features as the reference; only the expression may change.`
- Если Вера вышла старше своих лет, добавьте: `She looks young for her age, around
  27. Do not age her face: smooth fresh skin, no deep lines.`
- Если лицо вышло полным или тяжёлым, добавьте: `Slim, graceful build; a sweet light
  face with delicate features. Do not make the face heavy or full.`
- Если грудь вышла преувеличенной, добавьте: `Naturally proportioned medium bust;
  no exaggeration, no sexualization — this is an everyday candid photo, not glamour.`
- Если поехал фон, добавьте отдельно: `Keep the background identical to the reference:
  same window, same curtains, same table, same cup, same bokeh. Change only the
  expression.`
- Уменьшите формулировку эмоции до одной фразы — длинные описания модель часто
  трактует как разрешение менять внешность.
- Сгенерируйте 4 варианта и выберите тот, где совпадают форма глаз, линия бровей,
  полная нижняя губа, родинка на левой скуле, белая блуза и белая чашка на столе.
- Если поплыла родинка или чашка — вернитесь к эталону: это якоря, по которым видно,
  что кадр остался тем же человеком и тем же кафе.
- Если после смены сцены уехало лицо, сократите описание сцены до одной–двух фраз.
- Для кадров `profile_2..4` прикрепляйте два референса: эталон (лицо) и утверждённый
  `profile_1.jpg` (как Вера выглядит на улице). Если модель копирует фон из
  `profile_1.jpg`, добавьте: `Keep the face from the first reference and the new scene
  from the prompt; do not copy the background of the reference.`

## Имена файлов и связка с ботом

```
prompts/reference/vera-cafe-base.jpg          эталон, бот его не читает

scenarios/first_message/vera/images/profile_1.jpg  анкета: парк, белый
scenarios/first_message/vera/images/profile_2.jpg  анкета: сальса, пыльно-розовый
scenarios/first_message/vera/images/profile_3.jpg  анкета: караоке, горчичный
scenarios/first_message/vera/images/profile_4.jpg  анкета: море, морской

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
