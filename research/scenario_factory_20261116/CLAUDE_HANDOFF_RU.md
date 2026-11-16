# Независимая проверка Claude

Приватная ветка feat/shadow-factory-20261115, публичная research/scenario-factory. Проверять исходный код b6b2fef8d501cd6e40765838b325dc3dfba538f0 и финальный commit пакета; SHA source в release/MANIFEST.json и BUNDLE_SHA256.json, SHA документационного commit получить git rev-parse HEAD.

1. Сверить неизменённую модель, BASE и существующие варианты; S1 union, S5 идентичность fills и maker-assumption label.
2. Проверить только разрешённые публичные GET, фиксированный официальный article host, запрет redirect; отсутствие торговых SDK, ключей, private endpoints и реальных ордеров.
3. Проверить временную причинность ticker first-seen, закрытых свечей, next1m fill, задержки G3, Funding(entry,exit], SL-first/no TP fill-bar, old deadline replay до принятия revision объявления. Проверить портфель G3 по известному к моменту входа NAV.
4. Повторить47 offline-тестов tests/shadow_factory. Дополнительно на Windows проверить task Disabled/Running, отказ на локальных изменениях, --check/apply/rollback в одноразовой sandbox. Тесты Codex не доказывают реальный Scheduler/API.
5. Проверить пакет только с3 разрешёнными файлами + updater/manifest/readme, отсутствие БД/архивов/ключей. После отдельного разрешения владельца руководствоваться UPGRADE_README_RU.md; старый installer не использовать. Updater не управляет расписанием. Rollback архивирует новые paper-результаты до возвращения старой БД.
6. Независимо воспроизвести S5 из опубликованных inputs по EXPERIMENT_S5.json; не путать fee placebo с alpha-контролем и maker fills. Сверить295 неизвестных funding, отсутствие model-selection OOS claims. S4 только reuse старого результата.
7. Проверить недельные нулевые строки, среднюю длительность, common-activation BASE, концентрацию и owner-only promotion. Не включать LIVE.

## ПРОСТЫМИ СЛОВАМИ ДЛЯ ВЛАДЕЛЬЦА
Это проверка готового кода и доказательств, а не разрешение на торговлю или установка. Прибыльность не доказана.

Desktop Commander 0, Bybit-ключи 0, LIVE изменений 0
