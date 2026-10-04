/**
 * Dashlet «Ключевые показатели» (D-112): the values of a key-metrics set for the viewer, refreshed by the dashlet's
 * period; a removed set shows that it is deleted (its dashlets are removed when the set is deleted, D-113).
 */
define('itvolga:views/dashlets/report-metrics', ['views/dashlets/abstract/base'], (BaseView) => {

    return class extends BaseView {

        name = 'ReportMetrics'

        templateContent = `<div class="metrics-container"></div>`

        afterRender() {
            this.clearView('values');
            const setId = this.getOption('metricSetId');

            if (!setId) {
                const span = document.createElement('span');
                span.className = 'text-muted';
                span.textContent = this.translate('Set deleted', 'labels', 'ReportMetricSet');
                this.element.querySelector('.metrics-container').appendChild(span);

                return;
            }

            this.createView('values', 'itvolga:views/report-metric-set/values', {
                selector: '.metrics-container',
                setId: setId,
            }, view => view.render());
        }

        actionRefresh() {
            const view = this.getView('values');

            view ? view.load() : this.reRender();
        }
    };
});
