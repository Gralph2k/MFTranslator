# Фотографии Веры

Готово: десять кадров, 1024×1024, по одному на каждую эмоцию. Стиль, лицо,
одежда и кафе совпадают между кадрами.

```
calm.jpg        guarded.jpg     closed.jpg     irritated.jpg
hurt.jpg        warming.jpg     smiling.jpg    laughing.jpg
tired.jpg       tears.jpg
```

Сценарий сам находит эту папку: `bot/scenario.py` считает, что рядом со
`scenario.json` лежит `images/`, и `bot/faces.py` берёт картинку оттуда.

Если понадобится перегенерировать кадр — промпты и правила в
[prompts/vera-nano-banana.md](../../../prompts/vera-nano-banana.md). Рекомендация:
`guarded.jpg` стоит переснять — сейчас она читается скорее как «раздражена»,
чем «взвешивает, верить ли», а это стартовая эмоция сценария.

Для сценария про вечер выпускников пока используются фотографии Ани — они лежат
в `scenarios/reunion_call/images/`.
