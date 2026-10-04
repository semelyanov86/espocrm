/**
 * Date condition of a report: the core date search with the periods reports need beyond the core ones (yesterday,
 * tomorrow, weeks, next quarter and year, fiscal periods always, exactly N days ago/ahead). The browser only stores the
 * type: the server resolves the period at every run in the runner's time zone (D-92).
 */
define('itvolga:views/report/filter/date', ['views/fields/date'], (DateView) => {

    return class extends DateView {

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
