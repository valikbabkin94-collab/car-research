# PUMP_FADE runner: историческое сравнение и выключенный shadow-код

**Итог: улучшение не подтверждено; TRAIN-selected RUN15 хуже базы на TEST.**

- [Отчёт](REPORT_RU.md), [таблицы](TABLES_RU.md), [64 строки CSV](METRICS.csv).
- [Протокол](FROZEN_PROTOCOL.json), [контрольная точка](CHECKPOINT.json), [источники](SOURCE_MANIFEST.json).
- [Проверка Claude/ChatGPT](HANDOFF_FOR_CLAUDE_RU.md), [недостающие данные](DATA_NEEDED.md).

TRAIN_RUNNER_ROWS.jsonl.gz / TEST_RUNNER_ROWS.jsonl.gz содержат все4новыхвыхода на одних564/473входах. ВариантыPR#4/PR#5 повторно не рассчитывались. Новыхpaperнаблюдений0.

Офлайнunit-проверка: `python -m unittest -v test_runner` (14тестов; эти же проверки включены в93теста фабрики). Для воспроизведения использовать NumPy2.3.5/Python3.12, pinnedinputsPR#4, исходныйprepare.pyPR#4 только для кешацен; bootstrap встроен вrun_runner.py. CLI `--root ABSOLUTE_RESEARCH_SCRATCH --stage train|test`, ожидаемыеinput/prepared/results каквисходномскрипте. ЗавершённыеCOMPLETEэтапы отказываютсяперезапускаться. Поумолчаниюscratchпутьлокальныйдляэтогозапуска; независимыйаудиторзадаётсвой--root,нетсвязисноутбуком.

Перед TEST обязателен selection_commit.json с SHA уже опубликованного TRAINвыбора; точныеSHAвCHECKPOINT. Не меняйте winner после просмотраTEST. Если просто проверяете результат, читайте сохранённыеledgers/JSON — полныйповторне нужен.

pr4_engine.py — точная сохранённаякопиядля функцииfunding_result; старыйentryreplay не вызывался. Kernel runner_tail.py байт-в-байт совпадает с модулем shadow-кода. Unit-fixtures синтетические только для проверки исполнения; вPnL использованы реальные сохранённые цены.

Все файлы имеютSHA256 вMANIFEST.json, кроме самого манифеста. Результаты — условные price/funding-mark модели, не фактический доход счёта. LIVEне менялся.
