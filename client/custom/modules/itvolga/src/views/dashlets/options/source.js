/**
 * Options of the dashlets «Отчёт» and «Ключевые показатели»: the source (a report or a key-metrics set) is kept by id
 * only. Its name would be stored with the options and reach every user a dashboard template is given to, also one who
 * may not read the source (external review, round 3); it is looked up for display with the rights of the user.
 */
define('itvolga:views/dashlets/options/source', ['views/dashlets/options/base'], (BaseView) => {

    const SOURCES = {report: 'Report', metricSet: 'ReportMetricSet'};

    return class extends BaseView {

        setupBeforeFinal() {
            Object.entries(SOURCES).filter(([field]) => field in this.fields).forEach(([field, entityType]) => {
                const id = this.model.get(field + 'Id');

                if (!id) {
                    return;
                }

                this.wait(Espo.Ajax.getRequest(`${entityType}/${encodeURIComponent(id)}`)
                    .then(record => this.model.set(field + 'Name', record.name))
                    .catch(xhr => {
                        if (xhr && typeof xhr === 'object') {
                            xhr.errorIsHandled = true;
                        }
                    }));
            });
        }

        fetchAttributes() {
            const attributes = super.fetchAttributes();

            if (attributes) {
                Object.keys(SOURCES).forEach(field => delete attributes[field + 'Name']);
            }

            return attributes;
        }
    };
});
