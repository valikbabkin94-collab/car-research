# Claude: проверка PF live против истории

Репозиторий `car-research`, ветка `research/pf-live-vs-backtest`. Начать с итогового отчёта, `PROTOCOL_PRE_REPLAY_RU.md`, `CODE_RULE_COMPARISON.json`, `RESULTS/BASELINE_PARITY.json` и `CHECKPOINT.json`.

Готово: OLD parity 2113/2113, funding parity 1466, BE-only replay на сохранённых Bybit 5m, обе половины / TAIL40 / recent и условная вероятность серии. **13 закрытых live-строк недоступны.** Две карточки сигналов не заменяют сделки; обе RIGHT_CENSORED. Историю повторно не запускать.

## Проверка результатов

1. Протокол `173d1ba` до PnL; основной run `43898010151`, код `b7ef9526c0d474d0b4f51c9490ca50b6dd48f07a`. Все старые статусы/цены/gross/events и известный funding совпали. Изменены только BE price и соответствующий остаток для funding; сигналов/фильтров/TP не подбирали.
2. OLD BE=entry, default live short BE=entry*(1−0,0011). Snapshot не аттестует все 13 фактических версий. Model JSON семантически равен reference; отличающиеся SHA сериализованных файлов не означают смену модели. Actual runtime config и price type не получены.
3. FULL: 1761 closed / 1466 known / 295 unknown. При `[start,end)` 2112 opportunities, ещё одна censored на END. SELECTED: 1040 opportunities / 823 closed / 696 known / 127 unknown. Полного net по всем closed нет. RAW −89,309→−88,607R; SELECTED −24,988→−25,026R. Проверить обе половины и TAIL40, сохранённые отрицательные результаты.
4. Исторические частичные TP учитываются по каждой ноге. Не сравнивать всю модельную сделку только с последним BE; в live использовать полный realized результат, а не неполный последний close. JCT без даты/entry/исходного риска не сопоставлен.
5. Вероятность X≥12 из 13 условна. Для доступной SELECTED с 23.10: 8,11% OLD, 10,51% BE-aligned. Историческое p оценено по неполной выборке, iid и сопоставимость не доказаны. Это не вероятность правильности модели или случайности прибыли.
6. Проверить смысл entry-zone против fixed midpoint, времена фактических TP/BE, mark/last, maker/taker, минимум/lot/dust. Не подменять внутрисвечной порядок удобным после просмотра исходов. В модели сохранены консервативные допущения; нужны same-venue 1m/ticks и actual fills.
7. `RESULTS/FINAL_CHECKS.json`, run `43900553836`: 23 теста PASS, reconcile-only оставил SHA обоих исторических ledgers неизменными. Сохранены все необходимые входы, артефакты retention 7 дней.

## Недостающая безопасная выгрузка

Только при наличии у Claude авторизованного read-only доступа подготовить агрегаты, **не меняя торговлю, процессы, конфиги, VPN, стопы или ордера**. Codex такого доступа не получал и работал через GitHub.

- 13 закрытых PUMP_FADE-сделок: symbol, signal_ms, created_ms, entry_ms/exit_ms UTC, цены входа и исходного стопа, времена/цены/нормированные доли каждого partial exit, итог net_R, R_basis и pnl_basis. Проверить семейство/source и версии; другие сценарии по названию не смешивать.
- Итог должен включать все части. Если funding/fees не подтверждены — явный unknown/null. Не складывать одну и ту же комиссию или прибыль из двух источников дважды.
- Сопоставимый R basis: `INITIAL_NOTIONAL_X_0_0581`, то есть полный realized net / (первоначальное количество входа × actual entry × 0,0581). Первоначальное количество восстановить приватно, не использовать уменьшившийся остаток. Ни quantity, ни notional, ни баланс в public не переносить.
- Полный 30-дневный decision-log: принятые, отклонённые, неисполненные и отменённые сигналы, реальные причины и границы coverage. 13 закрытых сделок не являются полным журналом решений.
- Только whitelist из `LIVE_EXPORT_SCHEMA.json`: никаких raw account/order IDs, chat_id, адресов, ключей или сырой БД. До публикации рекурсивный scan, включая gzip/ZIP/NPZ.

Обновить в этой же публичной ветке только:

- `research/pf_live_vs_backtest_20261116/inputs/LIVE_TRADES_AGGREGATES.json`
- `research/pf_live_vs_backtest_20261116/inputs/LIVE_DECISIONS_AGGREGATES.json`

Указать актуальные status/coverage. Workflow `PF live aggregate reconciliation only` выполнит `audit.py --reconcile-only`, используя готовые `OLD_REPRODUCED.jsonl.gz` и `BE_ALIGNED_5M.jsonl.gz`. Годовой replay не повторяется. Для целевого анализа 13 сделок зафиксировать source/UTC/рынок/конфиг до просмотра новых цен; отсутствующие окна помечать DATA_GAP, не нулём или «бот пропустил».

## ПРОСТЫМИ СЛОВАМИ ДЛЯ ВЛАДЕЛЬЦА

История проверена, одна разница BE измерена. Для окончательного сравнения нужна безопасная выгрузка 13 настоящих сделок и решений сканера. Торговлю ради этого менять не нужно.

Desktop Commander 0, Bybit-ключи 0, LIVE изменений 0
