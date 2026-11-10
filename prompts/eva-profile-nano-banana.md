# Промпты для Nano Banana: четыре кадра анкеты Евы

Модель: **Gemini 2.5 Flash Image** (в обиходе «Nano Banana»).
Задача: четыре кадра для карточки анкеты Евы в сценарии `eva_message` — переписка
в приложении знакомств. Ева, 26, фрилансер-фотограф: уверенная, амбициозная,
прямая, живёт на скорости — мотоцикл, поездки, рестораны, съёмки. Анкета не про
красоту, а про то, что за ней есть жизнь.

**Стиль — фотореализм**, в отличие от аниме-серии Веры и Ани. Это осознанно:
разные героини, разные наборы. Не смешивать референсы и стили.

## Четыре кадра

| файл | сцена | что должно читаться |
|---|---|---|
| `profile_1.jpg` | съёмочная локация на крыше, золотой час, камера в руках | работа и «я не товар»: прямой уверенный взгляд |
| `profile_2.jpg` | мотоцикл на загородной дороге, закат, шлем в руке | скорость и свобода |
| `profile_3.jpg` | горная дорога или побережье, рюкзак, ветер | поездки без расписания |
| `profile_4.jpg` | ресторан, тёплый вечерний свет, бокал | вкус, вечер, «чего ищет» |

## Что заморожено во всех четырёх кадрах

Это один человек, а не четыре похожие девушки. Лицо, веснушки, разрез и цвет глаз,
**светлый блонд**, причёска, серьга и возраст — якоря. Сцена и одежда меняются в
каждом кадре; человек — нет.

| | Ева (не менять) |
|---|---|
| возраст | 26 |
| лицо | овальное, высокие скулы, мягкая линия подбородка |
| кожа | светлая тёплая, лёгкие веснушки на носу и верхних щеках |
| глаза | зелёно-карие, миндалевидные, прямой спокойный взгляд |
| брови | светлые, блондинистые, на пару тонов темнее волос, естественной формы |
| нос и губы | небольшой прямой нос, естественные полные губы, нюдовый оттенок |
| волосы | светлый тёплый блонд (медовый, чуть выгоревший на концах), собраны в низкий свободный хвост, пряди у лица |
| примета | маленькая серебряная серьга-кольцо в левом ухе |
| макияж | почти никакого, кожа живая, не «отфотошопленная» |
| телосложение | спортивное, подтянутое |
| стиль | фотореализм, естественная кожа с порами, 50 мм, мягкий свет, приглушённая тёплая палитра, кадр как из жизни, а не из рекламы |
| размер | 1:1, 1024×1024, по пояс или крупнее, лицо в фокусе |

## Одежда и цвет по кадрам

Четыре кадра стоят в анкете рядом, поэтому одинаковый наряд и одинаковый цвет читаются
как одно и то же фото. У каждого кадра — свой комплект и свой доминирующий цвет:

| файл | одежда | доминирующий цвет |
|---|---|---|
| `profile_1.jpg` | свободная льняная рубашка с подвёрнутыми рукавами поверх белой майки, тёмно-синие джинсы | глубокий зелёный |
| `profile_2.jpg` | кожаная косуха поверх чёрной футболки, выцветшие чёрные джинсы, потёртые коричневые ботинки | петроль-синий (глубокий сине-зелёный) |
| `profile_3.jpg` | лёгкая полевая куртка поверх белой футболки, хаки-брюки, трекинговые ботинки | горчичный (тёплый жёлтый) |
| `profile_4.jpg` | шёлковое платье-комбинация, светлый кардиган на плечах | бордо (винный) |

Цвета не повторяются: зелёный → петроль-синий → горчичный → бордо. Одежда простая, по
погоде и по сцене, без логотипов, надписей и «брендов»; ничего не расстёгнуто ради
эффекта и ничего не подчёркивает тело.

## Как работать (порядок важен)

1. **`profile_1.jpg` создаётся с нуля.** Референса ещё нет: лицо Евы рождается
   здесь. Сгенерируйте 3–4 варианта из шага 2.1, выберите один — он станет
   эталоном. Главное фото анкеты утверждается первым.
2. **`profile_2..4.jpg` — только с референсом.** Прикрепляйте утверждённый
   `profile_1.jpg` как изображение-референс и просите сохранить лицо. Меняются
   сцена, поза, одежда и выражение.
3. **Не смешивайте с Верой и Аней.** Не прикрепляйте `scenarios/first_date/images/*`
   и `scenarios/friday_evening/images/*`: модель подтянет медно-каштановое каре,
   оливковую рубашку и аниме-стиль.
4. **Меняйте сцену, позу и одежду, но не человека.** В каждом промпте есть фраза про
   сохранение лица — не убирайте её. Одежда в каждом кадре своя и своего цвета (см.
   таблицу «Одежда и цвет по кадрам»).
5. **Модель не рисует интерфейс.** Рамку анкеты, точки, сердечки и кнопки рисует
   бот; на изображении любой текст превращается в кашу.
6. **Никакой пошлости.** Ева прямая и не боится желания, но кадры анкеты — про
   жизнь и характер, а не про тело. Ракурс на уровне глаз, одежда по погоде.

## Шаг 1. Блок идентичности

Этот кусок идёт в начало каждого промпта. Для `profile_1.jpg` — без фразы про
референс, для остальных — с ней. Повторять дословно: длинные вольные пересказы
модель понимает как разрешение менять внешность.

```
A photorealistic portrait of one woman: 26 years old, an oval face with high cheekbones
and a soft but defined jawline, light warm skin with a light scatter of fine freckles
across the nose bridge and upper cheeks. Green-hazel almond-shaped eyes with a direct,
level gaze, soft blonde eyebrows one or two shades darker than her hair, a small
straight nose, natural full lips in a soft nude tone. Light warm honey-blonde hair,
slightly sun-bleached at the ends, clearly blonde and not mousy light brown, pulled
back into a loose low ponytail with a few strands escaping to frame her face. A single
small silver hoop earring in her left ear. Almost no makeup, real skin texture, no
retouching. Athletic, lean build. She looks like a real person, not a model: relaxed
confidence, a hint of irony, no posing, no coyness.

Photorealistic photograph, natural skin texture with visible pores and fine lines, no
beauty retouching, 50mm lens at eye level, shallow depth of field, soft natural light,
muted warm color grading, candid editorial feel. 1:1 square, 1024×1024. No text, no
watermark, no logo, no other people in focus.
```

## Шаг 2. Четыре кадра

### 1. Главное фото — `profile_1.jpg`

**Назначение:** первое, что видит игрок в карточке и по чему запоминает Еву. Она
фотограф на съёмке, камера в руках, взгляд в объектив: уверенно, без кокетства.
Это «работа и о себе» — кадр должен читаться как день из её жизни.

```
A photorealistic portrait of one woman: 26 years old, an oval face with high cheekbones
and a soft but defined jawline, light warm skin with a light scatter of fine freckles
across the nose bridge and upper cheeks. Green-hazel almond-shaped eyes with a direct,
level gaze, soft blonde eyebrows one or two shades darker than her hair, a small
straight nose, natural full lips in a soft nude tone. Light warm honey-blonde hair,
slightly sun-bleached at the ends, clearly blonde and not mousy light brown, pulled
back into a loose low ponytail with a few strands escaping to frame her face. A single
small silver hoop earring in her left ear. Almost no makeup, real skin texture, no
retouching. Athletic, lean build.

She is a freelance photographer at work: standing on a city rooftop in the late
afternoon, a professional mirrorless camera held loosely in both hands at chest level,
one hand resting on the lens, the camera strap over her shoulder. She wears a loose
forest-green linen shirt with the sleeves rolled to the elbow, a white tank top showing
at the open collar, and dark indigo jeans. She has just lowered the camera and looks
straight into the portrait lens. Slight three-quarter turn of the shoulders, head facing
the viewer. Head-and-shoulders to chest-up framing, centred.

Expression: calm, confident, level. A small closed-lip smile, one eyebrow raised by a
couple of millimetres, eyes direct and alive. Not flirting, not posing, not a wide
beauty-pageant smile.

Setting: a city rooftop at golden hour. Behind her, clearly out of focus: warm tiled
roofs, antennas, a strip of sky in peach and pale gold, the soft blur of a distant
street. No readable signs or text, no other people, no recognizable landmarks. Warm
low sun from the left gives a soft rim light on her hair; a broad soft fill keeps her
face readable.

Photorealistic photograph, natural skin texture with visible pores and fine lines, no
beauty retouching, 50mm lens at eye level, shallow depth of field, soft natural light,
muted warm color grading, candid editorial feel. 1:1 square, 1024×1024. No text, no
watermark, no logo, no other people in focus. No sunglasses, no hat, no jewelry except
the small silver hoop in the left ear.
```

**Негативные ограничения:**
- не фотореализм → только фотореализм: без аниме, вебтуна, 3D-рендера, живописи;
- не пластиковая кожа: без «гламурного» ретуширования, без студийного глянца,
  без идеальных кукольных черт;
- не менять возраст: 26, а не 19 и не 35; без детской округлости лица;
- не менять веснушки, цвет и разрез глаз, форму бровей, серьгу в левом ухе;
- не менять причёску: низкий свободный хвост, пряди у лица, светлый медовый блонд;
- камера в руках должна выглядеть как камера: ровный корпус, объектив, ремень; кисти
  и пальцы целые, без лишних пальцев и «сплавленных» рук;
- никакого текста: надписи на камере-реквизите, рекламные щиты, вывески, водяные
  знаки, логотипы;
- никаких людей на фоне, никаких отражений с лицами;
- не кадр для рекламы: без студийного фона, без идеальной позы, без взгляда
  «с обложки».

**Что проверить после генерации:**
- лицо подходит как эталон: форма лица, веснушки, зелёно-карие глаза, брови,
  губы, серьга в левом ухе, светлый блонд в низком хвосте;
- возраст читается как 26, кожа живая, веснушки лёгкие, а не декоративные;
- камера читается как фотоаппарат, руки естественные, ремень не «врос» в плечо;
- взгляд уверенный и спокойный, без кокетства и без пустой приветливой улыбки;
- фон — крыша и золотой час, размыт, без текста и чужих людей;
- кадр годится как главное фото анкеты: лицо крупно, макушка и плечи не обрезаны;
- наряд и цвет свои: зелёная рубашка, а не чёрная кожа и не нейтральный клон.

### 2. Мотоцикл — `profile_2.jpg`

**Назначение:** вторая сторона анкеты — скорость и свобода. Она ездит сама, а не
сидит пассажиркой. Кадр должен читаться как «выходные», а не как реклама мотоцикла.

```
Using the attached portrait as the reference, keep the exact same woman and change
only the scene, the pose, the clothing and her expression. Do not redraw her face:
keep the same facial features as the reference.

The same woman as in the attached reference image: 26 years old, an oval face with high
cheekbones and a soft but defined jawline, light warm skin with a light scatter of fine
freckles across the nose bridge and upper cheeks, green-hazel almond-shaped eyes, soft
blonde eyebrows one or two shades darker than her hair, a small straight nose, natural
full lips, a single small silver hoop earring in her left ear, light warm honey-blonde
hair in a loose low ponytail, almost no makeup, real skin texture.

She stands next to a classic black motorcycle on a quiet country road at sunset, a
helmet held in one hand at her hip. She wears a fitted petrol-blue (deep blue-green)
leather biker jacket over a plain black t-shirt, faded black jeans and worn brown
leather boots. Slight three-quarter turn of the body, head facing the viewer.

Expression: a small confident half-smile, eyes bright and direct. She looks like she
has just stopped for a moment and is enjoying the evening. Not shouting, not posing
like a biker poster, not a sexualized pose.

Setting: a narrow asphalt road between empty golden fields at sunset, a blurred line of
trees and a low sun behind her, warm haze, long soft shadows. The motorcycle is a real
classic road bike, softly out of focus behind her shoulder. No readable license plate,
no signs, no text, no other vehicles or people. Warm side light on her face, natural
shadows.

Photorealistic photograph, natural skin texture, no beauty retouching, 50mm lens at eye
level, shallow depth of field, muted warm color grading, candid editorial feel. 1:1
square, 1024×1024. No text, no watermark, no logo, no other people in focus.
```

**Негативные ограничения:**
- не менять лицо; в динамике и с новым светом модель чаще всего «перерисовывает»
  черты — сверять с `profile_1.jpg`;
- не менять хвост и блонд: волосы остаются светлыми, ветер может растрёпать пряди,
  но не перекрасить их в русый или тёмный;
- не сексуализировать: никакой позы «лёжа на баке», никакого ракурса снизу на бёдра,
  никакой расстёгнутой куртки, никакого «горящего» взгляда в камеру; она ездит,
  а не соблазняет;
- мотоцикл должен быть настоящим байком: колёса, бак, руль, выхлоп читаются;
  без надписей, наклеек и номеров;
- шлем в руке, а не на голове и не на земле; рука держит его правдоподобно;
- никакого текста на одежде, номерах, вывесках и в фоне;
- не рекламный кадр: без идеального заката «как в кино» и без студийного света;
- не копировать одежду и фон референса: зелёная рубашка и крыша остаются только
  в `profile_1.jpg`.

**Что проверить после генерации:**
- лицо совпадает с `profile_1.jpg`: глаза, брови, губы, веснушки, серьга в левом ухе;
- хвост и цвет волос не «поплыли»;
- кадр читается как «она и мотоцикл», а не как «девушка-модель с байком»;
- поза без пошлости: акцент на лице и свободе, не на теле;
- мотоцикл без надписей и номеров, не обрезан так, что непонятен;
- руки и пальцы целые, шлем не сливается с рукой;
- свет тёплый, лицо читаемо, фон не перетягивает;
- наряд петроль-синий и не повторяет другие кадры.

### 3. Путешествие — `profile_3.jpg`

**Назначение:** третья сторона — поездки без расписания. Кадр-настроение, а не
достопримечательность: где-то высоко, ветер, рюкзак, ей хорошо.

```
Using the attached portrait as the reference, keep the exact same woman and change
only the scene, the pose, the clothing and her expression. Do not redraw her face:
keep the same facial features as the reference.

The same woman as in the attached reference image: 26 years old, an oval face with high
cheekbones and a soft but defined jawline, light warm skin with a light scatter of fine
freckles across the nose bridge and upper cheeks, green-hazel almond-shaped eyes, soft
blonde eyebrows one or two shades darker than her hair, a small straight nose, natural
full lips, a single small silver hoop earring in her left ear, light warm honey-blonde
hair in a loose low ponytail, almost no makeup, real skin texture.

She stands at a mountain viewpoint on a clear morning, a worn canvas backpack on one
shoulder. She wears a mustard-yellow light field jacket over a plain white t-shirt, khaki
trekking trousers and worn hiking boots. She is caught mid-turn: her head is turned
back toward the camera, the wind pulls loose strands of hair across her face. Waist-up
framing, slightly off-centre, she is clearly the main subject.

Expression: an open, alive half-smile, eyes narrowed slightly against the light, calm
and pleased. She looks like someone who woke up early for this on purpose. Not a
tourist selfie grin, not a magazine pose.

Setting: a high mountain road with a stone guardrail, a deep valley and layered
blue-green ridges behind her, morning mist in the distance, pale sky, the sun low and
soft on the left. The background is out of focus: no signs, no buildings, no other
tourists, no readable text. Wind in her hair and jacket.

Photorealistic photograph, natural skin texture, no beauty retouching, 50mm lens at eye
level, shallow depth of field, soft natural light, muted cool-warm color grading, candid
editorial feel. 1:1 square, 1024×1024. No text, no watermark, no logo, no other people
in focus.
```

**Негативные ограничения:**
- не менять лицо; на ветру и в новом свете черты «плывут» чаще всего;
- не менять причёску на распущенные волосы: хвост остаётся, ветер только выбивает
  пряди; светлый блонд не меняется;
- не туристический постер: без гигантского заката, без «руки в кадре», без
  постановочного прыжка и без панорамы, где человека почти нет;
- никакого текста: указатели, таблички, карты, логотипы, водяные знаки;
- никаких других людей, машин, палаток и животных в фокусе;
- рюкзак и куртка — обычные, без брендов и надписей; одежда по погоде, не
  сексуализированная;
- не фотореализм → только фотореализм: без рисованных гор и «открыточного» HDR;
- не копировать одежду и фон референса: зелёная рубашка и крыша остаются только
  в `profile_1.jpg`.

**Что проверить после генерации:**
- лицо совпадает с `profile_1.jpg`; веснушки и серьга на месте;
- кадр читается как поездка и характер, а не как «стоит на фоне гор»;
- волосы растрёпаны ветром, но хвост и светлый блонд читаются;
- рюкзак, куртка и хаки-брюки без брендов и текста;
- фон размыт, без людей и указателей; горы не выглядят пластиковыми;
- лицо читаемо, свет не «съел» глаза;
- кроп: лицо и рюкзак в кадре, ничего важного не обрезано;
- горчичная куртка читается и не повторяет другие кадры.

### 4. Ресторан — `profile_4.jpg`

**Назначение:** четвёртая сторона — вкус и вечер. «Чего ищет»: не спонсора и не
скучный вечер, а человека, с которым хорошо сидеть за столом и ехать рядом; тянуть
за собой никого не собирается. Улыбка живая, без загадочности и без алкогольного
тумана.

```
Using the attached portrait as the reference, keep the exact same woman and change
only the scene, the pose, the clothing and her expression. Do not redraw her face:
keep the same facial features as the reference.

The same woman as in the attached reference image: 26 years old, an oval face with high
cheekbones and a soft but defined jawline, light warm skin with a light scatter of fine
freckles across the nose bridge and upper cheeks, green-hazel almond-shaped eyes, soft
blonde eyebrows one or two shades darker than her hair, a small straight nose, natural
full lips, a single small silver hoop earring in her left ear, light warm honey-blonde
hair in a loose low ponytail, almost no makeup, real skin texture.

She sits at a table in a small restaurant in the evening, leaning slightly forward,
both forearms on the table, a glass of red wine by her right hand. She wears a deep
wine-red silk slip dress with a soft cream knit cardigan over the shoulders — elegant,
not revealing. Slight three-quarter turn, head facing the viewer. Waist-up framing.

Expression: a relaxed, warm half-smile with the lips together, eyes directly on the
viewer, one eyebrow slightly raised as if she has just said something ironic. Alive,
present, not drunk, not seductive on purpose.

Setting: a small warm restaurant in the evening — dark wooden table, a blurred candle
and a small vase with a single stem, warm pendant lights behind her, dark wood panelling
softly out of focus. A blurred menu or wine list on the table with no readable text.
No other people in focus, no readable signs, no brand labels.

Photorealistic photograph, natural skin texture, no beauty retouching, 50mm lens at eye
level, shallow depth of field, warm low evening light, muted warm color grading, candid
editorial feel. 1:1 square, 1024×1024. No text, no watermark, no logo.
```

**Негативные ограничения:**
- не менять лицо; вечерний свет и улыбка чаще всего «перерисовывают» черты;
- не менять причёску и серьгу; макияж остаётся минимальным, без яркой помады и
  стрелок;
- не соблазняющий кадр: без глубокого выреза, без ракурса сверху на грудь, без
  «взгляда из-под ресниц», без языка и подмигивания;
- без алкогольной эстетики: один бокал вина, не бутылка, не несколько бокалов,
  не пьяная улыбка;
- никакого текста: меню, винная карта, этикетки, вывески, логотипы, водяные знаки;
- никаких других людей в фокусе, никаких отражений с лицами;
- не глянцевый ресторанный кадр для журнала: без студийного света, без идеальной
  сервировки;
- платье и кардиган без брендов и надписей;
- не копировать одежду и фон референса: зелёная рубашка и крыша остаются только
  в `profile_1.jpg`.

**Что проверить после генерации:**
- лицо совпадает с `profile_1.jpg`; глаза, брови, губы, веснушки, серьга на месте;
- улыбка живая и тёплая, а не загадочная и не пьяная;
- кадр читается как вечер, а не как реклама вина;
- бокал один, вино тёмное, без бутылок и логотипов;
- меню и карта на столе без читаемых букв;
- одежда элегантная, но без пошлости; ракурс на уровне глаз;
- фон тёплый и размытый, лицо главное;
- бордо читается, наряд не повторяет остальные кадры.

## Настройки и запреты

- Соотношение сторон: **1:1**, размер 1024×1024.
- Один стиль на все четыре кадра: фотореализм, естественная кожа, мягкий свет,
  приглушённая тёплая палитра, ощущение живого кадра. Никакого аниме, вебтуна,
  3D, живописи и «пластикового» глянца.
- Идентичность (лицо, веснушки, глаза, светлый блонд и хвост, серьга, возраст,
  «почти без макияжа») не меняется; меняются сцена, поза, одежда и выражение.
- Одежда в каждом кадре своя и своего цвета: зелёный → петроль-синий → горчичный →
  бордо. Четыре одинаковых наряда или цвета = четыре одинаковых фото.
- Ева — не модель и не «девушка с обложки»: расслабленная уверенность, ирония,
  живое лицо; не кокетство и не постановочная улыбка.
- Запрещено: читаемый текст, вывески, меню, номера, логотипы, бренды, водяные
  знаки; люди в фокусе; вульгарность, эротика, акцент на теле; второй экземпляр
  Евы в отражении; смена цвета волос (блонд не становится русым или тёмным) и глаз.
- Никакого алкоголя сверх одного бокала и никаких сигарет.
- Рамку анкеты, точки, сердечки и кнопки модель не рисует — это делает бот.

## Если лицо «плывёт»

- Прикрепите `profile_1.jpg` ещё раз и добавьте: `Do not redraw the face. Keep the
  exact same facial features as the reference; only the scene, the pose, the clothing
  and the expression may change.`
- Если после смены сцены уехало лицо, сократите описание сцены до одной-двух фраз:
  длинные описания модель понимает как разрешение переписать человека.
- Сгенерируйте 3–4 варианта и выберите тот, где совпадают форма глаз, линия бровей,
  губы, веснушки и серьга в левом ухе.
- Если поплыли веснушки, блонд стал русым или уехал хвост — вернитесь к
  `profile_1.jpg`: это якоря, по которым видно, что кадр остался тем же человеком.
- Если модель тащит одежду или фон из референса, добавьте: `Keep the face and hair
  from the reference; take the outfit and the background from the prompt, do not copy
  them from the reference image.`

## Имена файлов и связка с ботом

```
scenarios/eva_message/images/profile_1.jpg
scenarios/eva_message/images/profile_2.jpg
scenarios/eva_message/images/profile_3.jpg
scenarios/eva_message/images/profile_4.jpg
```

Анкета Евы — четыре кадра; кадров эмоций у неё нет: в переписке лицо не показывается.
Бот отправляет карточки до начала переписки, подписи к кадрам берёт из
`scenario.json` → `profile.captions`.

Префикс `profile_*` намеренный: имена кадров анкеты не должны совпадать с именами
эмоций (`calm`, `guarded`, …), иначе `bot/faces.py` примет их за кадры диалога. Пока
кадров нет, бот присылает текстовую карточку — сцена не ломается.

Подписи, под которые снимаются кадры:

| файл | подпись в анкете |
|---|---|
| `profile_1.jpg` | Снимаю людей — это моя работа и мой способ смотреть |
| `profile_2.jpg` | Выходные: мотоцикл и трасса без плана |
| `profile_3.jpg` | Поездки, где нет расписания |
| `profile_4.jpg` | Ищу того, кто поедет рядом, а не того, кого надо тянуть за собой |
