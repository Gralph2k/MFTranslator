# Промпты для Nano Banana: серия эмоций Ани

Модель: **Gemini 2.5 Flash Image** (в обиходе «Nano Banana»).
Задача: один и тот же персонаж в восьми эмоциях, аниме/вебтун, квадрат 1:1.

## Как работать (порядок важен)

1. **Сгенерируйте эталон** — шаг 1. Это единственный раз, когда лицо создаётся с нуля.
2. **Выберите лучший вариант** из 3–4 попыток. Дальше он — референс для всех остальных.
3. **Меняйте только эмоцию** — шаг 2 + нужный промпт из шага 3, всегда прикрепляя эталон
   как изображение-референс. Не перегенерируйте лицо заново, иначе оно «поплывёт».
4. На каждую эмоцию генерируйте 2–4 варианта: мимика — лотерея даже у хорошей модели.

## Шаг 1. Эталонный портрет

```
Flat anime / webtoon illustration, head-and-shoulders portrait of a 33-year-old woman.
Oval face with a soft jawline, warm light skin, hazel-brown eyes with a subtle amber ring,
thin naturally arched eyebrows, small straight nose, natural rose lips, almost no makeup.
Dark chestnut-brown hair, shoulder length, soft side-swept fringe across the forehead,
a few loose strands framing the face. She wears a cream oversized knit sweater.
Plain warm greige background (#EFE7E3). Soft diffused light from the upper left,
gentle cel shading, clean thin line art, muted warm palette, no harsh highlights.
Expression: calm and attentive — relaxed eyebrows, eyes open at a normal width,
lips closed in a neutral line, gaze directly at the viewer.
Centered composition at eye level, 1:1 square framing, high detail on the face.
No text, no watermark, no logo.
```

## Шаг 2. Шаблон для эмоций

Прикрепите эталон и напишите:

```
Using the attached portrait as the reference, change ONLY her facial expression to:
{описание эмоции}

Keep her identity exactly the same: same face shape, same eye color and eye shape,
same eyebrows, same nose and lips, same hairstyle and fringe direction, same cream
sweater, same head angle, same lighting, same warm greige background, same art style
and line weight. Do not beautify, do not change her age, do not change makeup,
do not change the pose. Square 1:1. No text, no watermark.
```

## Шаг 3. Восемь эмоций

### 1. Спокойно — `calm`
Базовое состояние, с него начинается диалог.

```
a calm, attentive expression: eyebrows relaxed at their natural height, eyelids open
at a normal width, mouth closed with a barely visible soft smile, gaze directly at
the viewer.
```

### 2. Устала — `tired`
После тяжёлого дня, когда она говорит «всё нормально».

```
tired and drained: upper eyelids lowered about halfway, gaze slightly unfocused,
eyebrows flat with the inner ends a little raised, mouth slightly open as if exhaling,
head tilted a few degrees to one side, faint shadows under the eyes.
```

### 3. Раздражена — `irritated`
На «успокойся» и непрошеные советы.

```
irritated and tense: eyebrows pulled down and together, eyes narrowed, pupils slightly
smaller, lips pressed into a thin line, jaw tight, faint flush on the cheeks.
```

### 4. Обижена — `hurt`
Её задели, но она ещё держится.

```
hurt and offended: inner ends of the eyebrows raised, eyes wide and glistening with
unshed tears, mouth small and downturned, chin slightly lowered, gaze at the viewer.
```

### 5. Закрылась — `closed`
Партнёр давит или обесценивает; она уходит в себя.

```
closed off and guarded: eyes looking away to the side, eyelids lowered, lips a flat
line, head turned slightly away from the viewer, shoulders a little hunched.
```

### 6. Теплеет — `warming`
Он замолчал и просто посидел рядом; лёд тронулся.

```
softening: eyebrows relaxed, eyelids slightly lowered in a gentle look, faint warm
smile with lips together, soft blush on the cheeks, gaze at the viewer.
```

### 7. Улыбается — `smiling`
Её услышали, стало легче.

```
a genuine warm smile: eyes curved with happiness, cheeks raised, lips parted in a
natural smile showing a hint of teeth, eyebrows relaxed.
```

### 8. Слёзы — `tears`
Она наконец рассказала, и её прорвало.

```
crying quietly: eyes wet and shining, one tear running down her cheek, inner eyebrows
raised, lips trembling slightly and slightly parted, chin lowered, restrained —
no sobbing, no exaggerated drama.
```

## Настройки и запреты

- Соотношение сторон: **1:1**, размер 1024×1024.
- Фон всегда один и тот же — `#EFE7E3`, без предметов и размытия.
- Свет всегда сверху-слева, стиль — плоская аниме-графика с мягкой заливкой.
- Запрещено: текст, подписи, водяные знаки, логотипы, украшения, другая одежда,
  другая причёска, фотореализм, 3D, смена возраста и цвета глаз.

## Если лицо «плывёт»

- Прикрепите эталон ещё раз и добавьте: `Do not redraw the face. Keep the exact same
  facial features as the reference; only the expression may change.`
- Уменьшите формулировку эмоции до одной фразы — длинные описания модель часто
  трактует как разрешение менять внешность.
- Сгенерируйте 4 варианта и выберите тот, где совпадают форма глаз и линия бровей.
- Храните файлы с именами `anya_calm.png`, `anya_tired.png` и так далее.

## Связка с ботом

Когда картинки будут готовы, их можно привязать к состоянию: `calm` при открытости
ниже 0.3, `warming` при росте, `hurt`/`closed` после давления, `tears` при сильном
сближении. Промпты для этого не нужны — нужны только имена файлов.
