# А. ARB — краткий разбор и отдельный code PR

Сообщён один инцидент, сырых проверенных trade/order/execution записей n=0. Уведомления09:17/09:25 и −5,04$ — факты сообщения владельца, а не пересчитанный торговый результат. Фактическая причина ещё НЕ УСТАНОВЛЕНА.

Исходник bde8d93461238697e6f769e2282943b382875235: `_xtpsl_sync` делает8 попыток импорта до тревоги. `_ximport_fills` ограничен5страницами×50 пофильтрам order history и realtime, окно начинается с открытия−60сек; отдельные executions/closed-PnL не запрашиваются. Возможны задержка публикации, отдельный child order/тип stop, лимиты истории/пагинации. Hedge positionIdx теряется в старом symbol-map. Выбор конкретной причины ARB без выгрузки был бы догадкой.

Новая существенная находка: старый importer отправляет сообщение о закрытии ДО commit, а исключение commit затем проглатывает. Это возможный механизм «закрыто в уведомлении, открыто в следующем цикле». Нужны реальные exception/DB/order IDs для проверки.

Если импорт не завершился, Trade.is_open/amount не снимаются. Это удерживает локальную строку открытой, source cap и, если текущий SL даёт риск, суммарный open risk. Сама тревога miss8 глобальный entries_blocked не устанавливает; другие stop/guard gates могут блокировать отдельно. Общий лимит и блок повторной пары также зависят от версии Freqtrade; установленная версия пока не подтверждена.

Отдельный Draft PR: https://github.com/valikbabkin94-collab/Crypto-Auto-Radar/pull/594
Ветка fix/arb-flat-readonly-reconcile-20261121
Commit c402ee38636341cbddfd209259ac8f4dd72f8b75

Реализован opt-in, ПО УМОЛЧАНИЮ ВЫКЛЮЧЕННЫЙ путь: подтверждённые one-way flat readbacks с server-time/grace, одна local-позиция и нет local/exchange pending orders, полный проверенный episode, фактические executions+order+closed-PnL/qty/fee. Zero position или closed-PnL summary в одиночку не закрывают БД. Только whitelist GET на биржу; запись лишь локальной бухгалтерии в savepoint, commit проверяется, успех сообщается ПОСЛЕ commit. Новые ордера/cancel/amend отсутствуют. При неполноте остаётся MANUAL_REVIEW, без освобождения слота по догадке. Старые частично импортированные orders без exact exec accounting, возраст эпизода>7дней, pending backupSL и hedge-mode консервативно требуют отдельной сверки.

50 unit tests PASS; fake API запрещает write calls. 62метода стратегии AST-неизменны,3метода — только opt-in guards, новый helper отдельно. Полная проверка с реальным Freqtrade ORM и сохранёнными ответами Bybit ещё нужна. Runtime/конфиги не изменялись; нельзя копировать старую базовую strategy целиком поверх другой actual version. Не сливать/не включать без явного OK владельца.

Экспортёр этого PR собирает недостающие raw-поля из готовых offline snapshots и cached exchange JSON, но не делает новых Bybit calls и не читает ключи.
