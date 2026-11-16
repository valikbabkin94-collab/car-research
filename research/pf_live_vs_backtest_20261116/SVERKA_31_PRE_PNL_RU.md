# Продолжение после b711017: таргетированная сверка 31 сигнала

Источник: неизменённые 13 trades и31decisions из b711017. Годовой replay готов, не повторять. Сначала проверка полей/цен/времён/частей и effective stop, затем только эти31сигнал на настоящих1m. CSV/JSON сохраняют все13live и18NOT_ENTERED_UNKNOWN; отсутствие причины не заменять выводом окасаниелимита.

Модель: закрытаяH1 reference close ×1.013,TTL8h отcreated_ms,вход не раньшепервогоцелого1mпослеcreated_ms;SL5.6%отfill,TP2.1/4.2/6.3%,доли50/30/20,BEshort=entry*(1−.0011)со следующей1m,hold72h. SL-first,noTPfillbar. По source clock использоватьприсланныйcreated_ms,неbackdateнаsignal_ms. Цена reference: original сохранённыйBybitlimit при exactmatch;иначе Bybit5m close непосредственно передsignal_ms изготовогоmarketcache;иначе Binance1m close(явныйcross-venueproxy). initial_stop_priceизБДнеравенподтверждённомуexchangeeffectiveSL; неувеличиватьSLдо12%наодномполе.

Binance USDT-M1m: checksum-verified dailyarchives11–16Nov,толькоадресныеsymbol/dayнужных31окон,максимум4worker. Неполныйтекущийдень:однаограниченнаяпроверкапубличныхklinesREST;при403/451неповторятьпосимволам. Funding: проверкапубликацииNovembermonthly/dailyarchive,переиспользованиеготового;еслиденежноепокрытиенет—model_net_R=null,price_Rпоказыватьотдельно. Неиспользоватьlivefunding_Rдляотличающейсямодельнойтраектории. BinancequotesнеобъявлятьсовпавшимBybitисполнением.

Времяобрезки=min(exported_ms двухфайлов),толькозакрытыесвечи. Недостающий1m—DATA_GAP,а неNOFILL. PendingдоTTL—PENDING/censored,непропускбота. ЕслиS/LTPзакрываютраньшеизвестногогоризонта,разрешёнзакрытыйисходпополномунаблюдённомупрефиксу;этоадреснаяадминистративнаяцензура,непересчётгодовогокорпуса.

Fees: .055%taker market/stop/time,.02%restinglimit/TP;прикасанииmaker-очередьнеподтверждена,этоassumed-touchмодель. Slippage5bpsдляmarket/SL/time,0дляrestinglimit/TP. Rdenom stopwidth+.0021,уPF=.0581. Actualnet_Rоставитькакпереданоператором;выходныеkind/fee_Rпомеченыэвристическими/оценочными. Реальныеpartialsнеподгонятьк50/30/20. Неdoublecount funding.

Корреляция: проверитьtimestampsNBIS/KORU/MVLL,показатьpre-entryclosedH1returnsизготовогоGitHubBybitcache. По13исходамρнеидентифицируется. Вероятностьсериипоказатьдляiidиperfect-correlationтолькоэтойтройки: P(X≥12)=p*[10*p^9*(1-p)+p^10];остальные10считаютсянезависимыми,этоусловнаячувствительность,неоценкап вероятностиудачи. pизранееопубликованныхOLD/BEselectedисторий,неподбиратьпо13исходам.

ПослеотчётасразуограниченнаяматрицаRubikпоотдельномузафиксированномупротоколу.Безточнойsame-venue1m/fundingпроверкинетобъявленияenginevalidatedдляLIVE;RubikбудетэкспериментальнымBinanceproxy,неподменойlive13.

## ПРОСТЫМИ СЛОВАМИ ДЛЯ ВЛАДЕЛЬЦА
Проверяемтольконужныесделкиисигналы. Стоп12%проверяемпофактам,непринимаемподсказкунаверу. Пробелывценахилиfundingнепревращаемвнулевойубытокиливыигрыш.

Desktop Commander 0, Bybit-ключи 0, LIVE изменений 0
