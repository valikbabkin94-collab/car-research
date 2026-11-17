# Handoff Claude Code: PF_HEDGED

Репозиторий: valikbabkin94-collab/car-research, ветка research/pf-hedged, каталог research/pf_hedged_20261117.

Прочитать FINAL_SUMMARY_RU.md, FINAL_AUDIT.json, PROTOCOL_PRE_PNL.json, ADDENDUM_PRE_PNL_RU.md, INVALID_RUN_AUDIT.json, selection/SELECTION_FROZEN.json и final/METRICS_ALL_VARIANTS.json. Основной отчёт также в final/OTCHET_DLYA_CLAUDE_CODEX_PF_HEDGED_20261117.md.

Результат:6 фиксированных вариантов убыточны на H1/H2/всей истории; REJECTED в проверенной модели затрат. Замороженный H_ALT50: H1−52.619R, H2−63.679R, last40−24.314R, full−118.083R. Высокий excess+101.048R/q.0015 на H2 не равен прибыли. Не выбирать другого победителя по H2.

Проверять без повторения прежних больших переборов:

1. Сравнить1761 inputs и1415 валидных/346 gaps; шорт-события исходного T0S1B0,13 отсутствовавших purge-путей и200 сохранённых контрольных событий. Родительские source pins в протоколе. Маски813 контролей проверены; max error1.192e−7R.
2. Проверить причинность5mclose+1сек, частичные доли и случай без оставшегося шорта. PIT decision строго до входа; cache key — точная минута/время, не bucket5m.12 regression tests в test_hedge.py. Сценарий границы PIT специально ловит старую ошибку.
3. Проверить квоты корзины, исключения stocks/ETFs, прошлые котировки, aliases только хедж-ноги, отсутствие фильтра по текущему Trading. Не считать snapshot текущих lotSize историческим фильтром.
4. Проверить единицы R=.056 цены сигнала, фактический short-stop12%, деньги и обе комиссии/проскальзывание. Parent netR и новая cost model различаются намеренно; сравнивать matched_nohedge_netR.
5. Проверить signs/timestamps funding, пропуски и стресс, proxy mark при отсутствии точного mark. Не называть неизвестный funding подтверждённым нулём.
6. Проверить H1 freeze в run44174225104 до corrected validation run44174898120, BH6 H2 и last40 отдельно, доступность≥180/200 контролей и day-block sign test. Коррелированные ±7д-контроли/режимы ограничивают интерпретацию p; вывод о прибыльности всё равно отрицательный.
7. Независимо суммировать ACTUAL_ROWS по variant/split и сравнить все цифры METRICS_ALL_VARIANTS.json; full включает purge, last40 перекрывает H2. DD реализованный, не MTM. Нельзя трактовать $5/R как исполнимый портфель55USDT.

Сохранённые результаты использовать повторно. Не пересчитывать BROAD224, LEVEL40, старые54 профиля, исходную подготовку путей или H1. Никаких изменений main/LIVE/ордера/ключи/VPN/Telegram/работающие сервисы. Для независимой проверки достаточно чтения опубликованных файлов и unit tests; повтор модели — только при обнаруженной конкретной ошибке.

Код:9100003c81d2b2c6b0bec0a49fcbb9653faded98. Commit исходных итогов:ca4f12935528d561dba9f9e605bd26bd1632e0fa. SHA256 полного JSON в FINAL_AUDIT.json. Кандидатов для бумажной фабрики нет.

Desktop Commander 0, Bybit-ключи 0, LIVE изменений 0.
