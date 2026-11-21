# Дополнение21.11: итог по приоритетам

1. Export: car_research_export.py в Draft PR#3,21 офлайн tests PASS. Реальную торговую базу не читали. Скрипт читает только явные согласованные offline snapshots, не меняет БД/файлы-источники, не подключается к Bybit/Telegram/Windows tasks и не читает .env. Секретные поля скрываются, реальные bundles PRIVATE: в публичный car-research их не копировать. Автоматическая очистка не является гарантией полной анонимности логов: перед публикацией вне приватного репозитория нужна отдельная проверка.

2. Egress: Draft PR#593 open/unmerged, head0921f24d2e9999ec4bae6b1989a1243fa55ed7ea. Codex не устанавливал и повторно не тестировал старый фикс; актуальная установка из GitHub не доказана.

3. ARB: отдельный Draft PR#594, commit c402ee38636341cbddfd209259ac8f4dd72f8b75,50 tests PASS, новая опция disabled. A_ARB_REPORT_RU.md содержит кодовые причины и ограничения; причина реального инцидента не доказана.

4. Б: стоп-анализ НЕ ПРОВЕРЕН (n0 пригодных новых строк); методика ATR14closed1m, ранний stop15min, post-stop originalTP1/24h, coincident source-stops5min зафиксирована без подгонки. ALT_CLONE raw/manager attribution требует paired ledgers/событий; конечные −50,67/−65R этого не доказывают.

5. В: source-рейтинг НЕ ВЫЧИСЛЕН до cash reconciliation. Пользовательские102/n16/PF5,15/WR88% не приняты за verified net. Для всех обсуждаемых источников пока категория «собрать/сверить данные», без изменения риска. ALTCOIN_MGR n1 и OLEG_STYLE n3 исключены из сравнительных выводов. Требования к независимому доказательству PF и цена ошибочного решения — B_C_REPORT_RU.md.

Остальной анализ дня падения BTC не запускался: ожидается пригодная выгрузка. Старые исследования/PR#1/#2 не изменены. Новых PnL-тестов0, LIVE/API Bybit/orders/configs/risks/IP/processes/tasks0, Desktop/Remote0, main merge0.

Недостаёт: согласованной DB copy без WAL и raw realized_profit/close_profit_abs/fills/fees/funding; initial financial protectiveSL/qty и manager BE/trailing/partial histories; raw/managed ALT_CLONE с одинаковыми входами; source/variant/deployed SHA и безопасного config extract; decision/ingest/egress/latency/clock events; coin/BTC1m и post-stop покрытия; ARB positions/order history/executions/closed-PnL/open-order cached responses с timeframe/IDs. Скрипт принимает эти УЖЕ СОХРАНЁННЫЕ источники и помечает отсутствующее. Если история никогда не логировалась, скрипт не может её восстановить.

Файл codex_task_export_script.txt не был получен: реализация покрывает текущие инструкции и DATA_NEEDED PR#3, чтение неизвестного текста не заявляется.
