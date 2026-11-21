# PUMP_FADE A/C — проверка перед возможной заменой входа

Статус: **DATA_GAP. Архив Acer не получен. Независимый PnL не рассчитывался. Forward-сбор не запущен.**

- [Отчёт: факты, непроверенные цифры, ограничения](REPORT_RU.md).
- [Точная выгрузка через приватный GitHub](DATA_NEEDED.md).
- [Замороженный протокол](FROZEN_PROTOCOL.json), [регистрация](REGISTRATION.json), [контрольная точка](CHECKPOINT.json).
- [Результаты с явным происхождением цифр](RESULTS.json).
- [Инструкция независимому проверяющему](HANDOFF_FOR_REVIEW_RU.md).

Только новая исследовательская папка. Нет задач Actions/Windows, служб, торговли, изменений runtime или новых рыночных загрузок. Python-файлы не имеют executable-bit, запускаются исключительно явно в исследовательской копии/GitHub-hosted runner после появления разрешённых данных. Не устанавливать на LIVE.

## Проверка кода

Python3.12, только стандартная библиотека, без установки зависимостей:

```bash
python -m unittest -v test_replay test_ingest
```

38 тестов используют синтетические unit-fixtures; они не дают статистики торговли. UNIT_TEST_RESULTS.txt сохраняет фактический результат запуска. ISOLATION_AUDIT.json — статический список импортов; это свидетельство отсутствия сетевого/ордерного пути в опубликованных скриптах, а не изменение сетевых разрешений машины.

## После получения архива

Сначала сверить GitHub commit/path/SHA256 оригинальных файлов, исходный симулятор, ML-snapshot и схему; результаты A/B/C остаются историческими EXPOSED. Не изменять геометрию для совпадения цифр: расхождения сохранять как результаты аудита.

`replay.py` принимает один разрешённый JSON-bundle (контракт ниже), вывод только в новый несуществующий каталог:

```bash
python replay.py --input /isolated/github-export/bundle.json --out /isolated/research-output/new-historical-audit --mode historical
```

Это пример команды, она НЕ выполнялась на архиве: его нет. Код выводит CLOSED_PRICE_MODEL/price_R, никогда actual-fill или true-net. Первоначальные сигналы/цены/журналы не нужно публиковать в открытый репозиторий. В отчёте сохранять проверенные безопасные производные и ссылки на приватные источники.

Forward-mode сейчас намеренно блокируется: REGISTRATION.model_snapshot_verified=false. После независимого ревью и получения исходной модели отдельным коммитом зафиксировать hash и фактическую новую границу старта, без её переноса назад. Каждый signal_ms/first_received должен быть позже нового старта. Не достаточно просто переключить флаг: проверяющий должен подтвердить происхождение snapshot и неизменность top50.

## Ручной импорт нового исследовательского batch

`ingest.py` не читает Telegram/биржу/базу/живой каталог. Он только превращает уже выгруженный через GitHub JSONL в новый журнал. Идентичные дубликаты внутри batch схлопываются; конфликтующие отвергаются. Между пакетами дедупликация делается по глобальному id при сборке итоговогоbundle; неоднозначные конфликты не теряются. Хеш-цепочка ловит редактирование после импорта, но не доказывает честность первого_received или полноту сигнального потока. Нужны исходный append-only журнал и сверка GitHub timestamp.

```bash
python ingest.py --input /isolated/github-export/signals.jsonl --out /isolated/research-output/batch001.jsonl --source-repo OWNER/PRIVATE_REPO --source-commit EXACT_40_HEX_SHA --source-path path/to/signals.jsonl
```

Команда не выполнялась, потому нет нового batch. Постоянное наблюдение не создано. Перед расчётом объединять только непротиворечивые пакеты и проверять coverage-heartbeat; пропущенные пакеты не считать отсутствием сигналов.

## Контракт bundle

Обязательные верхние поля: `provenance` (repo/commit/path/SHA256 исходников, биржа Bybit linear USDT perpetual, minute timestamp convention UTC-open, версия модели/симулятора), `signals` (список), `candles` (symbol → список минутных объектов); необязательное `observations`. Декларация provenance сама по себе не проверяет внешние файлы: это работа независимого аудитора. Локальный SHA256bundle фиксируется в результате.

Каждый signal: `id`, `symbol`, `signal_ms`, `first_received_ms`, `reference_price`, `ml_passed` boolean, `filter_keep="top50"`, `model_sha`. Исходный planned entry/SL/TP/created/expires/сеть хранить дополнительно в исходной выгрузке для сверки: модельный replay не подменяет ею полный FT.

Candle: `ts` целыеUTC-ms начала минуты, `open/high/low/close` положительные конечные числа. Неинтерполированные непрерывные реальные минуты; дубликаты/невалидный OHLC отвергаются, gap/pending отделяются. Volume/ликвидность/очередь не подтверждаются этим OHLC-модулем.

Observation: `signal_id`, `variant`, `decision_ms`, `asof_ms`, `flags` с tri-state True/False/null для `source_enabled`, `egress_safe`, `slots_available`, `risk_allowed`, `min_order_ok`, `symbol_available`, `network_ok`. Нет/будущее/старше1min → UNKNOWN. Pass вA не означает pass вC: сначала нужна отдельная причинная модель портфеля. Эти снимки не меняют price-only replay и не считаются исполнением.

Для режима BTC в signal нужны `btc_close_known`, `btc_close_24h_known`, `btc_close_known_ms`, `btc_close_24h_known_ms`: первая уже закрыта на signal_ms, вторая ровно24hраньше. Нет валидных timestamps → UNKNOWN.

Истинный net, funding cash, допустимые counterfactual-входы и недельная bootstrap-статистика в текущем коде НЕ вычисляются. Это явно отмечено в отчёте, чтобы не принять ценовую модель за независимый результат.
