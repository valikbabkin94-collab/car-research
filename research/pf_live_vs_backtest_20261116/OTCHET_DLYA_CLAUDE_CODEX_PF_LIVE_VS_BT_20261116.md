# PF: сверка 13 live-сделок и 18 сигналов без входа

Выгрузка b711017 разобрана. Реально: **13 сделок, 12 прибыльных, сумма 4.6282R**. Годовой replay не повторялся. Все 31 строки: [CSV](RESULTS/CASE31/ALL31.csv), [полные события](RESULTS/CASE31/ALL31.json), [источники и пробелы](RESULTS/CASE31/SOURCES.json).

|Символ|Live R|1m proxy статус|Price R модели|Net R модели|
|---|---:|---|---:|---:|
|CRWVUSDT|NA|CLOSED|0.1760|NA|
|BLUAIUSDT|NA|CLOSED|0.6077|NA|
|KORUUSDT|0.6115|CLOSED|0.6077|NA|
|MVLLUSDT|0.6174|CLOSED|0.6077|NA|
|NBISUSDT|0.6151|CLOSED|0.6077|NA|
|SOXLUSDT|NA|NOFILL|NA|NA|
|MUUUSDT|NA|CLOSED|0.1760|NA|
|SNXXUSDT|0.4028|CLOSED|0.1760|NA|
|ZHONGJIUSDT|NA|CLOSED|0.1760|NA|
|XCNUSDT|NA|CLOSED|-0.0215|NA|
|QUSDT|0.6045|CLOSED|0.6077|NA|
|ERAUSDT|0.5834|CLOSED|0.6077|NA|
|MAGMAUSDT|0.2005|CLOSED|0.1760|NA|
|PLAYSOUTUSDT|NA|DATA_GAP_SIGNAL_REFERENCE|NA|NA|
|AKEUSDT|0.3659|CLOSED|0.3916|NA|
|BARDUSDT|NA|CLOSED|0.1760|NA|
|SOPHUSDT|0.3818|CLOSED|0.1760|NA|
|BMTUSDT|0.1735|CLOSED|0.1760|NA|
|TACUSDT|NA|CLOSED|0.1760|NA|
|EVAAUSDT|NA|CLOSED|0.3916|NA|
|INITUSDT|NA|CLOSED|0.6077|NA|
|JELLYJELLYUSDT|0.6336|DATA_GAP_M1|NA|NA|
|NESAUSDT|NA|DATA_GAP_SIGNAL_REFERENCE|NA|NA|
|SHELLUSDT|NA|CLOSED|0.1760|NA|
|KAVAUSDT|NA|DATA_GAP_M1|NA|NA|
|VVVUSDT|NA|OPEN_RIGHT_CENSORED|NA|NA|
|DRVUSDT|NA|DATA_GAP_SIGNAL_REFERENCE|NA|NA|
|TACUSDT|NA|DATA_GAP_SIGNAL_REFERENCE|NA|NA|
|JCTUSDT|0.3977|DATA_GAP_SIGNAL_REFERENCE|NA|NA|
|SPACEUSDT|-0.9595|DATA_GAP_SIGNAL_REFERENCE|NA|NA|
|SKRUSDT|NA|DATA_GAP_SIGNAL_REFERENCE|NA|NA|

## Стоп и различие периодов

Все 13 входов датированы 11–16 ноября. Старый годовой корпус полноценно оценивал сигналы только до 08.11 23:00 из-за требования 80h наблюдения. Сравнение годового RAW и этой live-когорты не является сравнением одинаковых сделок.

Во всех 13 карточках signal stop равен 5,6% от actual entry. Единственный убыток SPACE закрылся примерно на +5,49% против шорта. DB initial_stop около 12%/19,8% не доказывает действующий stop: snapshot стратегии имеет широкий initial fallback до custom stop. Оснований менять торговый SL на 12% нет. Нативная история стоп-ордеров отсутствует, вывод ограничен этими фактами.

Суммируются все partial exits. Переданные kind эвристические, fee_R оценочный; реальные доли отличаются от идеальных 50/30/20 из-за округления. Trade-level net_R сохраняется как передан оператором, не заменяется суммой оценочных legs и funding не прибавляется дважды.

## Корреляция

NBIS/KORU/MVLL имеют общий signal_ms: True. Их сумма 1.8440R. По закрытым H1 ДО входа рассчитана матрица корреляции, n=168; данные и значения в SUMMARY.json. Ценовая корреляция не равна корреляции бинарных побед.

При historical selected p=0.7313 условная вероятность ≥12 побед из 13: iid **9.89%**; при полной зависимости только этой тройки и независимости остальных десяти **14.96%**. Это чувствительность к зависимости, а не измеренная вероятность «удачи». Истинная корреляция исходов и сопоставимость p для нового режима не установлены.

## Исполнение и 18 невходов

Статусы 1m proxy: {"CLOSED": 20, "NOFILL": 1, "DATA_GAP_SIGNAL_REFERENCE": 7, "DATA_GAP_M1": 2, "OPEN_RIGHT_CENSORED": 1}. Полный денежный model net известен для 0 из 31 строк. Funding November probe: HTTPError: HTTP Error 404: Not Found. REST blocked: True. Недостающие свечи/funding дают DATA_GAP/null, не NOFILL/0.

Binance явно является proxy Bybit. Даже касание лимита здесь не устанавливает причину отказа живого бота. До истечения TTL — pending/censored. Покрытие signals.json неполное; отсутствие записи не подтверждает отсутствие всех старых сигналов. Все 18 NOT_ENTERED_UNKNOWN оставлены в таблице независимо от наличия цены.

Без native Bybit 1m и фактических order/BE updates точная реплика LIVE не сертифицирована. Лимит +1,3% может менять отбор; в live есть зона вокруг midpoint и обновляемые заявки. Это проверяемая гипотеза, не объявленная причина всей разницы. Старый BE-компонент уже проверен отдельно и не объяснил годовой убыток.

## Следующий этап

Сразу запускается заранее замороженная матрица из 20 вариантов в research/pf-rubik. Она использует 1m, stop сигнала 5,6%, BE с fees и causal receipt clock, но остаётся экспериментальным Binance proxy. Разница top50 PIT в новом ТЗ и factory top200+model top50% фиксируется в её протоколе; LIVE-вариантом её молча не называем.

## ПРОСТЫМИ СЛОВАМИ ДЛЯ ВЛАДЕЛЬЦА

Выгрузка проверена, все сделки и невходы сохранены. Подсказка про действующий стоп 12% не подтвердилась. Положительная серия и старая история относятся к разным временным когортам; зависимость трёх одновременных сделок повышает вероятность серии. Пробелы цен/funding не скрыты. Дальше — ограниченный исследовательский поиск, без изменения торговли.

Desktop Commander 0, Bybit-ключи 0, LIVE изменений 0
