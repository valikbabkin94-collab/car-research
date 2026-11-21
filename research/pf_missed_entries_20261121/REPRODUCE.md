# Проверка кода без исполнения торговой системы

verify_source.py использует только Python stdlib и AST. Не импортирует торговые модули, не читает .env, не имеет сетевых вызовов, не отправляет сообщения или ордера и не считает PnL.

Аудитору с доступом к GitHub нужны пять файлов из SHA bde8d93461238697e6f769e2282943b382875235: CarFastPathV1.py сохранить как strategy_source.py, fastpath/report.py как report.py, fastpath/ingest.py как ingest.py, fastpath/tools/shadow_pump_fade.py и shadow_altcoin_clone.py под их именами. Точные SHA256 в CODE_SOURCE_MANIFEST.json.

```bash
python research/pf_missed_entries_20261121/verify_source.py --source-dir /path/to/github_source_copies
```

Готовый фактический вывод — SOURCE_VERIFICATION.json. Это source hash/AST assertions, не регрессионные тесты работающего бота и не независимая проверка рыночных результатов. Отдельные примеры искусственных свечей не использовались. Исторические исполнения не пересчитывались.

REPORT_RU.md ссылается на точные source lines; полные приватные runtime payload не опубликованы. Старый missed_audit.py найден, но не исполнялся: это иной авторский corpus/replay по 5m от публикации, а не требуемый market-at-decision PF контрфактуал. Старые PF_MARKET/PF_CHASE/resting исследования не дублировались.
