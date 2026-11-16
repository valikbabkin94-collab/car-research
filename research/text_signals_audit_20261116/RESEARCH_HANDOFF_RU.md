# Handoff: незавершённый text signals audit

Ветка research/text-signals-audit. Не путать source-forensics с PnL: новых T1–T3исходов НЕТ. SPECULANTKA private branch404,политикиT1–T4 не проверены. Примеры задания толькоtests.

SOURCE_COVERAGE/CLASSIFIED_POSTS/REVIEW_PACK — классификация69451поста. V0ошибки сохранены, V1только provisional:2383SIGNAL,459missing parsed levels,374доdedup. Нераспознанные уровни не означают отсутствующие. ДоPnL надо установить precision иразделить условные/рекламные/прошедшие посты. Не запускать финансовый перебор на нынешнем черновом классификаторе. Pack120примеров требует независимой проверки,7юнит-тестов не доказывают качество.

Для восстановления:normalize_sources.py читает старые parsed_posts и частный кэш нормализованных posts v2;если кэша нет,авторизованно восстановить толькоstudy_input posts из data/tg-mirrors-20261114 commitbf1211f617c1d0a9c086c67d97917e070bcfda0f сSHA-проверкой;HTML не распаковывать. Источники v2 и условия зеркал задокументированы в research/channels-audit-v2,commit99c7f56ce98355abfd6e70610b296f09d4b02f4d. Public содержит только очищенные фрагменты и формальные поля,без rawIDs/имён/ссылок.

Дальше продолжить работу по протоколу без старого replay:verify120cases,недостающиеуровниvsparsererror,7дlinks,дедуп/cooldown;получить SPECULANTKA export;зафиксироватьполитики/engineSHA до PnL. Реальные funding и случайное время на техжемонетах обязательны. T4 проценты не переводить вR/долларыи не считать строгой верхнейграницей. Не писать ДА/НЕТ о прибыльности без результата. Paper candidates[].Ничего не установлено,PR591/mainне менялись.

Desktop Commander 0, Telegram-сессии 0, Bybit-ключи 0, LIVE изменений 0
