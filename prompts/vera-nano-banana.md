# Промпты для Nano Banana: серия эмоций Веры

Модель: **Gemini 2.5 Flash Image** (в обиходе «Nano Banana»).
Задача: один и тот же персонаж в десяти эмоциях, аниме/вебтун, квадрат 1:1.
Вера — героиня сценария `first_date` («Первое свидание»): 30 лет, редактор, пришла
на свидание настороженной. Её лицо должно читаться как «слышит фальшь и решает,
верить ли», а не как «ей плохо».

Фон — летнее кафе: солнце, дерево, кофе. Он заморожен так же жёстко, как лицо,
иначе десять кадров будут из десяти разных заведений.

## Чем Вера отличается от Ани (важно для набора)

Стиль и линия — те же, что у Ани, иначе набор рассыпается. Отличается человек,
а фон отличается намеренно: Аня дома вечером, Вера — в кафе днём, летом.

| | Аня | Вера |
|---|---|---|
| возраст | 33 | 30 |
| лицо | овальное, мягкая линия подбородка | круглее, скулы заметнее |
| глаза | карие с янтарным ободком | серо-зелёные, чуть прищуренные |
| волосы | каштановые до плеч, косая чёлка | медные, каре до подбородка, прядь за ухом |
| одежда | кремовый свободный свитер | оливковая льняная рубашка с открытым воротом |
| примета | — | маленькая родинка на левой скуле |
| фон | тёплый однотонный `#EFE7E3` | летнее кафе, окно, кофе |

Линия, заливка, палитра и разрешение — общие: наборы должны смотреться из одной
книги, даже если сцены разные.

## Как работать (порядок важен)

1. **Сгенерируйте эталон** — шаг 1. Это единственный раз, когда лицо создаётся с нуля.
2. **Выберите лучший вариант** из 3–4 попыток. Дальше он — референс для всех остальных.
3. **Меняйте только эмоцию** — шаг 2 + нужный промпт из шага 3, всегда прикрепляя эталон
   как изображение-референс. Не перегенерируйте лицо заново, иначе оно «поплывёт».
4. На каждую эмоцию генерируйте 2–4 варианта: мимика — лотерея даже у хорошей модели.
5. **Не смешивайте с серией Ани.** Не прикрепляйте её кадры как референс: модель
   подтянет каштановые волосы и свитер.

## Шаг 1. Эталонный портрет

```
Flat anime / webtoon illustration, head-and-shoulders portrait of a 30-year-old woman.
Rounder face than average, soft full cheeks, noticeable cheekbones, warm light skin,
a small dark mole on her left cheekbone. Grey-green eyes, slightly narrow and observant,
thin straight eyebrows a shade darker than her hair, small straight nose, natural rose lips
with a fuller lower lip, almost no makeup.
Copper-auburn hair in a chin-length bob with a blunt edge, the right side tucked behind
her ear, a few strands falling forward across the temple.
She wears an olive-green linen shirt with an open collar, sleeves rolled to the elbow.
Gentle cel shading, clean thin line art, muted warm palette, no harsh highlights.

Setting — a small café on a bright summer day, seen from her side of the table. Behind
her shoulder a tall window with sheer white linen curtains, summer sunlight pouring in,
blurred green trees and warm stone houses outside. A wooden chair back and a strip of
pale wall with sun patches. In the lower foreground, slightly out of focus, a white
ceramic cappuccino cup on a saucer and a small glass of water on a light wooden table.
Soft warm bokeh, background muted in cream, honey and sage, clearly lower in contrast
than her face. Early-afternoon sun from the window on the left gives a soft rim light
on her hair, while a broad soft fill keeps her face evenly lit and readable.
No people in the background, no readable text or signage.

Expression: calm and level, with the faintest hint of irony — one eyebrow raised by
a couple of millimetres, mouth closed, a small smile that lives in the eyes more than
on the lips. Gaze directly at the viewer.
Centered composition at eye level, 1:1 square framing, high detail on the face.
No text, no watermark, no logo, no jewelry, no glasses.
```

## Шаг 2. Шаблон для эмоций

Прикрепите эталон и напишите:

```
Using the attached portrait as the reference, change ONLY her facial expression to:
{описание эмоции}

Keep her identity exactly the same: same rounder face shape, same grey-green eye color
and eye shape, same thin straight eyebrows, same nose, same fuller lower lip, same small
mole on the left cheekbone, same copper-auburn chin-length bob with the right side tucked
behind the ear, same olive-green linen shirt, same head angle, same lighting, same art
style and line weight.

And keep the background exactly as in the reference: same tall window with sheer white
curtains, same blurred green trees and sunlit stone houses outside, same wooden chair
back, same pale wall with sun patches, same light wooden table edge, same white cappuccino
cup on a saucer in the lower foreground, same soft bokeh and warm cream-honey palette.
Do not redraw the scene and do not add anything to it.

Do not beautify, do not change her age, do not change makeup, do not change the pose.
Square 1:1. No people in the background, no readable text or signage, no watermark.
```

## Фон: кафе, лето, солнце

Фон — такой же элемент идентичности, как родинка: он должен совпадать во всех десяти
кадрах до мелочей. Поэтому в эталоне он описан построчно, а в шаблоне перечислен
списком, который нельзя менять.

Что в кадре и остаётся на месте:

- **Окно** — высокое, за её плечом, с белыми льняными занавесками, летнее солнце
  бьёт внутрь.
- **Улица за окном** — размытая зелень деревьев и тёплый камень домов, не серый
  зимний город и не вечер.
- **Стол** — светлое дерево, нижний край кадра, чуть не в фокусе.
- **Кофе** — белая керамическая чашка с блюдцем и стакан воды, слева внизу, мягко
  размыты. Это якорь: если посуда поменяла форму или переехала — кадр переснимать.
- **Свет** — летний день, около часа: солнце с окна слева даёт тёплый контровой блик
  на волосах, а мягкая заливка спереди держит лицо читаемым. Иначе получится силуэт.

Чего быть не должно:

- людей, официантов, соседей по столику — фон не должен отбирать внимание у лица;
- читаемого текста: меню, вывесок, надписей на чашке (модель рисует из них кашу);
- резкости на фоне: глубина резкости малая, контраст фона ниже, чем у лица;
- других времён года и суток: только лето, только день.

## Шаг 3. Десять эмоций

### 1. Спокойно — `calm`
Базовое состояние. Она ещё не решила, интересно ли ей.
```
a calm, level expression with a faint thread of irony: eyebrows relaxed, one raised
a couple of millimetres, eyelids open at a normal width but slightly observant, mouth
closed with a small closed-lip smile, gaze directly at the viewer.
```

### 2. Настороженная — `guarded`
Главная эмоция сценария: он сказал что-то, и она взвешивает.
```
guarded and watchful, weighing him: head tilted two or three degrees, one eyebrow clearly
raised, eyes slightly narrowed and fixed on the viewer, lips closed and pressed at one
corner, jaw set. Not hostile — appraising.
```

### 3. Закрылась — `closed`
Он давит или оценивает; она перестаёт вкладываться в разговор.
```
closed off: eyes turned away to the side, eyelids lowered, lips a flat line, face still
and unrevealing, the look of a door closing mid-sentence. Shoulders slightly turned away.
```

### 4. Раздражена — `irritated`
На штамп, на «расслабься», на грубую шутку.
```
irritated, the wince of someone who edits for a living: eyebrows drawn down and slightly
together, a small vertical line between them, eyes narrowed, lips pressed thin, one nostril
flared a little, chin lifted slightly.
```

### 5. Обижена — `hurt`
Её задели, но она не опускает голову.
```
hurt and offended, holding herself upright: inner ends of the eyebrows raised, eyes wide
and glossy with unshed tears, mouth small and turned down, chin lifted slightly rather
than lowered. Restrained, not pitiful.
```

### 6. Теплеет — `warming`
Он не стал давить и попал в настоящую тему.
```
softening: the tension leaves her jaw, eyebrows relax, eyelids lowered a little in a warm
look, a small genuine smile appears with lips together, faint blush on the cheeks,
gaze at the viewer.
```

### 7. Улыбается — `smiling`
Он вспомнил про караоке — и это оказалось не приёмом.
```
a genuine warm smile: eyes curved with happiness, cheeks raised, lips parted in a natural
smile showing a hint of teeth, eyebrows relaxed. The irony is gone.
```

### 8. Смеётся — `laughing`
Стало легко; шутка попала в неё, а не в тему.
```
laughing openly: eyes closed in happy crescents, head tipped back slightly, mouth open
in a real laugh, cheeks raised, faint blush.
```

### 9. Устала — `tired`
Конец недели; она пришла на свидание через силу.
```
tired and drained: upper eyelids lowered about halfway, gaze slightly unfocused, eyebrows
flat with the inner ends a little raised, mouth slightly open as if exhaling, faint
shadows under the eyes.
```

### 10. Слёзы — `tears`
Редко и поздно: если она всё-таки рассказала о прошлом свидании.
```
crying quietly, not hiding it: eyes wet and shining, one tear on her cheek, inner eyebrows
raised, lips pressed and slightly parted, chin steady. Restrained — no sobbing,
no exaggerated drama.
```

## Настройки и запреты

- Соотношение сторон: **1:1**, размер 1024×1024.
- Фон всегда один и тот же — летнее кафе по описанию выше: окно, занавески, зелень
  за стеклом, деревянный стол, белая чашка кофе, мягкое боке.
- Свет всегда с окна слева: тёплый блик на волосах, лицо ровно освещено.
- Стиль — плоская аниме-графика с мягкой заливкой, без фотореализма.
- Запрещено: люди и официанты на фоне, меню и вывески с текстом, подписи, водяные
  знаки, логотипы, украшения, очки, другая одежда, другая причёска, смена возраста
  и цвета глаз, другое время суток и другое время года.
- Оливковая рубашка — часть личности: если модель меняет её на свитер, она тянет
  к Ане, и кадр надо перегенерировать.
- Фон — тоже часть личности: если кафе стало другим заведением, это не «мелкая
  разница», а причины переснять кадр.

## Если лицо или фон «плывут»

- Прикрепите эталон ещё раз и добавьте: `Do not redraw the face. Keep the exact same
  facial features as the reference; only the expression may change.`
- Если поехал фон, добавьте отдельно: `Keep the background identical to the reference:
  same window, same curtains, same table, same cup, same bokeh. Change only the
  expression.`
- Уменьшите формулировку эмоции до одной фразы — длинные описания модель часто
  трактует как разрешение менять внешность.
- Сгенерируйте 4 варианта и выберите тот, где совпадают форма глаз, линия бровей,
  родинка на левой скуле и белая чашка на столе.
- Если поплыла родинка или чашка — вернитесь к эталону: это якоря, по которым видно,
  что кадр остался тем же.

## Имена файлов и связка с ботом

Файлы кладутся в папку сценария — `scenarios/first_date/images/`:

```
scenarios/first_date/images/calm.jpg
scenarios/first_date/images/guarded.jpg
scenarios/first_date/images/closed.jpg
scenarios/first_date/images/irritated.jpg
scenarios/first_date/images/hurt.jpg
scenarios/first_date/images/warming.jpg
scenarios/first_date/images/smiling.jpg
scenarios/first_date/images/laughing.jpg
scenarios/first_date/images/tired.jpg
scenarios/first_date/images/tears.jpg
```

Префиксы не нужны: папка сама по себе означает персонажа. Сценарий — это папка
`scenarios/<id>/` с `scenario.json` и `images/` внутри, поэтому Вера не может
показать лицо Ани, даже если оба набора лежат в одном репозитории.
`bot/faces.py` берёт картинку из `scenario.faces_dir`. Если какого-то кадра ещё нет,
бот молча пришлёт только текст — сцены это не ломает.

Приоритет для `first_date`: `guarded`, `closed`, `irritated`, `warming`, `smiling`,
`laughing`. `calm`, `tired` и `tears` нужны реже, но пусть будут: состояние зависит
от хода игрока, а не от сценария.
