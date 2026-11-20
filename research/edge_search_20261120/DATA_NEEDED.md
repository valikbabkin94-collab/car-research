# DATA_NEEDED — точные недостающие доказательства

Сначала нужны **уже существующие** capture T1/T2. Codex не подключается к Acer/Honor и не меняет задачи. Приватные тексты и журналы публиковать только в приватном Crypto-Auto-Radar; в car-research допустимы обезличенные числовые производные. Ключи, `.env` и сессии не нужны. Повторять уже выполненные GitHub-расчёты вручную не требуется.

## T0: денежный trade_waterfall

Найденный экспорт 97 сделок содержит source/coin/side/open/close/entry/initial_stop/stop_pct/exit_reason/exits/net_R. Поля `realized_profit`, фактических fill_qty и settled funding в нём нет. Предыдущий X0-аудит переиспользован: его calibrated_R не доказывает реальный первоначальный финансовый риск.

Нужен безопасный экспорт доступного окна: trade_id/source/signal_hash; actual fills с order_id/fill_id/time/side/price/qty/fee/fee_asset; `realized_profit`; отдельные settled funding cashflows; версия Freqtrade и семантика включения funding в прибыль. Также нужны исходный **реальный защитный SL**, initial_qty и начальный риск в деньгах, а не аварийный `initial_stop`.

Для отказов нужны исходные заявки, no-order/cancel/unfilled, точные deny reasons и временные события entries_blocked/daily/risk/slot/reservation. Снимок текущего состояния не доказывает прошлую блокировку. Повторяющиеся строки TP одного ордера нельзя считать новыми полными fills. До этих данных настоящие netUSDT/R остаются NA.

## T1: существующий capture SHORT_STRONG

Если уже сохранены: `main30.csv`, `main_study/k5` либо компактный числовой журнал всех 1 981 семейств / 57 неполных / 61 отфильтрованного входа с SHA, первыми версиями и порядком исполнения. В проверенной ветке опубликованы метод и итоги, не эти исходники. Старый replay не запускать без нового причинного вопроса.

Для проверки после исходной фиксации нужны first_seen/first_received, family_id/revision/source_SHA, plan_type/entry_mode/side/ctx/regime, исходная зона/SL/TP, время публикации/истечения, bid/ask/touch/fill/no-fill и причины отказов, расходы, instrument filters и портфельные слоты. В том же окне нужны SHORT-only и SHORT+BEARISH, включая отказы. Использовать готовые записи текущего producer, не включать источник в LIVE и не создавать daemon. Уже просмотренный replay после 25.10 не становится независимым forward.

## T2: существующий коллектор PR #591

По handoff checkout расположен в `C:\CAR_PAPER_CHANNELS`, задача — `CAR_Shadow_Paper_Channels`. Актуальное выполнение из GitHub не проверено. Для чтения готовых результатов нужны:

- Фактический `StatePath` из аргументов задачи. По README путь по умолчанию: `<RepoRoot>/fastpath/freqtrade/user_data/shadow/paper_channels.json`.
- `paper_channels.json`: channel/post_hash, first_received, исходный plan и text SHA, редактирования, model/status/no-fill/skip/gap/fills/SL/TP/BE, code SHA.
- `paper_channels.posts.jsonl` и уже существующие `.gz`-части: NEW_POST/TEXT_CHANGED/MISSING_CANDIDATE/PRICE_BATCH/event_id, UTC и SHA. Исходный текст оставить приватным.
- `paper_channels.errors.jsonl`, покрытие и asof_utc, instrument info/qty/tick/min-notional/session filters, реальные funding cashflows.
- Для денежной проверки: уже согласованные риск, баланс и маржа как данные, без изменения настроек. Риск из другого старого конфига не доказывает sizing Whalesguide.

Время публикации не заменяет first_received; отсутствие отметки edited не доказывает исходную версию. PR #591 считает M0/M1/M3 без прежнего cooldown 6 часов, поэтому admission cohort может отличаться. Сначала сверить покрытие, SHA и общее окно. Не менять коллектор, scheduler и его порог 30 сделок. Желательная граница исследования в 40 независимых сделок — отдельный критерий анализа.

## T3: до любого PnL

Нужны 1h OHLCV и quote-turnover для исторической native crypto-вселенной, BTC и ETH; минимум 169 закрытий для 168 доходностей. Нужны listing/delisting/category/status того времени, point-in-time turnover rank и почасовой состав рыночного фактора.

Для входов — native Bybit 1m, синхронные bid/ask/depth после подтверждения, исторические qty/tick/notional filters, funding и задержки. Для контроля — готовый совпадающий журнал старого PF. Снимок 300 инструментов и обычные 1h цены не заменяют эти данные. Правила и пределы будущего независимого окна записаны в FROZEN_T3.md; текущих загрузок: 0. Новый постоянный сборщик не предлагается.

## T4: записи после исследования 12.11

По handoff существующая фабрика — `C:\CAR_SHADOW_FACTORY`, база `user_data/shadow/factory.sqlite`. Нужны готовые read-only экспорты TRADFI/EXT после исходной фиксации: сигналы, отказы, исполнения, code SHA, native symbol type, listing/status, календарь торгов/пауз/holiday/halt, комиссии/funding/lot/tick и отсутствующие 1m интервалы. Классификация нужна на дату решения, не по нынешнему снимку. Фабрику не перезапускать, второй коллектор не создавать.

## T5: синхронные котировки, если они уже есть

Нужны spot/index/mark/perp quotes или реальные trades с UTC/venue/clock skew, bid/ask/depth, исторические contract filters и funding/capital/margin. Часовые OHLC из FUNDING_CARRY не доказывают исполнимый premium. Если истории котировок нет, T5 остаётся DATA_GAP; платные API и новые постоянные сервисы не нужны.

Достаточно ссылок и SHA уже готовых приватных экспортов. Не отправлять ключи; не повторять расчёты Whalesguide/Wolfx и прежние матрицы.
