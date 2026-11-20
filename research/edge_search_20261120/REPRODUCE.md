# Воспроизведение выполненного расчёта

ФазаA: прочитаны task, OPS/HANDOFF18.11, PR560/590/591, pinnedresults/codes. ФазаB: один fixedWhalesM1 economic ledgeraudit +заданная отдельная диагностическаяWolfM0; без bars/новыхпараметров/маркетзагрузок. ФазаC: только исследовательские документы/code/data в этойветке. Отсутствующиеforward/T3/T5 не объявлены выполненными.

Протокол до новых агрегатов: b21119734c7e7e2fa566124aa1e0e9e242c21cfa.
Код+safeinput+8tests до результата: 7935b12c5047604fdcfca345818fb88f0b3690f3.
Данные происхождения и SHA: INPUT_PROVENANCE.json; raw private source payload не копируется вpublic.

Runtime: Python3.12 stdlib, без pip и торговыхбиблиотек. ВGitHubчерезотдельныйcheckout либо обычныйлокальныйисследовательскийcheckout:

```bash
git clone --single-branch --branch research/edge-search-20261120 https://github.com/valikbabkin94-collab/car-research.git
cd car-research
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s research/edge_search_20261120 -p 'test_*.py' -v
EXPERIMENT_CODE_SHA=7935b12c5047604fdcfca345818fb88f0b3690f3 PYTHONDONTWRITEBYTECODE=1 python research/edge_search_20261120/ledger_audit.py
```

PowerShell: передпоследнейкомандой `$env:EXPERIMENT_CODE_SHA='7935b12c5047604fdcfca345818fb88f0b3690f3'`; командаpython таже. Скрипт не импортирует runtime/SDK, не читает .env и не содержитnetwork. Пишет только research/edge_search_20261120/RESULTS.json. Это завершённыйодноразовый расчёт, не collector.

Тесты синтетические и проверяют алгебруcostdelta, R-геометрию, не-NET при неизвестномfunding, nofill/gap, exit-order drawdown, close-before-entry concurrency иконцентрацию. Они не заменяют реальные72/54исходов; те используются только вledger_audit.

Результат воспроизводится из inputs/targeted_numeric.json и split_definitions.json. numericinput — whitelist derivative из pinned private outcomes, extractioncode extract_inputs.py. Аудитор с доступом кприватномуисточнику может отдельно проверить исходный gzipSHA/ARTIFACT_MANIFEST и extraction; не публиковать rawtexts/ids. Вsourcecode PR590simulate возвращает `(gross−0.0021×entry)/abs(entry−initialSL)`, что позволяет строго алгебраически заменить общийcostbudget21→35/50bp без свечногопересчёта. Этиbp — гипотетическиеall-inexecutioncost, а не все измеренные реальныеиздержки.

runtime_seconds по определениюразличается на повторе. Дляканонического финансовогорезультата убрать только top-level runtime_seconds, JSON sort_keys=True/separators(',',':'), ensure_ascii=False/allow_nan=False и SHA256. CANONICAL_RESULT_SHA256.json хранитэтотhash; остальные поля/seed/R должнысовпасть. Приразличии code_commit проверьenv, не подменяй результаты заново подобраннойисторией.

Нет необходимости повторятьзапуск, чтобыпрочитать выводы. Все oldnegativeисточники уже закреплены вEVIDENCE_MATRIX; сверяющийChatGPT может проверятьформулы/выборочные строки иметаданные без повторныхмассовыхбэктестов.
