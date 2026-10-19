# Фотографии Веры

Пока пусто: кадры ещё не сгенерированы. Бот это переживает — если файла на нужную
эмоцию нет, он присылает только текст.

Как заполнить:

1. Откройте [prompts/vera-nano-banana.md](../../../prompts/vera-nano-banana.md).
2. Сгенерируйте эталон, потом десять эмоций от него (не наоборот).
3. Положите файлы сюда, имена — по эмоции, без префикса:

```
calm.jpg        guarded.jpg     closed.jpg     irritated.jpg
hurt.jpg        warming.jpg     smiling.jpg    laughing.jpg
tired.jpg       tears.jpg
```

Сценарий сам найдёт эту папку: `bot/scenario.py` считает, что рядом с `scenario.json`
лежит `images/`, и `bot/faces.py` берёт картинку оттуда. Для сценария про вечер
выпускников пока используются фотографии Ани — они лежат в его собственной папке
`scenarios/reunion_call/images/`.
