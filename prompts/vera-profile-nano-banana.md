# Промпты для Nano Banana: три кадра анкеты Веры

Модель: **Gemini 2.5 Flash Image** (в обиходе «Nano Banana»).
Задача: три кадра для карточки анкеты Веры в сценарии `first_message` — переписка
в приложении знакомств до первого свидания. Это та же Вера, что в `first_date`:
30 лет, редактор в небольшом издательстве, ироничная, настороженная, с надеждой,
которую сама от себя прячет.

Отличие от серии эмоций — в том, что здесь меняется сцена, а не мимика. В десяти
кадрах `scenarios/first_date/images/` заморожены и лицо, и кафе. В анкете кафе
не обязано быть тем же: анкета снималась в разных местах её жизни. Заморожено
в ней другое — человек. Если в кадре другая женщина, это не «похожая девушка»,
а брак: анкета должна читаться как та же Вера, к которой игрок потом придёт
на свидание.

Три кадра — это три её стороны, и все три она сама назвала в переписке:
работа и город, сальса по вторникам, караоке с подругами. Анкета не про красоту,
а про то, что за ней есть жизнь.

| файл | сцена | что должно читаться |
|---|---|---|
| `profile_1.jpg` | городская улица, день | главное фото: спокойно-ироничный взгляд в камеру, «я не товар» |
| `profile_2.jpg` | зал с зеркалами, тёплый свет | сальса: сосредоточена и довольна, танец, а не поза для фото |
| `profile_3.jpg` | караоке-комната, неон | ирония и азарт, микрофон, подруги фоном |

## Что заморожено во всех трёх кадрах

Внешность — та же, что в эталоне серии эмоций, слово в слово. Это не «примерно
такая девушка»: любая замена лица, причёски, цвета глаз или родинки — причина
перегенерировать кадр, а не «мелкая разница».

| | Вера (не менять) |
|---|---|
| возраст | 30 |
| лицо | круглее среднего, мягкие полные щёки, заметные скулы |
| глаза | серо-зелёные, чуть прищуренные, внимательные |
| брови | тонкие, прямые, на тон темнее волос |
| нос и губы | маленький прямой нос, естественные розовые губы с полной нижней |
| примета | маленькая тёмная родинка на левой скуле |
| макияж | почти никакого |
| волосы | медно-каштановое каре до подбородка с ровным срезом, прядь за правым ухом |
| одежда | оливковая льняная рубашка с открытым воротом, рукава подвёрнуты; допустима вариация в той же палитре |
| стиль | плоская аниме/вебтун-графика, мягкая заливка, тонкая чистая линия, приглушённая тёплая палитра, без жёстких бликов |
| размер | 1:1, 1024×1024, по пояс или крупнее, лицо в фокусе |

Из этого набора нельзя менять лицо, причёску, цвет глаз, родинку, возраст и макияж.
Меняются сцена, поза и выражение лица; одежда может варьироваться только в рамках,
оговорённых в промпте кадра. Смена сцены разрешена и нужна; смена человека — нет.

## Как работать (порядок важен)

1. **Возьмите эталон.** Лучший из десяти кадров эмоций — `scenarios/first_date/images/calm.jpg`
   (или эталонный портрет из шага 1 файла [`vera-nano-banana.md`](vera-nano-banana.md)).
   Его лицо и есть Вера.
2. **Сначала `profile_1.jpg`.** Он ближе всех к референсу: то же каре, тот же
   разворот плеч, только она больше не в кафе — стоит на городской улице, без стола,
   чашки и террасы. Главное фото анкеты утверждается первым: по нему игрок будет
   «узнавать» Веру.
3. **Выберите лучший вариант из 3–4 попыток.** Дальше прикрепляйте к нему эталон
   эмоций **и** утверждённый `profile_1.jpg` как второй референс — так модель видит
   и лицо, и как она выглядит вне кафе.
4. **Меняйте только сцену и позу.** Для кадров эмоций менялась только мимика;
   здесь меняется всё окружение, но не лицо. В каждом промпте об этом сказано
   отдельной фразой — не убирайте её.
5. **Не смешивайте с Аней.** Кадры `scenarios/reunion_call/images/` не прикрепляйте:
   модель подтянет каштановые волосы и свитер.
6. Не просите модель нарисовать рамку анкеты, сердечки, кнопки «нравится» и текст:
   карточку рисует бот, а на изображении любой текст превращается в кашу.

## Шаг 1. Блок идентичности

Этот кусок вставляется в начало каждого промпта, перед описанием сцены. Он
повторяется дословно: длинные вольные пересказы модель понимает как разрешение
менять внешность.

```
The same woman as in the attached reference images: a 30-year-old woman with a rounder
face, soft full cheeks and noticeable cheekbones, warm light skin, a small dark mole on
her left cheekbone. Grey-green eyes, slightly narrow and observant, thin straight
eyebrows a shade darker than her hair, small straight nose, natural rose lips with
a fuller lower lip, almost no makeup. Copper-auburn hair in a chin-length bob with
a blunt edge, the right side tucked behind her ear, a few strands falling forward
across the temple.
Flat anime / webtoon illustration, gentle cel shading, clean thin line art, muted warm
palette, no harsh highlights. 1:1 square, 1024×1024.
```

## Шаг 2. Три кадра

### 1. Главное фото — `profile_1.jpg`

**Назначение:** первое, что видит игрок в карточке анкеты и по чему запоминает
Веру. Лицо крупно, взгляд в камеру, спокойная ирония вместо приветливой маски.
Сцена — город днём, а не студийный фон: она живёт в этом городе, а не позирует.

```
Using the attached portrait as the reference, keep the exact same woman and change
only the scene, the framing and her expression.

Change the background completely: she is outdoors on a city street, not in the café
from the reference. Do not copy the café window, the wooden table, the white cup or
the curtains from the attached image — the reference is only for her face.

The same woman as in the attached reference images: a 30-year-old woman with a rounder
face, soft full cheeks and noticeable cheekbones, warm light skin, a small dark mole on
her left cheekbone. Grey-green eyes, slightly narrow and observant, thin straight
eyebrows a shade darker than her hair, small straight nose, natural rose lips with
a fuller lower lip, almost no makeup. Copper-auburn hair in a chin-length bob with
a blunt edge, the right side tucked behind her ear, a few strands falling forward
across the temple. She wears her olive-green linen shirt with an open collar, sleeves
rolled to the elbow.

Framing: head-and-shoulders, chest-up, centred, camera at her eye level, 1:1 square.
Her shoulders are turned slightly, the head faces the camera. She stands unhurried on
the pavement, arms relaxed, no cup in her hands and no table in front of her. This is
a dating-app main photo: it should read as a real woman who is a little tired of the
process and still curious, not as a polished model shot.

Expression: calm and level with the faintest hint of irony — one eyebrow raised by
a couple of millimetres, eyelids slightly narrowed, mouth closed, a small smile that
lives in the eyes more than on the lips. Gaze directly at the viewer. No coyness,
no flirting, no head tilt.

Setting: a quiet city street on an early-afternoon weekday. She stands on the pavement,
chest-up, and the street behind her is clearly out of focus: warm stone facades, shop
fronts with blank unreadable windows, green street trees, a strip of sunlit pavement and
the soft shapes of a pedestrian crossing. No table, no cup, no café terrace, no window
with curtains, no indoor interior — she is outdoors, on the street, and the background
is a blurred city, not a room. Background lower in contrast than her face, soft warm
bokeh in cream, honey and sage. Early-afternoon sun from the left gives a soft rim light
on her hair, while a broad soft fill keeps her face evenly lit and readable.

Flat anime / webtoon illustration, gentle cel shading, clean thin line art, muted warm
palette, no harsh highlights. High detail on the face.
No other people in the background, no readable text or signage, no watermark, no logo,
no jewelry, no glasses, no bicycle or car in the foreground.
```

**Негативные ограничения:**
- не менять лицо и причёску: та же форма лица, разрез и цвет глаз, линия бровей,
  нос, полная нижняя губа, родинка на левой скуле, каре до подбородка, прядь
  за правым ухом, медно-каштановый оттенок;
- не менять возраст и макияж: не молодить, не «улучшать», не добавлять стрелки,
  яркую помаду и контуринг;
- не менять одежду на свитер, пальто или вечернее платье — оливковая рубашка
  остаётся, иначе кадр тянет к Ане;
- не кафе и не интерьер: никакого стола, чашки, террасы, окна со шторами и
  витрины изнутри — кадр должен читаться как улица, а не как та же кофейня
  из десяти кадров эмоций;
- никакого текста: меню, вывески, надписи на чашке, подписи, водяные знаки,
  логотипы (модель рисует из букв кашу, и кадр становится непригодным);
- никаких людей на фоне и в отражениях, никаких украшений и очков;
- не фотореализм и не 3D: только плоская аниме/вебтун-графика;
- не «глянцевый» портрет для рекламы: без студийного света, без идеальной кожи.

**Что проверить после генерации:**
- лицо совпадает с эталоном: форма глаз, линия бровей, нос, губы, родинка на левой
  скуле на своём месте (это главный якорь кадра);
- причёска не «поплыла»: ровный срез каре, прядь за ухом, медный оттенок не ушёл
  в ярко-рыжий или тёмно-каштановый;
- возраст читается как 30, а не 24 и не 38; кожа не отфотошоплена;
- взгляд в камеру, ирония в глазах, а не пустая приветливая улыбка;
- фон читается как городская улица: нет стола, чашки, террасы, окна со шторами
  и интерьера кафе — иначе кадр снова станет копией кадра эмоций;
- фон размыт, без чужих людей, вывесок и текста; контраст фона ниже, чем у лица;
- кадр годится как аватарка: лицо достаточно крупно, макушка и плечи не обрезаны;
- кадр не выглядит как стоковая девушка из рекламы приложения.

### 2. Сальса — `profile_2.jpg`

**Назначение:** вторая сторона анкеты — у неё есть занятие, в котором она
разбирается и которое любит. В переписке она сама упомянула сальсу по вторникам,
и этот кадр должен совпадать с её словами: живой зал, движение, удовольствие
от того, что получается. Вульгарность здесь — не «риск», а прямой брак: на кадре
должен быть танец, а не тело.

```
Using the attached portrait as the reference, keep the exact same woman and change
only the scene, the pose and her expression.

The same woman as in the attached reference images: a 30-year-old woman with a rounder
face, soft full cheeks and noticeable cheekbones, warm light skin, a small dark mole on
her left cheekbone. Grey-green eyes, slightly narrow and observant, thin straight
eyebrows a shade darker than her hair, small straight nose, natural rose lips with
a fuller lower lip, almost no makeup. Copper-auburn hair in a chin-length bob with
a blunt edge, the right side tucked behind her ear, a few strands falling forward
across the temple. She wears a simple olive-sage wrap dress in the same muted palette
as her linen shirt, knee-length, sleeves rolled, with simple ballet flats.

Framing: three-quarter length, waist-up or a little lower, camera at her eye level,
1:1 square. She is caught mid-movement, as if the music just pulled her into a step:
shoulders turned, one arm raised in a frame, chin lifted, weight on one leg, the skirt
of the dress swinging slightly. The pose must read as dancing, not as a pose for
a photo.

Expression: focused and pleased — eyes open and bright, a small confident smile with
lips together or slightly parted, eyebrows relaxed, a faint flush from the movement.
She is doing something she is good at and enjoys it; she is not performing for the
camera.

Setting: a small salsa studio in the warm evening light — pale wooden floor, a wall of
mirrors softly blurred behind her, warm practical lamps, a strip of sage-green wall,
a blurred row of chairs. The mirrors stay vague and out of focus: no clear reflection
of her face and no doubled figure (a second Vera breaks the set). At most one or two
blurred dancers far in the background, out of focus, with no readable faces. Warm light
from the side and slightly above, soft shadow under the chin, no harsh flash.

Flat anime / webtoon illustration, gentle cel shading, clean thin line art, muted warm
palette, no harsh highlights. High detail on the face.
No vulgarity: the camera does not look up or down at her body, the dress is modest and
not revealing, no close-up on the hips or chest, no arched-back pin-up pose, no bedroom
look. No other person in focus, no readable text or signage, no watermark, no logo,
no jewelry, no glasses.
```

**Негативные ограничения:**
- не менять лицо и причёску: в динамике модель чаще всего «перерисовывает» лицо
  и меняет разрез глаз — это главный риск кадра;
- не менять возраст: не делать её юной танцовщицей или, наоборот, старше;
- без вульгарности: ракурс не снизу и не сверху на тело, нет акцента на бёдрах
  и груди, нет задранного подола, нет глубокого выреза, нет «горящего» взгляда
  в камеру — она танцует, а не соблазняет;
- не менять одежду на купальник, латекс и «костюм для латины»; допустима только
  спокойная вариация её оливковой рубашки-платья, балетки вместо каблуков;
- зеркала не должны показывать вторую Веру с другим лицом — отражения размыты;
- никакого текста: надписи на стенах, таблички, постеры, водяные знаки, логотипы;
- не фотореализм: та же плоская графика, что в остальных кадрах.

**Что проверить после генерации:**
- лицо то же, что в `profile_1.jpg` и в эталоне: глаза, брови, губы, родинка
  на левой скуле, каре до подбородка;
- поза читается как танец: движение есть в руках, корпусе и подоле, а не только
  в поднятой руке; кадр не выглядит как «стоит и улыбается в зале»;
- вульгарности нет: ракурс на уровне глаз, акцент на лице и движении, одежда
  не сползает и ничего не открывает;
- руки и пальцы целые — в динамике модель ломает кисти; подол и кисти рук
  не превратились в лишние пальцы;
- зеркала размыты и не дублируют лицо;
- свет тёплый, лицо читаемо; фон не перетягивает внимание;
- балетки, а не каблуки; платье — спокойная вариация её палитры, а не сценический
  костюм.

### 3. Караоке — `profile_3.jpg`

**Назначение:** третья сторона анкеты — та, где она не «редактор и умная женщина»,
а человек, с которым можно смеяться. В переписке она рассказывала про караоке
с подругами; кадр должен быть про вечер, а не про сцену и не про алкоголь.
Ироничная улыбка в этом кадре важнее, чем сама песня.

```
Using the attached portrait as the reference, keep the exact same woman and change
only the scene, the pose and her expression.

The same woman as in the attached reference images: a 30-year-old woman with a rounder
face, soft full cheeks and noticeable cheekbones, warm light skin, a small dark mole on
her left cheekbone. Grey-green eyes, slightly narrow and observant, thin straight
eyebrows a shade darker than her hair, small straight nose, natural rose lips with
a fuller lower lip, almost no makeup. Copper-auburn hair in a chin-length bob with
a blunt edge, the right side tucked behind her ear, a few strands falling forward
across the temple. She wears her olive-green linen shirt, sleeves rolled to the elbow —
this is a small private karaoke room with friends, not a stage.

Framing: chest-up or waist-up, she is clearly the main subject, 1:1 square, camera at
her eye level. She holds a black handheld microphone in one hand, close to her mouth,
the other hand free or half-raised. A slight three-quarter turn, her head is toward the
screen but her eyes come back to the camera — she is singing to her friends and
glancing at us.

Expression: an ironic half-smile, mouth open mid-phrase, eyes narrowed with amusement,
one eyebrow slightly raised — she knows this is a little ridiculous and enjoys it
anyway. Not drunk, not silly, not a staged wide grin.

Setting: a small private karaoke room at night — a glowing screen behind her shoulder
with blurred, unreadable abstract lyrics (only soft light, no letters), pink and teal
neon strips along the wall, a low table edge in soft bokeh. Two friends at the edge of
the frame, from behind or in profile, softly blurred and clearly secondary: they are
not looking at the camera, their faces are not readable. Neon light does not turn her
skin green or pink — her face stays warm and readable.

Flat anime / webtoon illustration, gentle cel shading, clean thin line art, muted warm
palette, no harsh highlights. High detail on the face.
No readable text anywhere: screen lyrics, signs, captions, watermark, logo. No jewelry,
no glasses. No alcohol bottles in the foreground, no glasses raised, no cigarettes,
no party clichés. No other person in focus.
```

**Негативные ограничения:**
- не менять лицо и причёску; неон не должен перекрасить волосы в розовый или
  зелёный — медный оттенок остаётся читаемым;
- не менять возраст и не «веселить» её: без пьяной улыбки, без широкой
  постановочной гримасы, без закатанных глаз;
- никакого читаемого текста: на экране только размытый свет, а не слова песни;
- подруги — фон: размыты, со спины или в профиль, не смотрят в камеру, не в фокусе;
- без пошлости и «вечеринки для взрослых»: без бутылок и бокалов на переднем плане,
  без сигарет, без задранной одежды, без языка и подмигивания;
- не менять одежду: та же оливковая рубашка, рукава подвёрнуты;
- микрофон в руке, а не «палка», не телефон, не бутылка;
- не фотореализм; та же палитра, что в остальных кадрах.

**Что проверить после генерации:**
- лицо то же, что в `profile_1.jpg` и в эталоне: глаза, брови, губы, родинка
  на левой скуле, каре до подбородка;
- улыбка ироничная и живая, а не пьяная и не «сцена»;
- микрофон читается как микрофон, лежит в руке правдоподобно, не закрывает лицо;
- на экране и в комнате нет читаемых букв; если модель нарисовала текст, кадр
  переснять — иначе он выглядит как обои с ошибкой;
- подруги размыты и вторичны, не отбирают внимание; их лиц не разобрать;
- неон не убил тёплый тон кожи, лицо читаемо и остаётся главным;
- на переднем плане нет бутылок, бокалов и сигарет;
- кроп: она главная, микрофон и рука в кадре, ничего важного не обрезано.

## Настройки и запреты

- Соотношение сторон: **1:1**, размер 1024×1024.
- Стиль один на все три кадра и на серию эмоций: плоская аниме/вебтун-графика,
  мягкая заливка, тонкая чистая линия, приглушённая тёплая палитра, без жёстких
  бликов и без фотореализма.
- Лицо, причёска, цвет глаз, родинка, возраст и «почти без макияжа» — идентичность.
  Меняются только сцена, поза и выражение лица.
- Одежда — оливковая льняная рубашка или её спокойная вариация в той же палитре
  (рубашка-платье для сальсы). Свитер, пальто, вечернее платье, купальник и
  «сценический костюм» запрещены.
- Запрещено: читаемый текст, вывески, меню, надписи на экране, водяные знаки,
  логотипы, украшения, очки; люди в фокусе на фоне; вульгарность, эротика,
  акцент на теле; смена возраста, цвета глаз и причёски; второй экземпляр Веры
  в отражении.
- Кадры анкеты — не кадры эмоций: фон в них сценный, а не замороженное кафе.
  В `profile_1.jpg` это городская улица без стола и чашки; замороженное кафе
  остаётся только в десяти эмоциях, и смешивать эти наборы в одном промпте не нужно.
- Рамку анкеты, сердечки, кнопки и любой интерфейс приложения модель не рисует —
  это делает бот, а не картинка.

## Если лицо «плывёт»

- Прикрепите эталон ещё раз и добавьте: `Do not redraw the face. Keep the exact same
  facial features as the reference; only the scene, the pose and the expression may
  change.`
- Если после смены сцены уехало лицо, сократите описание сцены до одной-двух фраз:
  длинные описания модель понимает как разрешение переписать человека.
- Сгенерируйте 4 варианта и выберите тот, где совпадают форма глаз, линия бровей,
  полная нижняя губа и родинка на левой скуле.
- Если поплыла родинка, цвет волос или срез каре — вернитесь к эталону: это якоря,
  по которым видно, что кадр остался тем же человеком.
- Для `profile_2.jpg` и `profile_3.jpg` прикрепляйте два референса: эталон эмоций
  (лицо) и утверждённый `profile_1.jpg` (как Вера выглядит на улице). Если модель
  копирует из `profile_1.jpg` ещё и фон — добавьте: `Keep the face from the first
  reference and the new scene from the prompt; do not copy the background of the
  reference.`

## Имена файлов и связка с ботом

Файлы кладутся в папку сценария `scenarios/first_message/images/`:

```
scenarios/first_message/images/profile_1.jpg
scenarios/first_message/images/profile_2.jpg
scenarios/first_message/images/profile_3.jpg
```

Рядом лежат десять кадров эмоций — копия `scenarios/first_date/images/`
(`calm.jpg`, `guarded.jpg`, …). Анкета и эмоции — два разных набора: первые три
файла показываются игроку как карточка до начала переписки, остальные десять
подставляются в диалог по настроению Веры. Подробности — в
[`scenarios/first_message/images/README.md`](../scenarios/first_message/images/README.md).

Префикс `profile_*` намеренный: имена кадров анкеты не должны совпадать с именами
эмоций, иначе `bot/faces.py` примет их за кадры диалога. Если кадров анкеты ещё
нет, бот просто показывает текстовую карточку — переписка начинается так же.
