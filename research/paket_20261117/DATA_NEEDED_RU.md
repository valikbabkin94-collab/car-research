# Недостающие данные

- OLEG: полный архив первоначальных сигналов и updates, published/first_observed UTC, инструмент/сторона, entry-zone, авторские SL/TP, timestamps изменений; требуются исходные версии сообщений, а не только итоговые посты. Инструменты oleg_main_study/style_study не являются архивом. Доступные13 LIVE и3 STYLE не подменяют историю.
- LIVE97:44 входа не подтверждены Binance1m. Нужны сохранённые Bybit1m [первый entry fill−1м, фактический exit+72ч], правильные symbol/contract multiplier/renames; разбиение entryfills с UTC/ценой и нормализованными весами, чтобы отличить усреднённую цену от первого исполнения; исходный strategy stop/risk at signal и изменения отдельно от safety stop. Funding/fee cash в долях первоначального notional, без баланса/ключей/ID. Это не предложение обращаться к торговому API.
- PF:346 из1761 фиксированных входов не подтверждены Binance5m-window. Полный список в PF_5M_ENTRY_VALIDATION. Ровно316 NOFILL и36 RIGHT_CENSORED без сохранённой точки входа остаются в PF_PRIOR_UNFILLED_AUDIT. Не восстанавливать точку входа задним числом из успеха цены.
- UNLOCK: открытая историческая календарная таблица date,symbol,unlocked amount/%supply,дата первой доступности расписания, revision vintage,источник. Два проверенных источника HTTP402/404; текущий/синтетический календарь не заменяет point-in-time историю.
- Новые листинги: date первого BinanceUSDT-M archive, отдельно daily-only новые символы, полный historical catalogue сdelisted; отсутствие раннего PIT top100 (<2023-11) означает пропуск контроля, не случайное заполнение сегодняшними монетами.
- Wick: анализируется сохранённый v1-universe, а не заявляется полный рынок. Для граничных месяцев нужен непрерывный предшествующий24hV. Потери по resource budget и source gaps сохраняются отдельно.

Desktop Commander 0, Telegram-сессии 0, Bybit-ключи 0, LIVE изменений 0
