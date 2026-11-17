# Claude Code — независимая проверка RECHECK_1M

Репозиторий valikbabkin94-collab/car-research; ветка research/recheck-1m-20261118; каталог research/recheck_1m_20261118.

Прочитать OTCHET_DLYA_CLAUDE_CODEX_RECHECK_1M_20261118.md, FINAL_COMPLETION_AUDIT.json, PROTOCOL_PRE_PNL.json, EXECUTION_CONTRACT_PRE_PNL_RU.md, SOURCE_AUDIT.json, DATA_NEEDED.md и final/DUMP_METRICS.json.

Выполнено: DUMP на всех1141 исходных записях,1001 покрыта минутами,140 явных gaps. Не выполнены точные новые IDEAS ABC/NIGHT из-за отсутствия исходных строк в GitHub. A5/B10 уже были1m, результаты переиспользованы; дополнительный last40/random требует журналов.

Проверить:

1. Исходный TRADE_LEDGER PRIMARY1141 и selected flags, fixed entry reference,807/334 controls. Не переобучалась ли TOP50. Нормировка старой модели должна быть(.056+.0021), не новая условная1R.
2. Протокол83acdf... был до PnL; code75c577... исправил только metadata collision и checkpoint IO. H1-выбор в finalize.py использует только H1 с исходным80h purge; H2 не определяет параметры. Код выбора был зафиксирован заранее; минутные строки обеих половин рассчитаны общими symbol jobs, не выдавать это за отдельно новый untouched holdout.
3. Replay сохраняет исходную цену и час, требует её достижимости внутри часа, после этого разрешает TP в следующих минутах того же часа. Не приравнивать это к гарантированному реальному limit-fill Binance: исходные цены с Bybit, внутри минуты остаются неизвестные порядки и gap/queue риски. FIRST/BE ambiguity и диагностический альтернативный replay не являются точными тиками/доказанной верхней границей.
4. Самостоятельно суммировать все1001/477 покрытых R и matched old R, события fraction=1, timestamps<=72h. Цифры RAW−73.252743R, TOP50−20.238R округлены в отчёте; точные значения в JSON. Не заявлять знак всех1141 по неполной выборке.
5. Проверить83 minute gaps/57 entry-price gaps, полные исходные1141/538 counts и долю покрытия. Не исключить пропуски из denominator.9 unit tests воспроизводимы без подключения торгового runtime.
6. Проверить paired comparisons: NOFILL=0 по возможности; отдельно common-filled пары. BH family8 с p=1 для недоступных тестов. Для TOP50 H2 excess+2.272R,q1, не основание продвижения.
7. Funding является архивным Bybit,1mclose Binance proxy. Первичный сравнимый R без funding; дополнительные known cash/unknown stress отдельно. Не называть частичный funding полным.
8. Проверить старый A5/B10 PROTOCOL: это уже1m, так что нет задачи повторять его как1h→1m. B10 full+15.927R при H1−1.631R не прошёл критерий; прежний H2 не свежий OOS.
9. NIGHT — skip lowvol AND lowATR, не leave-only-lowvol. Полный policy net=base_R*n+gain_per_opportunity*n, включая неотфильтрованные строки без признаков. Validation703 retained/−3.534R;610 covered mean−.01071R — другой denominator. Для новой проверки нужен PASSPORT_DATASET, не агрегаты.

Для продолжения выгрузить только точные сохранённые исследовательские inputs по DATA_NEEDED.md:17574 старых ABC событий с ATR/risk/controls/scripts;2272 PASSPORT строки либо3 CSV с исходными SHA;125 A5/B10 trades плюсконтроли; отсутствующие исторические Bybit1m окна. Исходные Telegram-тексты, ключи, ордера/аккаунт и работающие сервисы не нужны. Без этих данных не повторять уже готовый DUMP или старые BROAD224/LEVEL40/прочие переборы.

Успешный Actions run44187973528; code75c57764a0972e308257288cfcc3aa9baaf2a69f; исходный итоговый commitd18125d1d766dcceeb929ba91fe7831e4f363a4b. Новых variants нет, enabled=false ничего не активирует.

Desktop Commander 0, Bybit-ключи 0, LIVE изменений 0.
