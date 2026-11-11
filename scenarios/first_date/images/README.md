# Фотографии Веры

Готово: десять кадров, 1024×1024, по одному на каждую эмоцию. Сейчас это прежний
аниме-набор; Вера переводится в фотореализм — актуальные промпты на все её кадры
(эталон, анкета, эмоции, экран звонка) в
[prompts/vera-photoreal-nano-banana.md](../../../prompts/vera-photoreal-nano-banana.md).
Рекомендация для старого набора: `guarded.jpg` стоит переснять — он читается скорее
как «раздражена», чем «взвешивает, верить ли», а это стартовая эмоция сценария.

```
calm.jpg        guarded.jpg     closed.jpg     irritated.jpg
hurt.jpg        warming.jpg     smiling.jpg    laughing.jpg
tired.jpg       tears.jpg
```

Сценарий сам находит эту папку: `bot/scenario.py` считает, что рядом со
`scenario.json` лежит `images/`, и `bot/faces.py` берёт картинку оттуда.

Для сценария про вечер выпускников пока используются фотографии Ани — они лежат
в `scenarios/reunion_call/images/`.
