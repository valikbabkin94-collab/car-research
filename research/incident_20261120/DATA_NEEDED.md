# Что требуется из отсутствующих runtime-данных — только выгрузка в приватный GitHub

Никаких подключений к ноутбукам агентом. Публиковать обезличенный пакет в **приватный Crypto-Auto-Radar**, например отдельную data/incident-20261120; затем достаточно GitHub-ссылки. Не присылать API-ключи, .env, Telegram-сессии, токены, приватные заголовки/подписи запросов или полный exchange-config. В публичный car-research — только числовые обезличенные результаты.

## Общий интервал/время
Нужны timezone экрана владельца и исходные Telegram date/edit/firstObserved/received/decision/fill в UTC. Пока timezone неизвестна, пакет с буфером **2026-11-19T21:00:00Z–2026-11-21T03:00:00Z** покрывает MSK/UTC и позиции, перенесённые через границу. Если экспорт сделан до конца интервала — указать asof_utc, отсутствующий хвост не заполнять. Сигнал HYPE искать по source=YODA, symbol=HYPEUSDT и всем возможным sid, а не только по одной догаданнойUTC-минуте.

## Для пункта1 — подтвердить установленный код/пути/allowlist без изменения runtime
1. SHA256 четырёх реально установленных файлов относительно fastpath: `tools/car_egress_entry_guard.py`, `tools/car_ip_watchdog.py`, `freqtrade/strategies/egress_recovery.py`, `freqtrade/strategies/CarFastPathV1.py`. Если SHA не совпадает с опубликованным — приватная read-only копия этих файлов, без .env и конфигов с ключами.
2. Action Execute/Arguments/WorkingDirectory задач `CAR_Egress_EntryGuard` и IP-watchdog (имя фактической задачи). Нужен точный `--status-file`, `--state`, путь/значения явного `--expected-ip`, аргументы watchdog и частота. Экспорт только этих полей, не все процессы/службы.
3. Текущий владелец-подтверждённый whitelist IP конкретного ключа **без самого ключа/ID/секрета**. Не выводить новый allowlist из однажды увиденного147.45.63.64. Без этого код сравнивает только опубликованную оператором политику, не фактическую настройку аккаунта Bybit.
4. Файл по реальному `--status-file`, соседний `egress_guard_policy.json` и журнал/история результатов проверок за общий интервал. Текущий снимок не заменяет исторические интервалы. Для старого watcher: `freqtrade/user_data/shadow/ip_watchdog.json` и его stdout/stderr/Task History, если есть.
5. Mounts контейнера для проверки соответствия host→read-only strategies. Только read-only запрос `docker inspect --format '{{json .Mounts}}' car-fastpath-freqtrade-1`, не полный inspect с Env.

Пример read-only запроса владельцем/Claude: `Get-ScheduledTask -TaskName CAR_Egress_EntryGuard | Select-Object -ExpandProperty Actions | Select-Object Execute,Arguments,WorkingDirectory`. Ничего не запускать/перезапускать/отключать этой выгрузкой. Перед публикацией удалить секреты, если они оказались в старых args.

## Для пункта2 — настоящая цепочка Yoda/HYPE и бумажное исполнение
1. Первоначальный raw-event Yoda/HYPE20.11 и все его правки/сопровождение: text, publication/edit time, firstObserved/received, event_kind, source; согласованный псевдоним post_id/reply_id/sid для связки. Из опубликованного ingest видно два возможных event input: `/data/three/auth_web_shadow/events.ndjson` и `/data/three/events.ndjson`. Выгрузить только относящиеся кHYPE/этому окну строки с их источником; путь на Windows определить по mount map, не угадывать.
2. Reader health/gaps и ingest parse/ignore/route решения по тем же событиям; конечная сохранённая карточка из `user_data/car_signals/signals.json` (или реального signals_dir) с original sid/source, created/received/not_before/expires, zone, SL, TP, max_targets, status, commands и fingerprints. Если есть снимки до/после — оба.
3. Действовавший на тот момент subset car_fastpath: sources_enabled, allowed_sides, max_targets/tp_split, fee_rate, move_be_after_tp1, entry/chase tolerances, risk_usdt, max_open/max_open_risk, daily limit, source→paper routing и config SHA/время активации. **Не весь config.fastpath.json:** exchange keys/proxy credentials не нужны. Текущий конфиг не доказывает настройку утром20.11.
4. `strategy_state.json` и история `entries_blocked`/`egress_last_recovery`, consumed/invalid поHYPE, daily/manager latches, claim/admission записи; точные `CAR deny ...` или предыдущие строки confirm/candidate/WAIT. Если историю не записывали — прямо указать, не выводить её из текущего файла.
5. Paper-engine ledger для YODA/HYPE: actual entry time/price/quantity, пять исходных/использованные цели и доли, TP fills, BE/SL updates, final/open status, remaining qty, fees/funding и финансовый1R. Если Yoda вообще не маршрутизируется в работающий paper-engine — явно этот факт вместо фиктивного0R.
6. Bybit HYPEUSDT реальные1m свечи от публикации до последнего выхода/asof, raw funding payouts и применимые fees. Касание уровня после закрытия поBE не считать поздним исполнением той же позиции. Если внутри минуты важен порядок — тики/аггрегированные сделки при наличии, иначе неоднозначность отдельно.

## Для пункта3 — все источники и совокупный риск20.11
1. Все сигналы/решения дня (включая REJECTED/WAIT/NOFILL/expired/cancelled), а не только закрытые победители; тот же минимальный schema и source/sid, chronology, cause_code.
2. Открытые позиции и заявки на начало окна + хронология open/partial/SL/BE/close за весь интервал. Поля: source/sid/pair/side, actual fill time/price/quantity/fee, remaining_qty, финансовый исходныйSL/R и текущий protectiveSL во времени. Плечо/аварийный initial_stop не заменяет финансовый риск. Добавить исходы после конца дня для ещё открытых позиций или пометитьright-censored.
3. По OWNER/MANAGER store — read-only экспорт claims/reservations: sid/source/pair/status/risk_usdt/created_at/last_seen/released_at и причины. Отдельно от Trade/open-orders реестра: phantom claim не является открытой рыночной позицией. Секретов в этой выгрузке не нужно.
4. Полные интервалы egress block/unblock с причиной и actual/expected_IP (приватно), журнал принятых и отказанных сигналов для временногоjoin. Количество уведомлений не подменяет число блокировок/потерянных входов.
5. Для DUMP_BOUNCE/PUMP_FADE: реальные BTC и исследуемые пары1m за день, необходимый уже существующим frozen-rule lookback1h, причинный PIT-universe/volume rank на каждый час/решение, листинг/делистинг/доступность, сохранённые features и funding. Если PIT-rank уже сохранён — передать готовую таблицу с источником/временем, не перекачивать годы. Не использовать сегодняшний список top50 и номинальную дешевизну.
6. Все цены с venue/product/timeframe/timezone/period/count/gaps/checksum; все решения с code/config SHA. Спот, Bybit linear и Binance proxy не смешивать молча.

Безопасные диагностические запросы, выполняемые владельцем/Claude и публикуемые **после очистки секретов**:
```
docker logs --timestamps --since 2026-11-19T21:00:00Z --until 2026-11-21T03:00:00Z car-fastpath-freqtrade-1
docker logs --timestamps --since 2026-11-19T21:00:00Z --until 2026-11-21T03:00:00Z car-fastpath-ingest-1
```
Если реальные имена отличаются — указать соответствие, не создавать новые контейнеры. Для paperDB — read-only экспорт positions/events по sourceYODA/HYPE и всех дневных вариантов из фактического `--db`; не делать backup/live-db mutation агентом. Безэтих данных пункты2/3 остановлены; никаких удалённых команд здесь не выполнялось.
