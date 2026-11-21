# PUMP_FADE — ограниченное сравнение 5m-входов и выходов

Результат: выбранный на TRAIN вариант не прошёл TEST. Новая установка/торговля не запускалась.

- [Отчёт и ограничения](REPORT_RU.md).
- [Заполнения и пропуски](ENTRY_COUNTS_RU.md).
- [Все 16 конфигураций](ALL_VARIANTS_RU.md), [режимы](REGIMES_RU.md), [все 640 строк](METRICS.csv).
- [Протокол](FROZEN_PROTOCOL.json), [источники](CORE_INPUTS.json), [контрольная точка](CHECKPOINT.json).
- [Независимая проверка Claude/ChatGPT](HANDOFF_FOR_CLAUDE_RU.md).
- TRAIN_ALL_ROWS.jsonl.gz / TEST_ALL_ROWS.jsonl.gz — все сделки/неисполнения, пути выходов и funding proxy.

## Воспроизведение

Для независимой проверки сначала используйте сохранённые таблицы и журналы. Эти расчёты уже завершены; повторный запуск без найденной причины не нужен. Требуются Python3.12, NumPy (выполнено с2.3.5), gh с доступом к приватному Crypto-Auto-Radar. Локальные каталоги ниже — только изолированный исследовательский scratch или GitHub Actions runner, не торговый ноутбук. Скрипт скачивает исключительно существующие GitHub blobs, не обращается к бирже и пропускает проверенные файлы.

```bash
python fetch_inputs.py --out scratch/data
python prepare.py --data scratch/data --out scratch/prepared
python -m unittest -v test_engine
```

`fetch_inputs.py` и `prepare.py` не считают PnL. Для нового независимого аудита, только если повтор действительно нужен, в НОВОМ каталоге результатов:

```bash
CODE_COMMIT=83c13931033c83ea916f5a6624427bc86c3e0839 python run.py --prepared scratch/prepared --out scratch/audit_results --stage train_entries
```

Сверить TRAIN_ENTRY_SELECTION.json с зафиксированным d733cc25807c18697822be3ccd7bb60a1676e1db; только затем train_exits, сверить FINAL_TRAIN_SELECTION.json с4dd3040534d4ff74548a97b9bcb1a167399177e3; только затем test. При наличии COMPLETE этап отказывается запускаться повторно. Не менять selection или правила после TEST. Полный повтор не был сделан при публикации: выполнялись только проверки сохранённых результатов.

SHA256 каждого публикуемого файла — MANIFEST.json; сам MANIFEST не включает свой хеш. Последний commit SHA содержит Draft PR и история GitHub; код, протокол и замороженные выборы имеют отдельные точные SHA в CHECKPOINT.

Не импортируется runtime CAR/Freqtrade и не используются ключи/ордерные API. Касание OHLC предполагает исполнение, но не доказывает очередь/ликвидность. Unit fixtures синтетические только для тестирования алгоритма; в исследовательском PnL использованы реальные исходные свечи.
