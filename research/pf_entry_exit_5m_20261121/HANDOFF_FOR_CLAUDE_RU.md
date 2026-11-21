# Независимая проверка

Читайте REPORT_RU.md, FROZEN_PROTOCOL.json, INPUT_AUDIT.json, CHECKPOINT.json. Не запускайте завершённые расчёты повторно без найденной причины.

1. Проверьте порядок коммитов: протокол → код21tests → TRAIN-entry selection → TRAIN-final selection → TESTresults; сравните с STARTED/COMPLETE и SHA карточек.
2. Сверьте именно BASE/PRIMARY2113, а не1761filled-only;333 восстановленныхC из реальных предшествующихзакрытых5m,19tail/21purge сохранены.
3. Проверьте source callback в Crypto-Auto-Radar по SOURCE_CODE_REFERENCES.json: clamped rate/WAIT, TP1/SL skip, stop5,6%, TP2,1/4,2/6,3%,50/30/20, BE0,9989; текущийruntime неизвестен. ИсследовательскиеTTL/задержки/tolerance не выдаются за текущийLIVE.
4. В журналах:sumfraction=1, SLfirst/gap/noTPfillbar/BEсследующегобара, риск0,056 отдельно от старого0,0581, расходов21/40bp без doublecount.
5. Funding bracketing недостаточен для доказательства полноты;markproxy и null неизвестных не считать actualnet. MFE/MAE — wholebarcoarse.
6. Проверьте EXPOSEDисторию, неверность трактовки archive-selected какLIVEtop50, n12 в падающемTEST, недопустимость выбораE2поTEST. НовыхнезависимыхOOS/samecoinrandom/BH здесь нет и они не заявлены; положительныйкандидат не продвигается.
7. Проверьте все16конфигураций/640строк/журналы/CONCENTRATION/отрицательныерезультаты;посмотрите рискперекрытияпозиций, не считатьΣRпроцентомилиденежнымдоходом.
8. РеальнуюLIVE16сверку продолжать только послеDATA_NEEDED из REPORT;источникинепересчитывать. ПроверьтеDraft/unmerged, изменениятольковновойпапке,никакогодеплоя.
