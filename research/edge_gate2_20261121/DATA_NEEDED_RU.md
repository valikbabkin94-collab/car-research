# EDGE GATE 2: минимальные недостающие пакеты

Никаких ключей, `.env`, Telegram-сессий, чтения ноутбуков Codex и ручного повторения старых вычислений. Нужна публикация **уже сохранённых** безопасных исходников через приватный GitHub; наружу — только агрегаты. Сырые приватные посты и торговые идентификаторы не копировать в публичный car-research.

## 1. SHORT_STRONG — сначала этот пакет

Из объявленных `CAR_RUNTIME/analysis/main30.csv` и `main_study/k5`: готовый компактный ledger всех 1 981 первых family/revision и 57 неполных; side/ctx/regime/plan_type/entry_mode; исходные entry_zone/protectiveSL/TP/TTL; publication/first_received/decision/fill/partial_exit/final_exit UTC, причины no-fill/gap/отказа; gross price PnL, геометрический initial risk и source_R отдельно; code/data SHA и фактические границы/пропуски покрытия. Включить SHORT-only и SHORT+BEARISH. Если такого ledger нет, достаточно самих существующих CSV/133 файлов кэша с манифестом — до расчёта отдельно проверить исходную точность модели, не пересчитывать старое автоматически.

Для действительно новых наблюдений: тот же формат последующего capture, с первой глобальной версией, реальным receipt, незаполненными/отменёнными сигналами и историческими limits/fees/funding. Нельзя отбирать только 61 победивший набор либо считать исходный R одинаковым с T2.

## 2. Существующий paper PR #591

Фактические args задачи CAR_Shadow_Paper_Channels / StatePath (как read-only данные), scheduler LastRunTime/LastTaskResult, heartbeat/asof_utc и code SHA; по умолчанию `<RepoRoot>/fastpath/freqtrade/user_data/shadow/paper_channels.json`, также `paper_channels.posts.jsonl[.gz]`, `paper_channels.errors.jsonl`. По handoff checkout — C:\CAR_PAPER_CHANNELS. Не устанавливать/запускать/изменять задачу.

Нужны записи first_received после 14.11.2026 00:00 UTC: исходный text SHA/plan, NEW_POST/TEXT_CHANGED/MISSING_CANDIDATE/PRICE_BATCH, цены и все статусы M0/M1/M3, включая no-fill/gap. Actual receipt не заменять временем публикации. Приватный текст оставить приватным. Для задержек нужен clock offset или явная неопределённость синхронизации. Финансовые условия и sizing нужны как существующие данные, без изменения риска.

## 3. Фактические деньги CAR

Анонимизированные `realized_profit` И `close_profit_abs` раздельно с provenance/версиями, статусом закрытия и уникальным trade key; реальные entry/exit fills с quantity/price/fee/fee_asset/time/fill_id; settled funding по cashflow; начальный финансовый protectiveSL и quantity с timestamp; версии Freqtrade/учётная семантика. Для баланса — equity/cashflow reconciliation, deposits/withdrawals/transfers/unrealized отдельно. 26-строчный журнал и 97-строчный net_R export не заменяют эти поля.

Для пропусков — полные сигналы, решения gate, границы действительных блокировок, order intent, подтверждённые fill/cancel/no-fill, slot/risk reservations. 246 «denied entry» и 8 558 lock-сообщений из README — счётчики логов, не столько независимых потерянных прибыльных сделок. Нельзя переводить их в R без дедупликации и пути цены.

## 4. RESIDUAL_SHOCK

Native исторический crypto USDT-linear universe с delisted, PIT status/category/listing/turnover rank; полные 1h для 168-return warmup/рыночного фактора и время доступности закрытия; native 1m и contemporaneous bid/ask/depth/receive timestamps/filters; actual funding. Нужен ещё не использованный после новой фиксации интервал. Старые L50-файлы объявлены только в архивном манифесте за 06–16.10 и не получены через GitHub; нельзя назвать это новым prospective периодом.

Сначала внешний review нового landmark-контроля, estimands и валидного статистического теста; затем новый protocol SHA. Сейчас нет основания для нового PnL-прогона, длительной скачки или нового сборщика.
