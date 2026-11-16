# Round4 C — новые R1h/G3h, не замена старых

До любого нового PnL C. Окно1698796800000–1794614400000, HALF1746705600000, TAIL1756287360000. Binance USDT-M ALT_VENUE_PROXY, реальные verifiedH1. Издержки taker0.055%/ногу и5bps market; stress10bps. Maker только диагностически, не исполненные market ноги. Funding настоящие rate/timestamp и оставшееся количество, candle-markapprox отдельно, неизвестное не0. Пропуски quotes удерживаемого/delisted контракта не forwardfill и не ретроспективная ликвидация.

## R1h
Все4 старых frozenварианта L30/L90 LONG_SHORT/LONG_ONLY, сохранённые веса R1_FROZEN_WEIGHTS.csv.gz переиспользуются без fit. Решение понедельник00:00, исполнение **01:00open H1**, не00:15. Top20 PIT30dturnover, sign30/90d, vol30dtarget20%, gross<=1, веса и cash как Round3. NAV10000, fixedquantity между weeklyrebalance, fees только changequantity, закрытие ушедшихмонет. Почасовой MTM/real funding. Старый15m вход не заменён.

Сначала отдельный audit всех execution quotes, path держания и fundingcoverage. Если нет хотя бы одной требуемой цены/funding, весь полный net-тест DATA_BLOCKED; price-only/полныйконтроль не выдавать за net. После устранения блокера расчёт на неизменённых весах: оба полупериода иtail, 1000seed20261115 контролей с перестановкой последовательности недельных sign по инструменту при фиксированных magnitudes/ranks, всеиздержки. Нельзя менять веса после просмотраnet. ТестыSharpe>=1вобеихполовинах,MDD<=25%,контроль;R безSLнепридумывать.

## G3h
Новые5вариантов: FULL,NO_OWN_DECLINE,NO_REVERSAL,NO_QUALITY,NO_MEME. Исходные4G3/15m не переписывать. На каждомH1close: realPITtop150,top10losers r24<=−8%;ownr24−BTCr24<=−6pp. Qtop40past30dturnover,возраст>180д,проверенный nonmeme asof. Отсутствие в нынешнем неполноммемеснимке НЕ доказательствоnonmeme. NO_QUALITY убирает все3частиQ, оставляетtop150. NO_MEME убирает толькоnonmeme,rank/ageостаются. При неизвестномage/Qunknown,неpassed.

H1reversal: минимум последних24полныхH1; после него подтверждённыеpivot-lows с2левыми и2правыми закрытыми свечами, второйвыше первого;close>anchoredVWAPсминимума (реальныйquote/basevolume); текущийvolume>=1.5medianпредыдущих24полныхH1. Все24H1непрерывны; tieslatestminimum. Сигнал по последнейзакрытойH1, **openследующегоH1** (decisiontimestamp, первая следующаясвеча), не выдуманные15m. NO_REVERSALвходпозакрытиючасовогоотборабезэтогоподтверждения. Стопmin24h×(1−1e−8),width<=6%;TP1=+1R,TP2=+2R,TP3=entry+50%разницыclose24hago−min24h. ЕслиTP3<=TP2,отклонить,непереноситьTPподрезультат. Доли50/30/20,BEсоследующейH1послеTP1;SLfirst,неTPentrybar;48hmax;timeexitследующийдоступныйopenбезchase. Риск0.5%NAV, max5позиции,1насимвол,grossnotional<=100%NAV;fee-inclusiveplannedrisk. Отказы/unknown/repeats/censoringвжурнал.

Аудит сначала: корректныеassetidentity/listingtimestamps/meme-asof; sourcefunding214покрываетнекоторыемонеты,не всюPIT150; бездостаточногоexecution/funding/fullQневыдаватьполныйnet. СтатусDATA_BLOCKEDнеотклонениеидеи. Контрольприразблокировании:1000samecoin/side/hourofdayotherday внутриcalendarweek, толькоисторическидоступныйQ/confirm/context, тежеиздержки;seed20261115,непоискдня. Все5вариантовпоказыватьвключаяотрицательные. Критерийn>=60,PF>=1.3,net>0вобеихполовинах,tail>0,bestday<30%,Holm5. Текущиймемеснимокдлякаузальногонемемефильтранедостаточен.

## Продолжение оригинального15m
Проверять43743059934, при завершении брать только его checkpoint/готовые shards; не начинатьколлекторснуля и не запускатьдубликат. Старые определения pivot изстарогокода несовпадаютсновымсимметричнымpivotG3h — эторазныепротоколы,неподменять.

## ПРОСТЫМИ СЛОВАМИ ДЛЯ ВЛАДЕЛЬЦА
Новые часовые входы записаны отдельно. Сначала проверяем, хватает ли настоящих цен и расходов; отсутствующие данные не превращаем в прибыль или ноль.

Desktop Commander 0, Bybit-ключи 0, LIVE изменений 0
