# Воспроизведение выполненного расчёта

Протокол до новых агрегатов: `b21119734c7e7e2fa566124aa1e0e9e242c21cfa`.
Код, безопасные входы и восемь тестов до результатов: `7935b12c5047604fdcfca345818fb88f0b3690f3`.
Происхождение и SHA: INPUT_PROVENANCE.json. Приватный исходный экспорт в публичный репозиторий не копируется.

Выполнена только проверка экономики сохранённых Whalesguide M1 и отдельного Wolfx M0. Новых свечных прогонов и загрузок рынка не было. Python 3.12, стандартная библиотека, без установки пакетов или торговых библиотек.

```bash
git clone --single-branch --branch research/edge-search-20261120 https://github.com/valikbabkin94-collab/car-research.git
cd car-research
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s research/edge_search_20261120 -p 'test_*.py' -v
EXPERIMENT_CODE_SHA=7935b12c5047604fdcfca345818fb88f0b3690f3 PYTHONDONTWRITEBYTECODE=1 python research/edge_search_20261120/ledger_audit.py
```

Для PowerShell перед последней командой установить `$env:EXPERIMENT_CODE_SHA='7935b12c5047604fdcfca345818fb88f0b3690f3'`, затем выполнить ту же команду python. Код не импортирует runtime/SDK, не читает `.env` и не использует сеть. Записывает только RESULTS.json в исследовательской папке. Это одноразовый расчёт, не коллектор.

Тесты используют синтетические примеры исключительно для проверки алгебры издержек, геометрии R, неизвестного funding, no-fill/gap, просадки по порядку закрытий, close-before-entry при равных timestamps и концентрации. Они не заменяют реальные 72/54 исхода расчёта.

Входы: inputs/targeted_numeric.json и inputs/split_definitions.json. Extract-код: extract_inputs.py. Аудитор с доступом к приватному источнику может отдельно сверить gzip SHA/ARTIFACT_MANIFEST и числовую производную. Исходные тексты и ID не публиковать.

В PR #590 исходный симулятор возвращает `(gross−0.0021×entry)/abs(entry−initial_SL)`. Поэтому общий бюджет исполнения заменяется 21→35/50 bp алгебраически, без нового свечного бэктеста. Это гипотетические бюджеты исполнения, не измеренные полные расходы с funding.

Время выполнения runtime_seconds различается при повторе. Для канонической сверки удалить только это верхнеуровневое поле и сериализовать JSON с sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False. SHA256 сохранён в CANONICAL_RESULT_SHA256.json. Остальные поля, seed и результаты должны совпадать; code_commit берётся из переменной EXPERIMENT_CODE_SHA.

Повторный запуск не требуется для чтения отчёта: расчёт завершён, результаты и отрицательные выводы сохранены. Старые исследования перечислены в EVIDENCE_MATRIX.md и не пересчитывались.
