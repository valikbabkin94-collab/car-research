# Что ещё нужно

1. Новые безопасные экспорты законченных initial executions PUMP_FADE/OLEG_CLONE: source, signal_id, trade_id, symbol, side, strategy_sha, export_commit; список execution_id/time_ms/price/quantity. Не только касание лимитной цены свечой. Исторические исполнения24.11 могут использоваться для диагностики, но не добавляются задним числом в независимый forward.
2. Версия и параметры реально используемого менеджера ALT_CLONE/CAR_MANAGER, точная привязка к источникам, time-stamped stop/BE/partial/trailing transitions. Наличие manager-классов вGitHub не определяет активныйpolicy экземпляр. Без этого managed остаётся DATA_GAP_MANAGER_POLICY; обычная лестница не подставляется.
3. Новые1m/тики и funding/settlement marks периода наблюдения. Для execution внутри минуты и initial fills через несколько минут нужны более точные данные. В противном случае неоднозначность не исчезает.
4. Снимок версии установленной изолированной фабрики и хеши файлов. Пакет рассчитан на56cb2d569ba97ba417af68edbec4b54b4e2c3230: при несовпадении не перезаписывать установленную версию, сначала rebase/review. Установка и подключение daily-summary — только владельцем послеreview.
5. Для подтверждения наOLEG_CLONE — его самостоятельный ledger/будущие пары; наPUMP_FADE исторический результат не переносится. Покаforward в этой работе0, managed0.

Секреты/APIключи/IP/VPN/Telegram-сессии не требуются. Desktop/Remote и живые базы не используются.
