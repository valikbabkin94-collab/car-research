# DATA_GAP — точная выгрузка через приватный GitHub

Источник по заданию: Acer `C:\CAR_RESEARCH\PF_LIMIT_TEST_20261121`. Codex не подключается к ноутбуку и не запускает выгрузку на нём. Владелец/Claude может опубликовать архив в приватной ветке CAR или car-research; прислать repo, branch, commit, path и SHA256. Сырые приватные тексты/ключи в публичный car-research не переносить.

1. **Индекс архива:** рекурсивный список файлов (relative path, bytes, SHA256), README/протоколы, исходный симулятор и его git/code SHA, все параметры и нормировка R, original A/B/C tables и полный per-trade ledger включая незакрытые/NOFILL/отмены. Не только итоговые суммы.
2. **Все65сигналов:** original id/symbol/side, signal_ms, created_ms, first_received_ms сUTC/timezone, reference price и источник, planned original entry_low/high/mid, SL/TP/доли/BE/expiry, top50 score/threshold/pass, версия и SHA256ML-модели. Первичный необрезанный NDJSON/JSON плюс правила дедупликации.
3. **Публичные1mBybit:** исходные файлы с venue, symbol, timestamp-open UTC, OHLCV, интервалом/coverage, временем скачивания; сигнал−1min до окончания всех входныхTTL+hold, включая пропуски/делистнутые. Если исходный симулятор использовал bid/ask/ticks — их тоже. Не дополнять отсутствие свечей синтетикой.
4. **Исполнения17LIVE:** сопоставление signal_id/order_id/trade_id, request/ack/fill/cancel timestamps UTC, price/qty/fee/liquidity, realised/funding, каждый TP/BE/stop и частичный fill; точная таблица15совпаденийC и остальных различий. Ключи/секреты не нужны.
5. **Допуск:** decision timestamps, последняя закрытая свеча, proposed/custom/rounded rate, bid/ask, invalid/WAIT/cancel причины, transitions entries_blocked/egress, timeout/reject; pending/open slot count и доступный риск на тот момент. Нужны не только закрытые сделки. ФактическиеA-снимки не являются полноценнымC-портфелем.
6. **Безопасный config snapshot:** только PF/FT entry tolerance/chase/better, entry_mode, source enabled, TTL/unfilledtimeout/scheduler settings, risk cap/max slots/min stake rules, версияFreqtrade/стратегии. НикакихAPIключей,proxyпаролей,IPwhitelist илиtelegram sessions.
7. **Market minima:** time-stamped minQty/qtyStep/minNotional/precision/leverage, requested stake/size и округлённыйqty. Не увеличивать риск ради теста.
8. **Funding:** фактические ставки/settlement intervals/marks на удержании; реальныеfees/funding cash для LIVEотдельно. Не переносить cash старойA-сделки наC с другим временем/размером.
9. **Новый cohort:** исходныйtop50modelSHA и будущийappend-only журнал послеотдельногостарта; сырыеfirst_received/decision/потенциальныеquotes/order-receipts/outcomes в исследовательскомконтуре, плюс coverage heartbeat. При невозможностиполучатьновоебезвмешательствавLIVE — стоп сDATA_GAP, не создаватьслужбы.

Предлагаемое приватное место: `research/pf_forward_ac_20261121/inputs/PF_LIMIT_TEST_20261121/`. Это предложение для выгрузки, не утверждение, что папка уже существует.
