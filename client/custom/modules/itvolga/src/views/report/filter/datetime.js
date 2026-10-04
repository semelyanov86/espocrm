/**
 * Date-time condition of a report: as itvolga:views/report/filter/date over the core date-time search (days are local
 * days of the runner, the core converts them to UTC).
 */
define('itvolga:views/report/filter/datetime', ['views/fields/datetime'], (DatetimeView) => {

    return class extends DatetimeView {

        setup() {
            super.setup();

            this.searchTypeList = ['on', 'before', 'after', 'between', 'today', 'yesterday', 'tomorrow', 'past', 'future',
                'currentWeek', 'lastWeek', 'nextWeek', 'currentMonth', 'lastMonth', 'nextMonth', 'currentQuarter',
                'lastQuarter', 'nextQuarter', 'currentYear', 'lastYear', 'nextYear', 'currentFiscalYear',
                'lastFiscalYear', 'currentFiscalQuarter', 'lastFiscalQuarter', 'lastSevenDays', 'lastXDays',
                'nextXDays', 'olderThanXDays', 'afterXDays', 'xDaysAgo', 'inXDays', 'ever', 'isEmpty'];
            this.searchWithAdditionalNumberTypeList = [...this.searchWithAdditionalNumberTypeList, 'xDaysAgo', 'inXDays'];
        }
    };
});
