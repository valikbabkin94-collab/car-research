# Read-only выгрузка CAR: PF-пропуски, ARB, стопы и рейтинг

Реализован скрипт по текущему заданию и DATA_NEEDED PR #3. Файл `codex_task_export_script.txt` не приложен в этом сообщении и не найден в проверенных источниках; дословное выполнение неизвестного текста не заявляется. При появлении файла сверить его требования с этой реализацией, не запускать повторную выгрузку автоматически.

Скрипт **не запущен на реальной базе**. Пройдены 21 офлайн unit tests на отдельных временных SQLite-файлах/синтетических строках, не искусственная история рынка. Source bytes до/после совпадают, sidecar-файлы БД не создаются; network/SDK/process/service вызовов нет. Настоящие торговые результаты не вычислялись.

## Безопасность и запуск оператором

Python 3.11+ stdlib. Только явно предоставленные существующие offline snapshots. Нет SSH/Desktop, Windows Task Scheduler, API Bybit/Telegram, .env и config с ключами. Код читает SQLite с `mode=ro&immutable=1` и query_only. Непустой WAL/journal запрещён: immutable не должен игнорировать несохранённые данные активной базы. Нужна уже готовая согласованная копия; скрипт не запускает backup/checkpoint работающего бота. Если источник меняется во время чтения, источник BLOCKED и DB-выходы удаляются из нового bundle.

Пример ниже — инструкция, не выполненная команда. Оператор сам указывает уже сохранённые копии. Выход должен быть новым каталогом ВНЕ всех входных каталогов.

```powershell
python car_research_export.py --db C:\CAR_SNAPSHOTS\trades_consistent.sqlite --snapshot-root C:\CAR_SNAPSHOTS\user_data --paper-db C:\CAR_SNAPSHOTS\factory_consistent.sqlite --artifact C:\CAR_SNAPSHOTS\evidence\decision_events.jsonl --artifact C:\CAR_SNAPSHOTS\evidence\manager_events.jsonl --artifact C:\CAR_SNAPSHOTS\prices\coin_btc_1m.csv --code-file C:\CAR_SNAPSHOTS\code\CarFastPathV1.py --out C:\CAR_EXPORT_PRIVATE_20261121
```

`--artifact` повторяется для каждого УЖЕ имеющегося файла: ingest/strategy/report/guard logs, UTC clock offsets, exchange_positions/executions/order_history/open_orders/closed_pnl JSON, начальные protectiveSL события, price1m/quotes, исходные и managed ALT_CLONE ledgers с общей идентичностью. Поддержаны JSON/JSONL/NDJSON/CSV/TXT/LOG и gzip. Это не downloader. Для code-file сохраняется только SHA256. Конфиги с секретами запрещены; безопасный заранее подготовленный `research_config_extract.json` очищается от чувствительных полей.

Данные **PRIVATE_NOT_FOR_PUBLIC_GITHUB**: реальные bundles — только в приватный Crypto-Auto-Radar. Идентификаторы хешируются согласованно внутри одного bundle, тексты/секретные поля удаляются. Raw log lines с признаками секрета целиком скрываются, остальные логи могут содержать приватные торговые ID — наружу не публиковать. Хеши разных запусков не служат ключом соединения между bundles.

## Что именно добавлено для Б и В

Все trades (включая открытые), orders и trade_custom_data: исходные количества/цены, stop/initial_stop, комиссии, даты и агрегированный funding, если они есть в схеме; источник берётся из enter_tag ДО хеширования. realized_profit и close_profit_abs сохраняются отдельно, **никаких fallback**. Финансовый R из аварийного стопа не рассчитывается. Сохраняются все исходные столбцы с редактированием чувствительных полей, поэтому нестандартные stop/risk поля не отбрасываются молча.

Отдельные funding-таблицы выгружаются, только если существуют; отсутствие — MISSING/rows=null, не funding=0. История начального защитного SL, actual fees/cashflows, manager BE/trailing/partials, original/raw ALT_CLONE и тики после стопа не возникают из SQLite автоматически: добавить уже сохранённые файлы через --artifact. Если такие события не логировались, MANIFEST явно оставляет required gap.

Paper DB: positions/opportunities/events/runs/funding/intents/rejections/price_batches/variants, если таблицы есть. signals/state/producer feeds и существующие gzip-ротации копируются из ограниченного списка в snapshot-root, без обхода диска. Неизвестный schema table не угадывается: его имя сохранено, а payload не читается. Отсутствующий нужный иной table надо добавить после проверки схемы.

MANIFEST содержит строки источников, статус EXPORT/BLOCKED/TRUNCATED/MISSING, raw table columns, количество экспортированных строк и SHA256 файлов. Обрезанный/неполный набор не является доказательством всей истории. Никакой PnL, WR/PF, ATR и рейтинг скрипт не вычисляет.

Лимиты по умолчанию 50 MB на файл, 200 000 строк на таблицу/поток. Gzip читается с пределом распаковки. Полные JSON ограничены байтами; крупные market datasets лучше передавать готовыми ограниченными файлами нужного периода. Покрытие и timezone нужно явно описать в source_recipe_manifest.json; даты скрипт не переименовывает в UTC.

## Проверки

```bash
python -m unittest discover -s research/pf_missed_entries_20261121/export_v1/tests -v
```

Скрипт не зарегистрирован в задачах и не развёрнут. Использование выгрузки для последующих расчётов требует сверки MANIFEST, источников/версий и protocol freeze до PnL. Старые исследования не пересчитывать.
