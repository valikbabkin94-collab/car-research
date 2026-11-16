# Telegram Channels Audit v2 — архивный этап, 16.11.2026

## Главный результат

Прежний разбор не доказывал убыточность всех 45 каналов: ценовые исходы тогда имелись только для 10 каналов. Новые политики действительно меняют результаты отдельных каналов. Однако ни одна проверенная политика не прошла зафиксированные исторические требования n≥60 и PF≥1,3 в каждой половине и последних 40%; настоящий forward ещё не начат. Устойчивая прибыльность не доказана, рекомендаций в PR #591 нет.

Глобальный ответ «методика занижала / не занижала» — **NOT_ESTABLISHED**. На некоторых одинаковых подвыборках старые M2/M3 дают меньший результат, на других — больший. P1 меняет одновременно момент входа, выходы и издержки; нельзя приписывать всю разницу сопровождению автора.

## Что реально выполнено

Реестр содержит 45 каналов; прочитаны только нормализованные посты из сохранённой GitHub-ветки. Всего 69451 пост, 2489 полный исходный сигнал до 14.11.2026 00:00 UTC. Полные сигналы распознаны для 20 каналов; это не означает, что остальные не публикуют пригодные сделки — другие форматы, изображения и скрытая история не восстановлены.

Связанные обновления есть у 351 сигналов; явные CLOSE/BE/STOP — у 116. TP-reached учитывается как заявление, не как команда или доказанное исполнение. Отсутствующая доля закрытия не подставлялась. После проверки качества 76 условных закрытых траекторий исключены из строгого P1 независимо от знака доходности; они сохранены отдельно.

После адресного продления: P1 — {'TRADE': 2051, 'DATA_GAP_ENTRY': 143, 'REJECTED_MARKET_GEOMETRY_OR_STALE_TARGET': 182, 'UNRESOLVED_AUTHOR_LOG': 76, 'CENSORED_ASOF': 36, 'CENSORED_NEEDS_EXTENSION': 1}. Полностью закрытая общая выборка пяти политик — 1718 сигналов. Лишь 7 закрытых P1 содержат исполненный авторский CLOSE; нельзя называть всю остальную модель полной реконструкцией реальной торговли автора.

Продолжены только 38 ранее незавершённых случаев, получено 26 новых завершённых исходов. Все существовавшие закрытые строки и P4/P5 проверены на неизменность. Свечи уже готовых случаев не пересчитывались. Реестр исходных архивов и SHA сохранён; недостающие месяцы скачивались адресно.

## Политики и издержки

- P1: market в первую полную минуту после поста; явные связанные команды автора, иначе SL/последний TP. Нет принудительного закрытия через 24 часа или 7 суток.
- P2: тот же market; 50% TP1, остаток с BE до TP2. При единственном TP — всё на TP1.
- P3: тот же market, вся позиция на TP1.
- P4/P5: сохранённые M2/M3, без нового replay: limit/TTL и старые доли/тайм-ауты.

Все новые результаты учитывают комиссию 0,21% от entry notional за круг и стресс slippage 5 bps на рыночных исполнениях. У legacy этого дополнительного slippage не было; это ещё одно различие сравнения. Все результаты **EX_FUNDING**. Это Binance USDT-M 1m proxy, не доказанное Bybit execution. $5/R — арифметика фиксированного риска, не прогноз заработка или счёт с плечом.

## Несколько конкретных наблюдений на MATCHED5

|Канал и политика|n|WR%|PF|R|$ при $5/R|DD, R|
|---|---:|---:|---:|---:|---:|---:|
|Whalesguide P1|70|34.286|1.367|17.728|88.641|10.861|
|Whalesguide P4|70|72.857|1.651|9.072|45.358|3.707|
|WolfxCrypto_VIP P3|51|64.706|1.715|13.815|69.077|7.890|
|WolfxCrypto_VIP P4|51|56.863|1.290|3.360|16.801|3.049|
|BitcoinBullet_official P2|53|62.264|1.420|3.532|17.661|2.921|
|BitcoinBullet_official P4|53|73.585|0.905|-0.934|-4.672|4.627|
|BinanceKillersVipChannel P1|357|13.165|0.614|-104.374|-521.868|136.424|
|BinanceKillersVipChannel P4|357|63.305|0.655|-26.020|-130.099|28.760|

Это описательные наблюдения, не отбор победителей для торговли. Wolfx P1/P2/P3 здесь совпадают из-за структуры целей, поэтому три одинаковых результата не являются тремя независимыми подтверждениями. У Whalesguide в календарных частях matched5 только 51 и 19 сделок, у Wolfx — 1 и 50, у BitcoinBullet — 19 и 34. Порог размера выборки не выполнен.

## Полный реестр и покрытие

|Канал|Постов|Полных сигналов|Связанное обновление|Явное действие|Зеркало|
|---|---:|---:|---:|---:|---|
|AltcoinDaily_signaI|2430|0|0|0|MIRROR_END|
|BinanceKillersVipChannel|11194|541|172|83|MIRROR_END|
|Binance_Futures_Trades|800|28|2|0|PAGE_LIMIT|
|BitcoinBullet_official|539|67|2|1|PAGE_LIMIT|
|BullBearCrypto0|635|0|0|0|PAGE_LIMIT|
|Coin_Signals|788|0|0|0|PAGE_LIMIT|
|CryptoInnerCircle|800|0|0|0|PAGE_LIMIT|
|EveningTrader|0|0|0|0|DATA_BLOCKED|
|OldmanScalping|755|0|0|0|PAGE_LIMIT|
|RavenSignalsPro|641|0|0|0|PAGE_LIMIT|
|Raven_signalst_pro|0|0|0|0|DATA_BLOCKED|
|Teambuertrades|3|0|0|0|MIRROR_END|
|TopCryptoFuturesSignals|800|1|0|0|PAGE_LIMIT|
|TradingGainX|778|79|40|8|PAGE_LIMIT|
|Whalesguide|796|81|2|0|PAGE_LIMIT|
|WolfxCrypto_VIP|671|76|1|1|PAGE_LIMIT|
|altsignals|795|0|0|0|PAGE_LIMIT|
|astronomer_zero|0|0|0|0|DATA_BLOCKED|
|bitcoinbullets|799|0|0|0|PAGE_LIMIT|
|chainexsignals|634|1|1|1|MIRROR_END|
|coin_sgnls_PRO|416|45|2|0|MIRROR_END|
|coincodecap|800|0|0|0|PAGE_LIMIT|
|crusader_trades|2682|2|0|0|MIRROR_END|
|crypto_Winston|736|2|0|0|PAGE_LIMIT|
|crypto_signalsf|800|0|0|0|PAGE_LIMIT|
|cryptoclassics|702|0|0|0|PAGE_LIMIT|
|cryptoinsidebets|800|0|0|0|PAGE_LIMIT|
|cryptoninjas_trading_ann|0|0|0|0|DATA_BLOCKED|
|cryptoroverytofficiaI|600|0|0|0|PAGE_LIMIT|
|cryptosignals0rg|7801|1121|59|3|DATA_BLOCKED|
|fatpigsignals|799|0|0|0|PAGE_LIMIT|
|fedrussianinsiders|800|4|2|0|PAGE_LIMIT|
|free_crypto_vip|800|96|6|5|PAGE_LIMIT|
|learn2tradectypto|800|86|11|2|PAGE_LIMIT|
|learn2tradenews|800|74|8|4|PAGE_LIMIT|
|main3commassignals|655|44|19|5|PAGE_LIMIT|
|ne_investor|11378|2|2|1|MIRROR_END|
|safe_academy|9672|127|19|2|MIRROR_END|
|sagesignals8|800|0|0|0|PAGE_LIMIT|
|tokenwhisperer_io|800|0|0|0|PAGE_LIMIT|
|traderosho|796|0|0|0|PAGE_LIMIT|
|universalcryptosignals|80|0|0|0|DATA_BLOCKED|
|wallstreetqueenofficial|782|0|0|0|PAGE_LIMIT|
|wolfoftrading|798|12|3|0|PAGE_LIMIT|
|wolfxsignals_freegroup|496|0|0|0|PAGE_LIMIT|

## Все каналы × пять политик на одинаковом MATCHED5

В каждой тройке календарных колонок указано **n / PF / R**. n=0 показано как NA, это отсутствие результата, не доказанный убыток. В [TABLES.csv](RESULTS/TABLES.csv) и [TABLES.json](RESULTS/TABLES.json) сохранены все 3375 строк: AVAILABLE, MATCHED5, чувствительность без видимых редакций × все периоды × пять политик. AVAILABLE содержит дополнительные исполнения вне общей старой выборки и не предназначен для наивного сравнения разных n.

|Канал|P|n ALL|WR%|PF ALL|R ALL|$5/R|CAL H1: n/PF/R|CAL H2: n/PF/R|Исторические40%: n/PF/R|Новые посты|
|---|---|---:|---:|---:|---:|---:|---|---|---|---|
|AltcoinDaily_signaI|P1|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|AltcoinDaily_signaI|P2|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|AltcoinDaily_signaI|P3|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|AltcoinDaily_signaI|P4|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|AltcoinDaily_signaI|P5|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|BinanceKillersVipChannel|P1|357|13.165|0.614|-104.374|-521.868|80 / 0.919 / -3.193|277 / 0.562 / -101.181|96 / 0.764 / -19.286|NOT_STARTED|
|BinanceKillersVipChannel|P2|357|69.468|0.537|-41.278|-206.388|80 / 0.900 / -0.837|277 / 0.500 / -40.441|96 / 0.431 / -20.047|NOT_STARTED|
|BinanceKillersVipChannel|P3|357|75.070|0.555|-39.383|-196.915|80 / 0.867 / -1.107|277 / 0.522 / -38.276|96 / 0.461 / -18.990|NOT_STARTED|
|BinanceKillersVipChannel|P4|357|63.305|0.655|-26.020|-130.099|80 / 0.745 / -1.740|277 / 0.647 / -24.280|96 / 0.798 / -3.997|NOT_STARTED|
|BinanceKillersVipChannel|P5|357|41.737|0.753|-38.313|-191.566|80 / 1.073 / 1.539|277 / 0.703 / -39.852|96 / 0.763 / -10.487|NOT_STARTED|
|Binance_Futures_Trades|P1|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|Binance_Futures_Trades|P2|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|Binance_Futures_Trades|P3|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|Binance_Futures_Trades|P4|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|Binance_Futures_Trades|P5|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|BitcoinBullet_official|P1|53|41.509|0.783|-7.482|-37.408|19 / 0.459 / -7.070|34 / 0.981 / -0.411|19 / 0.820 / -2.492|NOT_STARTED|
|BitcoinBullet_official|P2|53|62.264|1.420|3.532|17.661|19 / 1.657 / 1.523|34 / 1.329 / 2.009|19 / 1.452 / 1.704|NOT_STARTED|
|BitcoinBullet_official|P3|53|75.472|1.373|3.023|15.116|19 / 1.421 / 0.931|34 / 1.354 / 2.092|19 / 1.482 / 1.752|NOT_STARTED|
|BitcoinBullet_official|P4|53|73.585|0.905|-0.934|-4.672|19 / 1.183 / 0.501|34 / 0.799 / -1.435|19 / 0.949 / -0.237|NOT_STARTED|
|BitcoinBullet_official|P5|53|50.943|0.911|-1.721|-8.607|19 / 0.690 / -2.083|34 / 1.029 / 0.362|19 / 0.910 / -0.771|NOT_STARTED|
|BullBearCrypto0|P1|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|BullBearCrypto0|P2|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|BullBearCrypto0|P3|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|BullBearCrypto0|P4|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|BullBearCrypto0|P5|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|Coin_Signals|P1|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|Coin_Signals|P2|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|Coin_Signals|P3|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|Coin_Signals|P4|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|Coin_Signals|P5|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|CryptoInnerCircle|P1|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|CryptoInnerCircle|P2|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|CryptoInnerCircle|P3|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|CryptoInnerCircle|P4|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|CryptoInnerCircle|P5|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|EveningTrader|P1|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|EveningTrader|P2|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|EveningTrader|P3|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|EveningTrader|P4|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|EveningTrader|P5|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|OldmanScalping|P1|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|OldmanScalping|P2|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|OldmanScalping|P3|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|OldmanScalping|P4|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|OldmanScalping|P5|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|RavenSignalsPro|P1|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|RavenSignalsPro|P2|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|RavenSignalsPro|P3|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|RavenSignalsPro|P4|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|RavenSignalsPro|P5|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|Raven_signalst_pro|P1|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|Raven_signalst_pro|P2|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|Raven_signalst_pro|P3|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|Raven_signalst_pro|P4|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|Raven_signalst_pro|P5|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|Teambuertrades|P1|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|Teambuertrades|P2|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|Teambuertrades|P3|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|Teambuertrades|P4|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|Teambuertrades|P5|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|TopCryptoFuturesSignals|P1|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|TopCryptoFuturesSignals|P2|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|TopCryptoFuturesSignals|P3|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|TopCryptoFuturesSignals|P4|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|TopCryptoFuturesSignals|P5|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|TradingGainX|P1|65|10.769|0.225|-48.918|-244.590|21 / 0.665 / -5.621|44 / 0.065 / -43.297|26 / 0.000 / -26.085|NOT_STARTED|
|TradingGainX|P2|65|56.923|0.641|-10.128|-50.642|21 / 0.555 / -3.800|44 / 0.678 / -6.329|26 / 0.667 / -3.769|NOT_STARTED|
|TradingGainX|P3|65|63.077|0.713|-7.965|-39.827|21 / 0.531 / -3.988|44 / 0.793 / -3.978|26 / 0.901 / -1.115|NOT_STARTED|
|TradingGainX|P4|65|50.769|0.800|-5.146|-25.729|21 / 0.544 / -3.882|44 / 0.927 / -1.264|26 / 0.811 / -2.173|NOT_STARTED|
|TradingGainX|P5|65|33.846|0.804|-7.755|-38.776|21 / 0.582 / -5.307|44 / 0.909 / -2.448|26 / 0.829 / -2.780|NOT_STARTED|
|Whalesguide|P1|70|34.286|1.367|17.728|88.641|51 / 1.296 / 10.590|19 / 1.567 / 7.138|30 / 1.183 / 4.034|NOT_STARTED|
|Whalesguide|P2|70|78.571|1.467|7.407|37.033|51 / 1.332 / 4.185|19 / 1.991 / 3.222|30 / 1.111 / 0.824|NOT_STARTED|
|Whalesguide|P3|70|78.571|1.461|7.308|36.539|51 / 1.306 / 3.854|19 / 2.062 / 3.454|30 / 1.263 / 1.960|NOT_STARTED|
|Whalesguide|P4|70|72.857|1.651|9.072|45.358|51 / 1.420 / 4.720|19 / 2.609 / 4.352|30 / 1.214 / 1.466|NOT_STARTED|
|Whalesguide|P5|70|47.143|1.242|6.711|33.553|51 / 1.128 / 2.691|19 / 1.592 / 4.019|30 / 0.980 / -0.271|NOT_STARTED|
|WolfxCrypto_VIP|P1|51|64.706|1.715|13.815|69.077|1 / 0.000 / -1.334|50 / 1.842 / 15.149|16 / 1.571 / 3.625|NOT_STARTED|
|WolfxCrypto_VIP|P2|51|64.706|1.715|13.815|69.077|1 / 0.000 / -1.334|50 / 1.842 / 15.149|16 / 1.571 / 3.625|NOT_STARTED|
|WolfxCrypto_VIP|P3|51|64.706|1.715|13.815|69.077|1 / 0.000 / -1.334|50 / 1.842 / 15.149|16 / 1.571 / 3.625|NOT_STARTED|
|WolfxCrypto_VIP|P4|51|56.863|1.290|3.360|16.801|1 / 0.000 / -1.198|50 / 1.438 / 4.558|16 / 0.581 / -1.721|NOT_STARTED|
|WolfxCrypto_VIP|P5|51|58.824|1.351|6.706|33.530|1 / 0.000 / -1.198|50 / 1.442 / 7.904|16 / 1.208 / 1.327|NOT_STARTED|
|altsignals|P1|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|altsignals|P2|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|altsignals|P3|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|altsignals|P4|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|altsignals|P5|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|astronomer_zero|P1|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|astronomer_zero|P2|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|astronomer_zero|P3|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|astronomer_zero|P4|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|astronomer_zero|P5|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|bitcoinbullets|P1|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|bitcoinbullets|P2|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|bitcoinbullets|P3|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|bitcoinbullets|P4|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|bitcoinbullets|P5|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|chainexsignals|P1|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|chainexsignals|P2|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|chainexsignals|P3|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|chainexsignals|P4|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|chainexsignals|P5|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|coin_sgnls_PRO|P1|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|coin_sgnls_PRO|P2|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|coin_sgnls_PRO|P3|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|coin_sgnls_PRO|P4|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|coin_sgnls_PRO|P5|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|coincodecap|P1|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|coincodecap|P2|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|coincodecap|P3|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|coincodecap|P4|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|coincodecap|P5|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|crusader_trades|P1|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|crusader_trades|P2|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|crusader_trades|P3|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|crusader_trades|P4|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|crusader_trades|P5|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|crypto_Winston|P1|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|crypto_Winston|P2|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|crypto_Winston|P3|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|crypto_Winston|P4|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|crypto_Winston|P5|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|crypto_signalsf|P1|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|crypto_signalsf|P2|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|crypto_signalsf|P3|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|crypto_signalsf|P4|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|crypto_signalsf|P5|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|cryptoclassics|P1|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|cryptoclassics|P2|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|cryptoclassics|P3|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|cryptoclassics|P4|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|cryptoclassics|P5|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|cryptoinsidebets|P1|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|cryptoinsidebets|P2|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|cryptoinsidebets|P3|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|cryptoinsidebets|P4|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|cryptoinsidebets|P5|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|cryptoninjas_trading_ann|P1|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|cryptoninjas_trading_ann|P2|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|cryptoninjas_trading_ann|P3|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|cryptoninjas_trading_ann|P4|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|cryptoninjas_trading_ann|P5|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|cryptoroverytofficiaI|P1|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|cryptoroverytofficiaI|P2|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|cryptoroverytofficiaI|P3|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|cryptoroverytofficiaI|P4|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|cryptoroverytofficiaI|P5|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|cryptosignals0rg|P1|889|25.084|0.946|-40.087|-200.436|834 / 0.964 / -24.997|55 / 0.646 / -15.090|317 / 0.893 / -27.714|NOT_STARTED|
|cryptosignals0rg|P2|889|33.746|0.626|-71.052|-355.261|834 / 0.616 / -56.555|55 / 0.660 / -14.497|317 / 0.547 / -43.529|NOT_STARTED|
|cryptosignals0rg|P3|889|69.516|0.588|-73.879|-369.396|834 / 0.566 / -59.382|55 / 0.660 / -14.497|317 / 0.521 / -44.418|NOT_STARTED|
|cryptosignals0rg|P4|889|19.798|0.742|-44.587|-222.936|834 / 0.680 / -45.363|55 / 1.025 / 0.776|317 / 0.747 / -20.575|NOT_STARTED|
|cryptosignals0rg|P5|889|34.308|0.880|-52.750|-263.752|834 / 0.883 / -46.791|55 / 0.852 / -5.959|317 / 0.880 / -20.089|NOT_STARTED|
|fatpigsignals|P1|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|fatpigsignals|P2|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|fatpigsignals|P3|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|fatpigsignals|P4|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|fatpigsignals|P5|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|fedrussianinsiders|P1|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|fedrussianinsiders|P2|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|fedrussianinsiders|P3|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|fedrussianinsiders|P4|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|fedrussianinsiders|P5|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|free_crypto_vip|P1|82|29.268|0.617|-21.700|-108.501|46 / 0.472 / -17.200|36 / 0.814 / -4.500|31 / 0.918 / -1.632|NOT_STARTED|
|free_crypto_vip|P2|82|53.659|0.323|-16.532|-82.660|46 / 0.265 / -10.097|36 / 0.396 / -6.435|31 / 0.339 / -6.324|NOT_STARTED|
|free_crypto_vip|P3|82|64.634|0.325|-16.371|-81.853|46 / 0.262 / -10.060|36 / 0.407 / -6.311|31 / 0.394 / -5.786|NOT_STARTED|
|free_crypto_vip|P4|82|34.146|0.165|-15.113|-75.567|46 / 0.210 / -6.684|36 / 0.126 / -8.430|31 / 0.077 / -8.542|NOT_STARTED|
|free_crypto_vip|P5|82|47.561|0.462|-18.084|-90.420|46 / 0.393 / -11.473|36 / 0.550 / -6.611|31 / 0.483 / -6.838|NOT_STARTED|
|learn2tradectypto|P1|37|32.432|0.864|-3.854|-19.269|24 / 0.965 / -0.630|13 / 0.694 / -3.224|14 / 0.976 / -0.256|NOT_STARTED|
|learn2tradectypto|P2|37|32.432|0.698|-8.563|-42.816|24 / 0.743 / -4.585|13 / 0.622 / -3.978|14 / 0.904 / -1.011|NOT_STARTED|
|learn2tradectypto|P3|37|32.432|0.638|-10.264|-51.318|24 / 0.690 / -5.532|13 / 0.551 / -4.732|14 / 0.833 / -1.765|NOT_STARTED|
|learn2tradectypto|P4|37|32.432|0.857|-3.031|-15.157|24 / 1.098 / 1.322|13 / 0.433 / -4.354|14 / 0.816 / -1.412|NOT_STARTED|
|learn2tradectypto|P5|37|32.432|0.729|-7.097|-35.487|24 / 1.033 / 0.531|13 / 0.234 / -7.629|14 / 0.529 / -4.687|NOT_STARTED|
|learn2tradenews|P1|29|17.241|0.239|-23.601|-118.005|20 / 0.352 / -13.630|9 / 0.000 / -9.971|9 / 0.000 / -9.971|NOT_STARTED|
|learn2tradenews|P2|29|17.241|0.239|-23.601|-118.005|20 / 0.352 / -13.630|9 / 0.000 / -9.971|9 / 0.000 / -9.971|NOT_STARTED|
|learn2tradenews|P3|29|17.241|0.239|-23.601|-118.005|20 / 0.352 / -13.630|9 / 0.000 / -9.971|9 / 0.000 / -9.971|NOT_STARTED|
|learn2tradenews|P4|29|24.138|0.655|-7.572|-37.861|20 / 0.797 / -3.021|9 / 0.357 / -4.551|9 / 0.357 / -4.551|NOT_STARTED|
|learn2tradenews|P5|29|13.793|0.412|-16.740|-83.698|20 / 0.604 / -7.696|9 / 0.000 / -9.044|9 / 0.000 / -9.044|NOT_STARTED|
|main3commassignals|P1|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|main3commassignals|P2|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|main3commassignals|P3|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|main3commassignals|P4|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|main3commassignals|P5|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|ne_investor|P1|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|ne_investor|P2|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|ne_investor|P3|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|ne_investor|P4|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|ne_investor|P5|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|safe_academy|P1|85|34.118|0.591|-26.325|-131.627|57 / 0.686 / -12.380|28 / 0.439 / -13.945|33 / 0.464 / -15.008|NOT_STARTED|
|safe_academy|P2|85|47.059|0.417|-23.842|-119.212|57 / 0.349 / -19.023|28 / 0.588 / -4.820|33 / 0.517 / -6.672|NOT_STARTED|
|safe_academy|P3|85|60.000|0.470|-21.500|-107.499|57 / 0.361 / -18.463|28 / 0.739 / -3.037|33 / 0.639 / -4.963|NOT_STARTED|
|safe_academy|P4|85|51.765|0.801|-6.352|-31.761|57 / 0.623 / -8.493|28 / 1.227 / 2.141|33 / 1.132 / 1.386|NOT_STARTED|
|safe_academy|P5|85|35.294|0.638|-17.857|-89.286|57 / 0.651 / -11.602|28 / 0.610 / -6.256|33 / 0.543 / -8.632|NOT_STARTED|
|sagesignals8|P1|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|sagesignals8|P2|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|sagesignals8|P3|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|sagesignals8|P4|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|sagesignals8|P5|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|tokenwhisperer_io|P1|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|tokenwhisperer_io|P2|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|tokenwhisperer_io|P3|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|tokenwhisperer_io|P4|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|tokenwhisperer_io|P5|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|traderosho|P1|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|traderosho|P2|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|traderosho|P3|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|traderosho|P4|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|traderosho|P5|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|universalcryptosignals|P1|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|universalcryptosignals|P2|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|universalcryptosignals|P3|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|universalcryptosignals|P4|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|universalcryptosignals|P5|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|wallstreetqueenofficial|P1|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|wallstreetqueenofficial|P2|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|wallstreetqueenofficial|P3|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|wallstreetqueenofficial|P4|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|wallstreetqueenofficial|P5|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|wolfoftrading|P1|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|wolfoftrading|P2|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|wolfoftrading|P3|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|wolfoftrading|P4|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|wolfoftrading|P5|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|wolfxsignals_freegroup|P1|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|wolfxsignals_freegroup|P2|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|wolfxsignals_freegroup|P3|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|wolfxsignals_freegroup|P4|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|
|wolfxsignals_freegroup|P5|0|NA|NA|NA|NA|NA|NA|NA|NOT_STARTED|

## Заявления автора и цены

Из 87 связанных TP-reached сообщений у 27 однозначно указан номер цели. Проверка закрытых минут до публикации дала: {'DATA_GAP_PROXY_PRICES': 2, 'MARKET_TOUCH_COMPATIBLE_NOT_FILL_PROOF': 23, 'NO_TOUCH_IN_COMPLETE_PROXY_WINDOW_NOT_FRAUD_PROOF': 2, 'TP_INDEX_UNRESOLVED': 60}. 23 совместимых касания не доказывают исполнение автора; 2 несовпадения не доказывают обман при другом рынке, неизвестных редакциях и исключённой публикационной минуте. Остальные номера/цены неизвестны. Детали в TP_CLAIM_MARKET_CHECK.json.

Текстовый фильтр месячной статистики находит также рекламу. Без капитала, плеча, долей и полного журнала он не даёт сопоставимую доходность; эти кандидаты статпостов помечены NON_COMPARABLE, а не признаны истинными или ложными.

## Предвзятость и ограничения

8 зеркал дошли до доступного конца, 31 ограничено PAGE_LIMIT, 6 имеют DATA_BLOCKED. Даже MIRROR_END не восстанавливает удалённые/VIP-посты. Видимые редакции: 3886/69451. Числовые пропуски: 11354/80805 слотов; это не число удалений и не доля удалённых убытков. Даты, статусы и SHA источника — MIRROR_BIAS_AUDIT.json и SOURCE_MANIFEST.json.

Исторические версии текста на момент публикации неизвестны. Есть отдельная чувствительность без видимых редакций, но отсутствие отметки не доказывает отсутствие редактирования. Идентичность нескольких авторов внутри канала не восстановлена, поэтому P1 остаётся каналовым прокси по распознанным командам, не доказанной стратегией конкретного человека.

MATCHED5 отбирает полностью закрытые случаи и может зависеть от цензурирования длинных позиций. Это общая сравнимая, но не полная авторская выборка. Отсутствующие SL/TP не достраивались по будущим сообщениям. Максимальная просадка считается в R по закрытиям, не по mark-to-market портфеля. Последние 40% старой истории — исторический OOS, не новый forward.

## Канал друга и незавершённые работы

Название канала друга пока не получено: нужен @username или t.me-ссылка. Его отдельная история и свежий --resume-сбор не выполнялись; произвольный другой канал вместо него не выбран.

Настоящий forward после фиксации методики не набран. У 143 исходных сигналов нет пригодной цены входа. 36 P1 остались открыты на границе снимка 14 ноября. Ещё один P1 по KEEPUSDT упирается в конец проверенного февральского архива 2022 года: terminal settlement неизвестен, фиктивный выход по последней цене не добавлен. Подробности в KNOWN_BLOCKERS.json.

Следующий этап: независимая проверка связей обновлений, получение названия канала друга и новые нормализованные наблюдения. Не менять P1–P5 по этим результатам, не подменять funding нулём, не добавлять новые стопы. Продолжать только реальные пробелы; повторный download того же законченного KEEP-архива не поможет.

## ПРОСТЫМИ СЛОВАМИ ДЛЯ ВЛАДЕЛЬЦА

Старый общий вывод обо всех 45 каналах был слишком широким. Найдены положительные ограниченные подвыборки, и способ исполнения влияет на цифры. Но устойчиво прибыльный канал по заданным требованиям пока не подтверждён. Полный журнал автора, скрытые посты и текущая торговля друга из этих зеркал не восстановлены. PR #591, LIVE и работающие сервисы не менялись.

Desktop Commander 0, Bybit-ключи 0, LIVE изменений 0
