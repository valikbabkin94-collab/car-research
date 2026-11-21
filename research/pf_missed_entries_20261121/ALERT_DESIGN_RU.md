# Предложение observability, не установленный код

Этот документ не меняет LIVE и не разрешает обход защит. Любая реализация — отдельный code PR с tests, без merge/deploy до OK владельца.

Состояния по immutable source+signal ID: emitted → accepted/rejected_ingest → eligible → pending_wait / blocked → order_intent → fill / terminal_skip / expired_unfilled / data_gap. Сохранять все attempts и timestamps/quote source, first deny и последующие причины; pending и data_gap не превращать в skip/0R. Одно выполнение сигнала может иметь и egress, и последующий price deny — intersections отдельно от disjoint primary counts.

Предлагаемый N=3 окончательных последовательных пропуска eligible сигналов PF. Streak определяется порядком сигналов, не попыток; незавершённый pending не пропуск. Fill сбрасывает streak. Порог задаётся только для наблюдения, не меняет допуск. Сигналы разных монет сохраняют порядок UTC и tie по ID, повторные события идемпотентны. При отсутствии полного ledger streak UNKNOWN, не 0. Notify на переходе below→at_threshold, recovery на первом подтверждённом fill, без spam на каждом цикле. После рестарта state сохраняется и не создаёт повтор incident.

Если во время PF eligible intent guard вернул confirmed EGRESS_BLOCKED — немедленное сообщение один раз на signal/incident с code, UTC, типом IP failure, стадией и current quote availability. Предупреждение неизвестного IP само по себе не утверждать блокировкой. Никогда не отменять fail-closed и не отправлять ордер «для проверки».

Health observer отдельно сообщает, что producer/ingest/price stream устарел; отсутствие подходящего торгового сигнала не является неисправностью. Действующий hourly schedule и source должны быть доказаны deployed metadata, а порог silence — явно согласован по их cadence, без нового сервиса в этом этапе.

Ежедневная строка (поля, НЕ пример измеренных чисел): PF emitted=?, accepted=?, pre-ingest rejected={full codes}, eligible=?, entry fills=?, pending=?, terminal skipped={full codes}, blocked unique=?, mixed causes=?, DATA_GAP=?. Все числа за одно окно и одну cohort; publication/creation/receipt/decision/fill clocks не смешивать. Полные русские причины + машинные коды, цена и время/age по возможности. Длинный отчёт разбивать на сообщения без разрыва Markdown entities/fences и без потери текста, response сохранять без токенов. Отказ отправки — отдельное observability событие, не успех.

Обязательные tests до code PR: success/WAIT/TP1/STOP; ingest stale/future/filter/duplicate; disabled source отдельно; egress before signal/during WAIT/after terminal; mixed reasons distinct counts; N=3 boundary; duplicate attempts; out-of-order/tied events; restart/recovery; unknown data; отсутствие new orders/config writes; длинные Unicode reasons >4096 с корректным Markdown split; failure Telegram не помечает sent. Сценарии используют синтетические события исключительно как unit tests, не искусственную рыночную историю/PnL.

Не существует защиты, которая гарантирует прибыль или постоянно исполняет PUMP_FADE в любой рынок. Цель этого наблюдения — не скрывать отсутствие сигналов/данных/допуска и вовремя сообщать владельцу.
