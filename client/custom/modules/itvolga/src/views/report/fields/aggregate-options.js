/**
 * Labels of the aggregates of the model, for the parts that refer to them (group sort, HAVING, labels).
 */
define('itvolga:views/report/fields/aggregate-options', ['itvolga:report/catalog'], (Catalog) => {

    return {
        /**
         * @return {{key: string, label: string}[]}
         */
        list(view) {
            const lang = view.getLanguage();

            return (view.model.get('aggregates') || []).map(item => {
                const ref = item.field ? (item.link ? item.link + '.' + item.field : item.field) : null;
                const fnLabel = lang.translateOption(item.function, 'aggregateFunction', 'Report');

                return {
                    key: ref ? item.function + ':' + ref : item.function,
                    label: ref ? fnLabel + ': ' + Catalog.label(view.catalog, ref) : fnLabel,
                };
            });
        },
    };
});
