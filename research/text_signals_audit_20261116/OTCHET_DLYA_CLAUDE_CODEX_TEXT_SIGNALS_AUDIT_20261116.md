# Полный аудит текстовых сигналов —17.11.2026

методика 14.11 выбрасывала прибыльный формат — недостаточно данных: 27 сигналов без доступной свечи входа; для наиболее наполненного сочетания Whalesguide/политика не хватает минимум 29 дополнительных завершённых уникальных сигналов в последних40% до порога60; это не гарантирует PF≥1,3 и значимый BH.

## Выполнено по всей исходной выборке

Исходные374 записи сохранены. После исправления классификатора26 оказались не новыми сигналами,3—точными дубликатами. Все345 уникальных свежих сигналов включены в T1/T2/T3. Унаследованный cooldown6h удалён из исключений:33 затронутых записи досчитаны независимо от исхода, предыдущие результаты не пересчитывались и проверены на неизменность. Получено1122 строки для374×3,включая все отказы и пробелы.

SPECULANTKA не ожидалась. Мини-пилоты не повторялись. Старые/v2 исходы импортированы для сравнения,не пересчитывались. Отдельно сохранены реальные исполнения,1035 случайных по времени контрольных случаев,источники,хэши,границы периодов и поправкаBH.

## Итог по всем каналам вместе

|Политика|Завершено|WR%|PF|ΣR|$при$5риска|MaxDD,R|Rприfunding adverse|Rприfunding favourable|Неизвестныйfunding,n|
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|T1|314|67.5159|0.7883|-18.5471|-92.7354|25.8799|-18.8456|-18.2485|119|
|T2|312|50.6410|1.0680|8.6653|43.3264|19.3435|7.9527|9.3779|115|
|T3|318|66.9811|0.8052|-17.6642|-88.3211|25.8063|-17.9585|-17.3699|119|

Это сумма фиксированных R на сделку,не модель счёта с плечом или лимитами портфеля. T2 дал положительный суммарный результат,но PF≈1,068,просадка≈19,34R и доля трёх лучших сделок≈51,9% чистого результата. По зафиксированным порогам и независимому случайному контролю кандидатов нет.

## Funding и цены

По новому ТЗ неизвестный funding принят равным0,а не исключён из расчёта. В таблице явно указано число таких допущений. Реальные денежные платежи используются при полном покрытии архивом; при неполном покрытии whole-trade funding предполагается0. Чувствительность неизвестного funding:±0,01%за8h на entry notional с учётом остатка и длительности частичных выходов. Это сценарий,не восстановленный funding.

Сначала использован сохранённый checksummed1mкэш. Недостающие реальные и случайные окна запрошены в monthly/daily data.binance.vision,включая делистнутые инструменты. Bybit public linear kline опрошен без ключей;хост вернул HTTP403. Географическую блокировку не обходили. Поэтому27 уникальных записей со статусом «нет данных» по входу означают отсутствие доступных цен,а не доказанное отсутствие цены вообще. Ещё2 policy-строки T2 не имеют полного24hконтекста. Все эти строки сохранены в DATA_GAPS.csv и ALL_TRADES,не превращены в убытки/NOFILL.

Снимок ограничен17ноября00:00UTC;2 позицииT2 правосторонне цензурированы. Невалидные stop/targets и2 неопределённые авторские инструкции T1 тоже сохранены отдельно. Binance/Bybit окна не смешиваются внутри сделки. Комиссия0,055%на сторону,5bpsmarket slippage,SL-first,TPне в entrybar.

## Проверка ПРОЧЕЕ

На30 случайных постах ПРОЧЕЕ проведён просмотр полного нормализованного текста самимCodex. Найдена1явная торговая карточка,ошибочно отнесённая вOTHER из-за рекламногоfooter;правило исправлено доPnL. Остальные примеры включали новости,рекламу,результаты и условную аналитику. Это не независимая ручная сертификация всего парсера и не точная оценка доли пропущенных сделок по всем каналам. Ключи,seed и метки сохранены в OTHER_MANUAL_REVIEW_30.json.

|Канал|Посты|ПРОЧЕЕ|ДоляПРОЧЕЕ|
|---|---:|---:|---:|
|AltcoinDaily_signaI|2430|562|23.13%|
|BinanceKillersVipChannel|11194|5712|51.03%|
|Binance_Futures_Trades|800|0|0.00%|
|BitcoinBullet_official|539|342|63.45%|
|BullBearCrypto0|635|437|68.82%|
|Coin_Signals|788|416|52.79%|
|CryptoInnerCircle|800|641|80.12%|
|OldmanScalping|755|569|75.36%|
|RavenSignalsPro|641|379|59.13%|
|Teambuertrades|3|3|100.00%|
|TopCryptoFuturesSignals|800|557|69.62%|
|TradingGainX|778|353|45.37%|
|Whalesguide|796|427|53.64%|
|WolfxCrypto_VIP|671|101|15.05%|
|altsignals|795|524|65.91%|
|bitcoinbullets|799|564|70.59%|
|chainexsignals|634|109|17.19%|
|coin_sgnls_PRO|416|237|56.97%|
|coincodecap|800|513|64.12%|
|crusader_trades|2682|2429|90.57%|
|crypto_Winston|736|644|87.50%|
|crypto_signalsf|800|777|97.12%|
|cryptoclassics|702|596|84.90%|
|cryptoinsidebets|800|31|3.88%|
|cryptoroverytofficiaI|600|553|92.17%|
|cryptosignals0rg|7801|5116|65.58%|
|fatpigsignals|799|300|37.55%|
|fedrussianinsiders|800|763|95.38%|
|free_crypto_vip|800|6|0.75%|
|learn2tradectypto|800|331|41.38%|
|learn2tradenews|800|339|42.38%|
|main3commassignals|655|414|63.21%|
|ne_investor|11378|9768|85.85%|
|safe_academy|9672|8691|89.86%|
|sagesignals8|800|796|99.50%|
|tokenwhisperer_io|800|793|99.12%|
|traderosho|796|541|67.96%|
|universalcryptosignals|80|51|63.75%|
|wallstreetqueenofficial|782|594|75.96%|
|wolfoftrading|798|682|85.46%|
|wolfxsignals_freegroup|496|393|79.23%|
|EveningTrader|0|0|NA|
|Raven_signalst_pro|0|0|NA|
|astronomer_zero|0|0|NA|
|cryptoninjas_trading_ann|0|0|NA|

## Канал × старая методика /v2 /текстовые политики

В колонках: **n / PF / R**. Исторические выборки различаются:старый/v2 корпус имеет явные уровни,новый—кандидаты из исходных374. Это сравнение двух наборов,не изолированный причинный эффект смены выхода. Нулевоеn—нет оценки,не доказанный убыток. Полная CSV:COMPARISON_WIDE.csv;новая таблица сWR,$5/R,DD,стрессом иBH—TABLES.json.

|Канал|Набор|Политика|Половина1:n/PF/R|Половина2:n/PF/R|Последние40%:n/PF/R|
|---|---|---|---|---|---|
|AltcoinDaily_signaI|OLD|P4|NA|NA|NA|
|AltcoinDaily_signaI|OLD|P5|NA|NA|NA|
|AltcoinDaily_signaI|V2|P1|NA|NA|NA|
|AltcoinDaily_signaI|V2|P2|NA|NA|NA|
|AltcoinDaily_signaI|V2|P3|NA|NA|NA|
|AltcoinDaily_signaI|TEXT|T1|NA|NA|NA|
|AltcoinDaily_signaI|TEXT|T2|NA|NA|NA|
|AltcoinDaily_signaI|TEXT|T3|NA|NA|NA|
|BinanceKillersVipChannel|OLD|P4|101 / 0.864 / -1.048|310 / 0.614 / -31.997|109 / 0.868 / -2.851|
|BinanceKillersVipChannel|OLD|P5|101 / 1.225 / 5.254|310 / 0.724 / -42.429|109 / 0.851 / -7.113|
|BinanceKillersVipChannel|V2|P1|82 / 1.023 / 0.930|357 / 0.716 / -82.515|161 / 1.002 / 0.267|
|BinanceKillersVipChannel|V2|P2|104 / 1.070 / 0.657|399 / 0.603 / -40.732|184 / 0.672 / -13.968|
|BinanceKillersVipChannel|V2|P3|104 / 0.996 / -0.040|399 / 0.621 / -38.518|184 / 0.739 / -11.063|
|BinanceKillersVipChannel|TEXT|T1|1 / NA / 0.164|3 / 0.000 / -2.267|3 / 0.000 / -2.267|
|BinanceKillersVipChannel|TEXT|T2|1 / NA / 0.300|3 / 0.000 / -3.373|3 / 0.000 / -3.373|
|BinanceKillersVipChannel|TEXT|T3|1 / NA / 0.164|3 / 0.000 / -2.267|3 / 0.000 / -2.267|
|Binance_Futures_Trades|OLD|P4|NA|NA|NA|
|Binance_Futures_Trades|OLD|P5|NA|NA|NA|
|Binance_Futures_Trades|V2|P1|11 / 0.125 / -6.566|6 / 0.635 / -1.698|9 / 0.372 / -4.996|
|Binance_Futures_Trades|V2|P2|13 / 1.787 / 1.664|8 / 0.224 / -2.712|11 / 0.533 / -1.661|
|Binance_Futures_Trades|V2|P3|13 / 1.582 / 1.194|8 / 0.327 / -2.311|11 / 0.498 / -1.723|
|Binance_Futures_Trades|TEXT|T1|NA|NA|NA|
|Binance_Futures_Trades|TEXT|T2|NA|NA|NA|
|Binance_Futures_Trades|TEXT|T3|NA|NA|NA|
|BitcoinBullet_official|OLD|P4|21 / 1.197 / 0.540|39 / 0.751 / -1.906|22 / 0.854 / -0.753|
|BitcoinBullet_official|OLD|P5|21 / 0.693 / -2.318|39 / 0.986 / -0.199|22 / 0.893 / -1.023|
|BitcoinBullet_official|V2|P1|19 / 0.459 / -7.070|37 / 0.942 / -1.381|22 / 0.786 / -3.461|
|BitcoinBullet_official|V2|P2|19 / 1.657 / 1.523|37 / 1.405 / 2.486|22 / 1.572 / 2.181|
|BitcoinBullet_official|V2|P3|19 / 1.421 / 0.931|38 / 1.471 / 2.781|23 / 1.672 / 2.441|
|BitcoinBullet_official|TEXT|T1|NA|NA|NA|
|BitcoinBullet_official|TEXT|T2|NA|NA|NA|
|BitcoinBullet_official|TEXT|T3|NA|NA|NA|
|BullBearCrypto0|OLD|P4|NA|NA|NA|
|BullBearCrypto0|OLD|P5|NA|NA|NA|
|BullBearCrypto0|V2|P1|NA|NA|NA|
|BullBearCrypto0|V2|P2|NA|NA|NA|
|BullBearCrypto0|V2|P3|NA|NA|NA|
|BullBearCrypto0|TEXT|T1|NA|NA|NA|
|BullBearCrypto0|TEXT|T2|NA|NA|NA|
|BullBearCrypto0|TEXT|T3|NA|NA|NA|
|Coin_Signals|OLD|P4|NA|NA|NA|
|Coin_Signals|OLD|P5|NA|NA|NA|
|Coin_Signals|V2|P1|NA|NA|NA|
|Coin_Signals|V2|P2|NA|NA|NA|
|Coin_Signals|V2|P3|NA|NA|NA|
|Coin_Signals|TEXT|T1|1 / 0.000 / -0.315|1 / NA / 0.609|1 / NA / 0.609|
|Coin_Signals|TEXT|T2|1 / 0.000 / -0.358|NA|NA|
|Coin_Signals|TEXT|T3|1 / 0.000 / -0.315|1 / NA / 0.609|1 / NA / 0.609|
|CryptoInnerCircle|OLD|P4|NA|NA|NA|
|CryptoInnerCircle|OLD|P5|NA|NA|NA|
|CryptoInnerCircle|V2|P1|NA|NA|NA|
|CryptoInnerCircle|V2|P2|NA|NA|NA|
|CryptoInnerCircle|V2|P3|NA|NA|NA|
|CryptoInnerCircle|TEXT|T1|NA|NA|NA|
|CryptoInnerCircle|TEXT|T2|NA|NA|NA|
|CryptoInnerCircle|TEXT|T3|NA|NA|NA|
|EveningTrader|OLD|P4|NA|NA|NA|
|EveningTrader|OLD|P5|NA|NA|NA|
|EveningTrader|V2|P1|NA|NA|NA|
|EveningTrader|V2|P2|NA|NA|NA|
|EveningTrader|V2|P3|NA|NA|NA|
|EveningTrader|TEXT|T1|NA|NA|NA|
|EveningTrader|TEXT|T2|NA|NA|NA|
|EveningTrader|TEXT|T3|NA|NA|NA|
|OldmanScalping|OLD|P4|NA|NA|NA|
|OldmanScalping|OLD|P5|NA|NA|NA|
|OldmanScalping|V2|P1|NA|NA|NA|
|OldmanScalping|V2|P2|NA|NA|NA|
|OldmanScalping|V2|P3|NA|NA|NA|
|OldmanScalping|TEXT|T1|6 / 0.502 / -0.515|4 / 0.333 / -1.384|4 / 0.333 / -1.384|
|OldmanScalping|TEXT|T2|7 / 0.293 / -3.512|4 / 1.365 / 0.789|4 / 1.365 / 0.789|
|OldmanScalping|TEXT|T3|7 / 0.716 / -0.589|4 / 0.373 / -1.302|4 / 0.373 / -1.302|
|RavenSignalsPro|OLD|P4|NA|NA|NA|
|RavenSignalsPro|OLD|P5|NA|NA|NA|
|RavenSignalsPro|V2|P1|NA|NA|NA|
|RavenSignalsPro|V2|P2|NA|NA|NA|
|RavenSignalsPro|V2|P3|NA|NA|NA|
|RavenSignalsPro|TEXT|T1|NA|1 / NA / 0.386|1 / NA / 0.386|
|RavenSignalsPro|TEXT|T2|NA|1 / 0.000 / -1.025|1 / 0.000 / -1.025|
|RavenSignalsPro|TEXT|T3|NA|1 / NA / 0.386|1 / NA / 0.386|
|Raven_signalst_pro|OLD|P4|NA|NA|NA|
|Raven_signalst_pro|OLD|P5|NA|NA|NA|
|Raven_signalst_pro|V2|P1|NA|NA|NA|
|Raven_signalst_pro|V2|P2|NA|NA|NA|
|Raven_signalst_pro|V2|P3|NA|NA|NA|
|Raven_signalst_pro|TEXT|T1|NA|NA|NA|
|Raven_signalst_pro|TEXT|T2|NA|NA|NA|
|Raven_signalst_pro|TEXT|T3|NA|NA|NA|
|Teambuertrades|OLD|P4|NA|NA|NA|
|Teambuertrades|OLD|P5|NA|NA|NA|
|Teambuertrades|V2|P1|NA|NA|NA|
|Teambuertrades|V2|P2|NA|NA|NA|
|Teambuertrades|V2|P3|NA|NA|NA|
|Teambuertrades|TEXT|T1|NA|NA|NA|
|Teambuertrades|TEXT|T2|NA|NA|NA|
|Teambuertrades|TEXT|T3|NA|NA|NA|
|TopCryptoFuturesSignals|OLD|P4|NA|NA|NA|
|TopCryptoFuturesSignals|OLD|P5|NA|NA|NA|
|TopCryptoFuturesSignals|V2|P1|1 / NA / 0.971|NA|1 / NA / 0.971|
|TopCryptoFuturesSignals|V2|P2|1 / NA / 0.518|NA|1 / NA / 0.518|
|TopCryptoFuturesSignals|V2|P3|1 / NA / 0.464|NA|1 / NA / 0.464|
|TopCryptoFuturesSignals|TEXT|T1|2 / NA / 0.327|2 / NA / 0.769|2 / NA / 0.769|
|TopCryptoFuturesSignals|TEXT|T2|2 / NA / 2.855|2 / NA / 2.941|2 / NA / 2.941|
|TopCryptoFuturesSignals|TEXT|T3|2 / NA / 0.327|2 / NA / 1.211|2 / NA / 1.211|
|TradingGainX|OLD|P4|22 / 0.482 / -4.986|47 / 1.056 / 0.973|28 / 0.848 / -1.749|
|TradingGainX|OLD|P5|22 / 0.535 / -6.411|47 / 1.121 / 3.329|28 / 0.994 / -0.102|
|TradingGainX|V2|P1|21 / 0.665 / -5.621|52 / 0.055 / -51.667|29 / 0.000 / -28.788|
|TradingGainX|V2|P2|22 / 0.487 / -4.985|56 / 0.928 / -1.526|31 / 0.778 / -2.823|
|TradingGainX|V2|P3|22 / 0.466 / -5.173|56 / 1.003 / 0.064|31 / 1.016 / 0.210|
|TradingGainX|TEXT|T1|1 / 0.000 / -1.037|1 / 0.000 / -1.036|1 / 0.000 / -1.036|
|TradingGainX|TEXT|T2|1 / 0.000 / -1.024|1 / 0.000 / -1.053|1 / 0.000 / -1.053|
|TradingGainX|TEXT|T3|1 / 0.000 / -1.037|1 / 0.000 / -1.036|1 / 0.000 / -1.036|
|Whalesguide|OLD|P4|53 / 1.338 / 4.150|19 / 2.609 / 4.352|30 / 1.214 / 1.466|
|Whalesguide|OLD|P5|53 / 1.053 / 1.199|19 / 1.592 / 4.019|30 / 0.980 / -0.271|
|Whalesguide|V2|P1|55 / 1.249 / 9.671|19 / 1.567 / 7.138|30 / 1.183 / 4.034|
|Whalesguide|V2|P2|56 / 1.319 / 4.363|21 / 2.411 / 4.589|32 / 1.294 / 2.192|
|Whalesguide|V2|P3|56 / 1.319 / 4.362|21 / 2.342 / 4.365|32 / 1.385 / 2.870|
|Whalesguide|TEXT|T1|100 / 1.290 / 5.843|47 / 1.351 / 3.518|31 / 1.331 / 2.214|
|Whalesguide|TEXT|T2|100 / 1.252 / 9.201|45 / 1.565 / 6.076|29 / 2.048 / 5.016|
|Whalesguide|TEXT|T3|100 / 1.290 / 5.843|47 / 1.351 / 3.518|31 / 1.331 / 2.214|
|WolfxCrypto_VIP|OLD|P4|1 / 0.000 / -1.198|50 / 1.438 / 4.558|16 / 0.581 / -1.721|
|WolfxCrypto_VIP|OLD|P5|1 / 0.000 / -1.198|50 / 1.442 / 7.904|16 / 1.208 / 1.327|
|WolfxCrypto_VIP|V2|P1|1 / 0.000 / -1.334|67 / 1.555 / 14.174|25 / 1.069 / 0.808|
|WolfxCrypto_VIP|V2|P2|1 / 0.000 / -1.334|67 / 1.555 / 14.174|25 / 1.069 / 0.808|
|WolfxCrypto_VIP|V2|P3|1 / 0.000 / -1.334|67 / 1.555 / 14.174|25 / 1.069 / 0.808|
|WolfxCrypto_VIP|TEXT|T1|NA|NA|NA|
|WolfxCrypto_VIP|TEXT|T2|NA|NA|NA|
|WolfxCrypto_VIP|TEXT|T3|NA|NA|NA|
|altsignals|OLD|P4|NA|NA|NA|
|altsignals|OLD|P5|NA|NA|NA|
|altsignals|V2|P1|NA|NA|NA|
|altsignals|V2|P2|NA|NA|NA|
|altsignals|V2|P3|NA|NA|NA|
|altsignals|TEXT|T1|NA|NA|NA|
|altsignals|TEXT|T2|NA|NA|NA|
|altsignals|TEXT|T3|NA|NA|NA|
|astronomer_zero|OLD|P4|NA|NA|NA|
|astronomer_zero|OLD|P5|NA|NA|NA|
|astronomer_zero|V2|P1|NA|NA|NA|
|astronomer_zero|V2|P2|NA|NA|NA|
|astronomer_zero|V2|P3|NA|NA|NA|
|astronomer_zero|TEXT|T1|NA|NA|NA|
|astronomer_zero|TEXT|T2|NA|NA|NA|
|astronomer_zero|TEXT|T3|NA|NA|NA|
|bitcoinbullets|OLD|P4|NA|NA|NA|
|bitcoinbullets|OLD|P5|NA|NA|NA|
|bitcoinbullets|V2|P1|NA|NA|NA|
|bitcoinbullets|V2|P2|NA|NA|NA|
|bitcoinbullets|V2|P3|NA|NA|NA|
|bitcoinbullets|TEXT|T1|NA|NA|NA|
|bitcoinbullets|TEXT|T2|NA|NA|NA|
|bitcoinbullets|TEXT|T3|NA|NA|NA|
|chainexsignals|OLD|P4|NA|NA|NA|
|chainexsignals|OLD|P5|NA|NA|NA|
|chainexsignals|V2|P1|1 / 0.000 / -0.070|NA|1 / 0.000 / -0.070|
|chainexsignals|V2|P2|1 / NA / 0.109|NA|1 / NA / 0.109|
|chainexsignals|V2|P3|1 / NA / 0.287|NA|1 / NA / 0.287|
|chainexsignals|TEXT|T1|NA|NA|NA|
|chainexsignals|TEXT|T2|NA|NA|NA|
|chainexsignals|TEXT|T3|NA|NA|NA|
|coin_sgnls_PRO|OLD|P4|NA|NA|NA|
|coin_sgnls_PRO|OLD|P5|NA|NA|NA|
|coin_sgnls_PRO|V2|P1|12 / 0.634 / -4.422|8 / 0.720 / -1.541|5 / 0.138 / -3.725|
|coin_sgnls_PRO|V2|P2|12 / 0.375 / -5.559|8 / 0.586 / -0.971|5 / 0.334 / -0.770|
|coin_sgnls_PRO|V2|P3|12 / 0.392 / -5.408|8 / 0.575 / -0.944|5 / 0.352 / -0.669|
|coin_sgnls_PRO|TEXT|T1|2 / NA / 0.466|1 / 0.000 / -1.036|1 / 0.000 / -1.036|
|coin_sgnls_PRO|TEXT|T2|2 / 0.655 / -0.261|1 / 0.000 / -1.018|1 / 0.000 / -1.018|
|coin_sgnls_PRO|TEXT|T3|2 / 0.159 / -0.869|1 / 0.000 / -1.036|1 / 0.000 / -1.036|
|coincodecap|OLD|P4|NA|NA|NA|
|coincodecap|OLD|P5|NA|NA|NA|
|coincodecap|V2|P1|NA|NA|NA|
|coincodecap|V2|P2|NA|NA|NA|
|coincodecap|V2|P3|NA|NA|NA|
|coincodecap|TEXT|T1|2 / 2.466 / 0.283|3 / 0.788 / -0.068|3 / 0.788 / -0.068|
|coincodecap|TEXT|T2|2 / 6.285 / 1.182|4 / 4.338 / 1.615|4 / 4.338 / 1.615|
|coincodecap|TEXT|T3|2 / 2.466 / 0.283|4 / 2.565 / 0.501|4 / 2.565 / 0.501|
|crusader_trades|OLD|P4|NA|NA|NA|
|crusader_trades|OLD|P5|NA|NA|NA|
|crusader_trades|V2|P1|1 / 0.000 / -1.022|1 / NA / 1.797|1 / NA / 1.797|
|crusader_trades|V2|P2|1 / NA / 0.432|1 / NA / 1.331|1 / NA / 1.331|
|crusader_trades|V2|P3|1 / NA / 0.886|1 / NA / 0.866|1 / NA / 0.866|
|crusader_trades|TEXT|T1|1 / NA / 0.165|NA|NA|
|crusader_trades|TEXT|T2|1 / 0.000 / -1.057|NA|NA|
|crusader_trades|TEXT|T3|1 / NA / 0.165|NA|NA|
|crypto_Winston|OLD|P4|NA|NA|NA|
|crypto_Winston|OLD|P5|NA|NA|NA|
|crypto_Winston|V2|P1|1 / 0.000 / -1.010|NA|NA|
|crypto_Winston|V2|P2|2 / NA / 0.117|NA|1 / NA / 0.107|
|crypto_Winston|V2|P3|2 / NA / 0.251|NA|1 / NA / 0.221|
|crypto_Winston|TEXT|T1|NA|NA|NA|
|crypto_Winston|TEXT|T2|NA|NA|NA|
|crypto_Winston|TEXT|T3|NA|NA|NA|
|crypto_signalsf|OLD|P4|NA|NA|NA|
|crypto_signalsf|OLD|P5|NA|NA|NA|
|crypto_signalsf|V2|P1|NA|NA|NA|
|crypto_signalsf|V2|P2|NA|NA|NA|
|crypto_signalsf|V2|P3|NA|NA|NA|
|crypto_signalsf|TEXT|T1|NA|NA|NA|
|crypto_signalsf|TEXT|T2|NA|NA|NA|
|crypto_signalsf|TEXT|T3|NA|NA|NA|
|cryptoclassics|OLD|P4|NA|NA|NA|
|cryptoclassics|OLD|P5|NA|NA|NA|
|cryptoclassics|V2|P1|NA|NA|NA|
|cryptoclassics|V2|P2|NA|NA|NA|
|cryptoclassics|V2|P3|NA|NA|NA|
|cryptoclassics|TEXT|T1|NA|NA|NA|
|cryptoclassics|TEXT|T2|NA|NA|NA|
|cryptoclassics|TEXT|T3|NA|NA|NA|
|cryptoinsidebets|OLD|P4|NA|NA|NA|
|cryptoinsidebets|OLD|P5|NA|NA|NA|
|cryptoinsidebets|V2|P1|NA|NA|NA|
|cryptoinsidebets|V2|P2|NA|NA|NA|
|cryptoinsidebets|V2|P3|NA|NA|NA|
|cryptoinsidebets|TEXT|T1|NA|NA|NA|
|cryptoinsidebets|TEXT|T2|NA|NA|NA|
|cryptoinsidebets|TEXT|T3|NA|NA|NA|
|cryptoninjas_trading_ann|OLD|P4|NA|NA|NA|
|cryptoninjas_trading_ann|OLD|P5|NA|NA|NA|
|cryptoninjas_trading_ann|V2|P1|NA|NA|NA|
|cryptoninjas_trading_ann|V2|P2|NA|NA|NA|
|cryptoninjas_trading_ann|V2|P3|NA|NA|NA|
|cryptoninjas_trading_ann|TEXT|T1|NA|NA|NA|
|cryptoninjas_trading_ann|TEXT|T2|NA|NA|NA|
|cryptoninjas_trading_ann|TEXT|T3|NA|NA|NA|
|cryptoroverytofficiaI|OLD|P4|NA|NA|NA|
|cryptoroverytofficiaI|OLD|P5|NA|NA|NA|
|cryptoroverytofficiaI|V2|P1|NA|NA|NA|
|cryptoroverytofficiaI|V2|P2|NA|NA|NA|
|cryptoroverytofficiaI|V2|P3|NA|NA|NA|
|cryptoroverytofficiaI|TEXT|T1|NA|NA|NA|
|cryptoroverytofficiaI|TEXT|T2|NA|NA|NA|
|cryptoroverytofficiaI|TEXT|T3|NA|NA|NA|
|cryptosignals0rg|OLD|P4|867 / 0.698 / -44.957|65 / 1.113 / 4.144|340 / 0.767 / -21.556|
|cryptosignals0rg|OLD|P5|867 / 0.888 / -46.252|65 / 0.929 / -3.290|340 / 0.866 / -24.650|
|cryptosignals0rg|V2|P1|894 / 1.038 / 26.918|78 / 0.463 / -47.855|360 / 0.852 / -46.642|
|cryptosignals0rg|V2|P2|900 / 0.677 / -54.073|81 / 0.508 / -44.370|367 / 0.508 / -75.686|
|cryptosignals0rg|V2|P3|900 / 0.592 / -63.913|81 / 0.508 / -44.370|367 / 0.484 / -77.632|
|cryptosignals0rg|TEXT|T1|3 / 0.513 / -0.507|3 / 0.128 / -1.069|2 / 0.854 / -0.027|
|cryptosignals0rg|TEXT|T2|3 / 0.923 / -0.017|3 / 0.000 / -2.250|2 / 0.000 / -1.201|
|cryptosignals0rg|TEXT|T3|3 / 0.513 / -0.507|3 / 0.128 / -1.069|2 / 0.854 / -0.027|
|fatpigsignals|OLD|P4|NA|NA|NA|
|fatpigsignals|OLD|P5|NA|NA|NA|
|fatpigsignals|V2|P1|NA|NA|NA|
|fatpigsignals|V2|P2|NA|NA|NA|
|fatpigsignals|V2|P3|NA|NA|NA|
|fatpigsignals|TEXT|T1|NA|NA|NA|
|fatpigsignals|TEXT|T2|NA|NA|NA|
|fatpigsignals|TEXT|T3|NA|NA|NA|
|fedrussianinsiders|OLD|P4|NA|NA|NA|
|fedrussianinsiders|OLD|P5|NA|NA|NA|
|fedrussianinsiders|V2|P1|1 / 0.000 / -1.070|NA|NA|
|fedrussianinsiders|V2|P2|1 / 0.000 / -0.055|NA|NA|
|fedrussianinsiders|V2|P3|1 / 0.000 / -0.039|NA|NA|
|fedrussianinsiders|TEXT|T1|NA|NA|NA|
|fedrussianinsiders|TEXT|T2|NA|NA|NA|
|fedrussianinsiders|TEXT|T3|NA|NA|NA|
|free_crypto_vip|OLD|P4|47 / 0.237 / -6.451|39 / 0.150 / -8.579|34 / 0.104 / -8.691|
|free_crypto_vip|OLD|P5|47 / 0.401 / -11.321|39 / 0.552 / -6.863|34 / 0.488 / -7.090|
|free_crypto_vip|V2|P1|51 / 0.607 / -13.617|38 / 0.749 / -6.577|33 / 0.832 / -3.708|
|free_crypto_vip|V2|P2|51 / 0.478 / -7.198|40 / 0.386 / -7.195|35 / 0.333 / -7.084|
|free_crypto_vip|V2|P3|51 / 0.474 / -7.176|40 / 0.385 / -7.180|35 / 0.371 / -6.655|
|free_crypto_vip|TEXT|T1|6 / 0.949 / -0.053|2 / NA / 1.217|2 / NA / 1.217|
|free_crypto_vip|TEXT|T2|6 / 1.267 / 0.544|2 / NA / 2.849|2 / NA / 2.849|
|free_crypto_vip|TEXT|T3|6 / 0.949 / -0.053|2 / NA / 1.217|2 / NA / 1.217|
|learn2tradectypto|OLD|P4|25 / 0.963 / -0.575|18 / 0.598 / -4.669|19 / 0.851 / -1.727|
|learn2tradectypto|OLD|P5|25 / 0.925 / -1.367|18 / 0.457 / -7.540|19 / 0.669 / -4.598|
|learn2tradectypto|V2|P1|32 / 1.231 / 4.860|20 / 0.997 / -0.035|22 / 1.334 / 4.543|
|learn2tradectypto|V2|P2|32 / 0.994 / -0.120|20 / 0.923 / -1.046|22 / 1.260 / 3.533|
|learn2tradectypto|V2|P3|32 / 0.997 / -0.056|20 / 0.849 / -2.057|22 / 1.185 / 2.522|
|learn2tradectypto|TEXT|T1|1 / 0.000 / -0.611|1 / 0.000 / -0.395|1 / 0.000 / -0.395|
|learn2tradectypto|TEXT|T2|1 / 0.000 / -0.434|1 / 0.000 / -1.081|1 / 0.000 / -1.081|
|learn2tradectypto|TEXT|T3|1 / 0.000 / -0.611|1 / 0.000 / -0.395|1 / 0.000 / -0.395|
|learn2tradenews|OLD|P4|21 / 0.707 / -4.919|14 / 0.558 / -4.866|14 / 0.558 / -4.866|
|learn2tradenews|OLD|P5|21 / 0.550 / -9.594|14 / 0.310 / -8.955|14 / 0.310 / -8.955|
|learn2tradenews|V2|P1|27 / 0.645 / -8.641|13 / 0.326 / -7.425|14 / 0.470 / -5.835|
|learn2tradenews|V2|P2|27 / 0.691 / -6.887|13 / 0.254 / -8.221|14 / 0.398 / -6.631|
|learn2tradenews|V2|P3|27 / 0.679 / -7.135|13 / 0.264 / -8.102|14 / 0.409 / -6.512|
|learn2tradenews|TEXT|T1|NA|NA|NA|
|learn2tradenews|TEXT|T2|NA|NA|NA|
|learn2tradenews|TEXT|T3|NA|NA|NA|
|main3commassignals|OLD|P4|NA|NA|NA|
|main3commassignals|OLD|P5|NA|NA|NA|
|main3commassignals|V2|P1|10 / 0.277 / -7.885|29 / 0.198 / -22.844|17 / 0.036 / -18.836|
|main3commassignals|V2|P2|10 / 0.590 / -2.091|32 / 0.356 / -11.218|18 / 0.181 / -9.701|
|main3commassignals|V2|P3|10 / 0.576 / -2.083|32 / 0.581 / -7.181|18 / 0.459 / -6.369|
|main3commassignals|TEXT|T1|NA|NA|NA|
|main3commassignals|TEXT|T2|NA|NA|NA|
|main3commassignals|TEXT|T3|NA|NA|NA|
|ne_investor|OLD|P4|NA|NA|NA|
|ne_investor|OLD|P5|NA|NA|NA|
|ne_investor|V2|P1|NA|1 / 0.000 / -1.163|1 / 0.000 / -1.163|
|ne_investor|V2|P2|NA|1 / 0.000 / -1.163|1 / 0.000 / -1.163|
|ne_investor|V2|P3|NA|1 / 0.000 / -1.163|1 / 0.000 / -1.163|
|ne_investor|TEXT|T1|4 / 0.749 / -0.520|7 / 0.605 / -1.006|7 / 0.605 / -1.006|
|ne_investor|TEXT|T2|4 / 1.023 / 0.047|8 / 1.221 / 0.597|8 / 1.221 / 0.597|
|ne_investor|TEXT|T3|4 / 0.587 / -0.856|8 / 0.844 / -0.397|8 / 0.844 / -0.397|
|safe_academy|OLD|P4|66 / 0.628 / -9.007|31 / 1.113 / 1.266|37 / 1.047 / 0.579|
|safe_academy|OLD|P5|66 / 0.670 / -11.732|31 / 0.614 / -7.060|37 / 0.558 / -9.334|
|safe_academy|V2|P1|63 / 0.705 / -12.560|33 / 0.591 / -11.043|38 / 0.599 / -12.106|
|safe_academy|V2|P2|68 / 0.478 / -16.858|34 / 0.561 / -6.613|40 / 0.525 / -8.153|
|safe_academy|V2|P3|68 / 0.493 / -16.217|34 / 0.693 / -4.616|40 / 0.658 / -5.852|
|safe_academy|TEXT|T1|23 / 0.405 / -6.213|64 / 0.398 / -14.935|51 / 0.393 / -11.402|
|safe_academy|TEXT|T2|23 / 0.313 / -11.087|62 / 1.147 / 4.049|50 / 1.085 / 1.936|
|safe_academy|TEXT|T3|23 / 0.367 / -6.613|65 / 0.466 / -13.779|52 / 0.483 / -10.247|
|sagesignals8|OLD|P4|NA|NA|NA|
|sagesignals8|OLD|P5|NA|NA|NA|
|sagesignals8|V2|P1|NA|NA|NA|
|sagesignals8|V2|P2|NA|NA|NA|
|sagesignals8|V2|P3|NA|NA|NA|
|sagesignals8|TEXT|T1|NA|NA|NA|
|sagesignals8|TEXT|T2|NA|NA|NA|
|sagesignals8|TEXT|T3|NA|NA|NA|
|tokenwhisperer_io|OLD|P4|NA|NA|NA|
|tokenwhisperer_io|OLD|P5|NA|NA|NA|
|tokenwhisperer_io|V2|P1|NA|NA|NA|
|tokenwhisperer_io|V2|P2|NA|NA|NA|
|tokenwhisperer_io|V2|P3|NA|NA|NA|
|tokenwhisperer_io|TEXT|T1|NA|NA|NA|
|tokenwhisperer_io|TEXT|T2|NA|NA|NA|
|tokenwhisperer_io|TEXT|T3|NA|NA|NA|
|traderosho|OLD|P4|NA|NA|NA|
|traderosho|OLD|P5|NA|NA|NA|
|traderosho|V2|P1|NA|NA|NA|
|traderosho|V2|P2|NA|NA|NA|
|traderosho|V2|P3|NA|NA|NA|
|traderosho|TEXT|T1|8 / 0.769 / -0.118|12 / 1.755 / 1.825|9 / 1.475 / 0.988|
|traderosho|TEXT|T2|8 / 0.261 / -2.907|12 / 3.207 / 7.143|9 / 3.612 / 5.575|
|traderosho|TEXT|T3|8 / 1.106 / 0.053|12 / 1.755 / 1.825|9 / 1.475 / 0.988|
|universalcryptosignals|OLD|P4|NA|NA|NA|
|universalcryptosignals|OLD|P5|NA|NA|NA|
|universalcryptosignals|V2|P1|NA|NA|NA|
|universalcryptosignals|V2|P2|NA|NA|NA|
|universalcryptosignals|V2|P3|NA|NA|NA|
|universalcryptosignals|TEXT|T1|NA|NA|NA|
|universalcryptosignals|TEXT|T2|NA|NA|NA|
|universalcryptosignals|TEXT|T3|NA|NA|NA|
|wallstreetqueenofficial|OLD|P4|NA|NA|NA|
|wallstreetqueenofficial|OLD|P5|NA|NA|NA|
|wallstreetqueenofficial|V2|P1|NA|NA|NA|
|wallstreetqueenofficial|V2|P2|NA|NA|NA|
|wallstreetqueenofficial|V2|P3|NA|NA|NA|
|wallstreetqueenofficial|TEXT|T1|1 / 0.000 / -1.035|NA|NA|
|wallstreetqueenofficial|TEXT|T2|1 / 0.000 / -1.064|NA|NA|
|wallstreetqueenofficial|TEXT|T3|1 / 0.000 / -1.035|NA|NA|
|wolfoftrading|OLD|P4|NA|NA|NA|
|wolfoftrading|OLD|P5|NA|NA|NA|
|wolfoftrading|V2|P1|4 / 3.631 / 5.646|5 / 0.000 / -5.240|4 / 0.000 / -4.217|
|wolfoftrading|V2|P2|5 / 1.577 / 0.635|6 / 0.058 / -4.935|5 / 0.072 / -3.912|
|wolfoftrading|V2|P3|5 / 1.428 / 0.471|6 / 0.128 / -4.568|5 / 0.159 / -3.544|
|wolfoftrading|TEXT|T1|NA|NA|NA|
|wolfoftrading|TEXT|T2|NA|NA|NA|
|wolfoftrading|TEXT|T3|NA|NA|NA|
|wolfxsignals_freegroup|OLD|P4|NA|NA|NA|
|wolfxsignals_freegroup|OLD|P5|NA|NA|NA|
|wolfxsignals_freegroup|V2|P1|NA|NA|NA|
|wolfxsignals_freegroup|V2|P2|NA|NA|NA|
|wolfxsignals_freegroup|V2|P3|NA|NA|NA|
|wolfxsignals_freegroup|TEXT|T1|NA|NA|NA|
|wolfxsignals_freegroup|TEXT|T2|NA|NA|NA|
|wolfxsignals_freegroup|TEXT|T3|NA|NA|NA|

## Контроль,устойчивость и сколько данных не хватает

Границы половин и последних40% определены по датам всех исходных374 канальных записей,не по завершившимся прибыльным сделкам. Последние40% пересекаются со второй половиной,это не два независимых будущих теста. На каждую активную запись задано одно случайное время той же монеты/стороны в той же календарной половине; времена старых контрольных случаев сохранены при досчёте33.

Для разностей фактических и случайных R выполнены4095 парных перестановок поUTCдням;это не4095новых переборов входа. При парном покрытии<95%p=1,пропуски контроля не удаляются тайно. BH по45×3=135комбинациям в каждом срезе,неизвестныеp=1. Все скорректированныеq=1:статистически подтверждённого превосходства не получено,неполное покрытие контроля ограничивает силу вывода.

Минимальный дефицит по наиболее наполненному Whalesguide/T1илиT3:первая половина0,вторая13,последние40%29 до60 в каждом срезе. Так как последний срез входит во вторую половину,нижняя граница—29 дополнительных уникальных завершённых наблюдений,не42. Нужны именно наблюдения нужного среза/расширение корпуса,а не произвольные будущие сделки. У остальных сочетаний свои дефициты в SAMPLE_SHORTFALLS.json. Даже заполнение этогоn не гарантирует PF≥1,3/BH.

## Ограничения и итог

Редакции,VIP,удалённые посты,изображения,идентичность авторов внутри канала и фактическое исполнение неизвестны. T1 использует только однозначно распознанные обновления:отсутствие распознанного действия не доказывает отсутствие сопровождения. Неопределённая доля не подставляется,такой исход не считается известным авторским PnL. Данные зеркал и ликвидность прокси не доказывают точное исполнениеBybit.

методика 14.11 выбрасывала прибыльный формат — недостаточно данных: 27 сигналов без доступной свечи входа; для наиболее наполненного сочетания Whalesguide/политика не хватает минимум 29 дополнительных завершённых уникальных сигналов в последних40% до порога60; это не гарантирует PF≥1,3 и значимый BH.

FULL_PAPER_CANDIDATES.json пустой. Предложений установки вPR591 нет,main/торговые конфигурации не изменены. Сохранены исходы всех исходных374 и случайный контроль;другие исследования и мини-пилоты не запускались.

## ПРОСТЫМИ СЛОВАМИ ДЛЯ ВЛАДЕЛЬЦА

Полный проход сделан. T2 остался немного в плюсе в общей сумме,но это не устойчивая доказанная стратегия;T1 иT3 убыточны в этой модели. Одного хорошего пилота было недостаточно. Неизвестныйfunding теперь учтён по заданному допущению,а недоступные цены не выкинуты из реестра. Оснований объявить пропущенный формат стабильно прибыльным или запускать торговлю нет.

Desktop Commander 0, Telegram-сессии 0, Bybit-ключи 0, LIVE изменений 0
