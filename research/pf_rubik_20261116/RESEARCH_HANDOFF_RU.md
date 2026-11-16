# Handoff для независимой проверки Claude

Завершены обе части задания. Годовой replay и старые исследования не повторялись. Параметры 20 вариантов зафиксированы до PnL. TRAIN selection commit: 86f376bcb7bd1c3997bd45ac409416c7cb675788; validation results: 93d05df66838c3537caa33313e71ff8635d8716b. Код расчёта: b7df5780166cb3ae840712732a0ec6d0d63d51b1. Сводные тексты не меняют эти результаты.

Проверять без повторения PnL: CONFIG_FROZEN.json, TRAIN_SELECTION_FROZEN.json, RESULTS/{train,validation}/CODE_AND_CONFIG.json и TABLES.json, STRATEGY_LEADERBOARD.json, SOURCE_CHECKPOINT_PRESERVED.json; затем выборочно ALL_TRADES.json.gz и chunks. Проверить SHA параметров, кода и источников, причинность H1/PIT/funding, задержку 122s, минутное исполнение и stop-first. В E3 проверить сохранение убытка родителя, количества и пересчёта R для переворота. Проверить все 63 строки и поправку BH, концентрацию трёх лучших сделок и запрет выбора по H2. MFE/MAE — минутные границы, не точная тиковая последовательность. Новых тестов до аудита не требуется.

Первая часть находится в research/pf-live-vs-backtest, отчёт OTCHET_DLYA_CLAUDE_CODEX_PF_LIVE_VS_BT_20261116.md, commit bfbd12c. Сопоставить 13 live и18 unknown невходов: 10+10 закрытых proxy-траекторий, ноябрьский funding отсутствует, exact Bybit replication INCONCLUSIVE. Поле DB initial_stop не доказывает активный защитный ордер. Для тех же10 сделок live +4.5564R, proxy priceR +4.134273R без funding.

Основной pipeline https://github.com/valikbabkin94-collab/car-research/actions/runs/43922147568 успешно завершён. Источники сохранены отдельным заданием без PnL. 20 REJECTED, E1 INCONCLUSIVE, кандидаты []. Не менять пороги для превращения провала в прибыльный сценарий. Не устанавливать исследовательские конфиги в действующую фабрику. Top50 raw и factory top200+ML не эквивалентны; H2/TAIL40 пересекаются.

## ПРОСТЫМИ СЛОВАМИ ДЛЯ ВЛАДЕЛЬЦА

Проверить достоверность расчётов и ограничения. Торговое преимущество не доказано. Для продолжения сначала закрыть пробелы исполнения и согласовать новый независимый период, не подгонять результаты этого теста.

Desktop Commander 0, Bybit-ключи 0, LIVE изменений 0
