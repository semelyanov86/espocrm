/**
 * The charts of a report result (D-105): their common title, up to three charts in one row and the notes of what a
 * chart could not show. Used by the result page and the dashlet «Отчёт»; a click on a chart triggers `drill-down`.
 */
define('itvolga:views/report/charts', ['view'], (View) => {

    return class extends View {

        templateContent = `
            <div class="itv-report-charts">
                <h5 data-role="title"></h5>
                <div class="row" data-role="row"></div>
                <div class="text-muted small" data-role="notes"></div>
            </div>`

        setup() {
            this.chart = this.options.chart;
            this.height = this.options.height || 300;
            this.on('resize', () => this.chart.items.forEach((item, i) => {
                const view = this.getView('chart' + i);

                view && view.trigger('resize');
            }));
        }

        async afterRender() {
            const chart = this.chart;
            const title = this.element.querySelector('[data-role="title"]');
            const row = this.element.querySelector('[data-role="row"]');
            const notes = this.element.querySelector('[data-role="notes"]');
            const width = Math.floor(12 / Math.max(1, chart.items.length));

            title.textContent = chart.title || '';
            title.classList.toggle('hidden', !chart.title);

            chart.items.forEach((item, i) => {
                const column = document.createElement('div');
                column.className = 'col-sm-' + width;
                column.dataset.chart = String(i);
                row.appendChild(column);
            });

            const texts = new Set();

            chart.items.forEach(item => (item.notes || []).forEach(note => texts.add(
                this.translate('note' + note.charAt(0).toUpperCase() + note.slice(1), 'labels', 'Report')
                    .replace('{n}', '50'))));
            texts.forEach(text => {
                const div = document.createElement('div');
                div.textContent = text;
                notes.appendChild(div);
            });

            for (const [i] of chart.items.entries()) {
                const view = await this.createView('chart' + i, 'itvolga:views/report/chart', {
                    selector: `[data-chart="${i}"]`,
                    chart: chart,
                    index: i,
                    height: this.height,
                });

                this.listenTo(view, 'drill-down', path => this.trigger('drill-down', path));
                await view.render();
            }
        }
    };
});
