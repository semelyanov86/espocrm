/**
 * Values of a key-metrics set for the viewer (D-112): rows «label … value» in the order of the set; the label leads to
 * the source — the result of the report, or the standard record list of the filter's conditions in a modal. A row
 * whose source is closed, removed or changed shows its status instead of a value. Used by the dashlet «Ключевые
 * показатели» and the page of the set.
 */
define('itvolga:views/report-metric-set/values', ['view'], (View) => {

    return class extends View {

        templateContent = `<div data-role="values"><span class="text-muted">…</span></div>`

        setup() {
            this.generation = 0;
            this.addActionHandler('openFilter', (e, target) => this.openFilter(Number(target.dataset.index)));
        }

        /** The record view asks its bottom view for field views (none here). */
        getFieldViews() {
            return {};
        }

        getFieldView() {
            return null;
        }

        setId() {
            return this.options.setId || (this.model ? this.model.id : null);
        }

        afterRender() {
            this.load();
        }

        message(text) {
            const box = this.element.querySelector('[data-role="values"]');
            box.innerHTML = '';
            const span = document.createElement('span');
            span.className = 'text-muted';
            span.textContent = text;
            box.appendChild(span);
        }

        async load() {
            const generation = ++this.generation;

            try {
                const data = await Espo.Ajax.getRequest(`ReportMetricSet/${encodeURIComponent(this.setId())}/values`);

                if (generation === this.generation && this.isRendered()) {
                    this.rows = data.rows;
                    this.renderRows(data.rows);
                }
            } catch (xhr) {
                if (xhr && typeof xhr === 'object') {
                    xhr.errorIsHandled = true;
                }

                if (generation === this.generation && this.isRendered()) {
                    this.message(this.translate(xhr && xhr.status === 404 ? 'Set deleted' : 'No access', 'labels',
                        'ReportMetricSet'));
                }
            }
        }

        renderRows(rows) {
            const box = this.element.querySelector('[data-role="values"]');
            box.innerHTML = '';

            if (!rows.length) {
                this.message(this.translate('No rows', 'labels', 'ReportMetricSet'));

                return;
            }

            const table = document.createElement('table');
            table.className = 'table table-condensed';
            const tbody = document.createElement('tbody');

            rows.forEach((row, i) => {
                const tr = document.createElement('tr');
                tr.dataset.id = row.id;
                const labelCell = document.createElement('td');
                const link = document.createElement('a');
                link.textContent = row.label;

                if (row.source === 'report') {
                    link.href = '#Report/view/' + encodeURIComponent(row.reportId);
                } else if (row.status === 'ok') {
                    link.setAttribute('role', 'button');
                    link.dataset.action = 'openFilter';
                    link.dataset.index = String(i);
                }

                // A filter the viewer cannot build has no conditions here: no link to a list without them.
                labelCell.appendChild(row.source === 'filter' && row.status !== 'ok' ?
                    document.createTextNode(row.label) : link);
                const valueCell = document.createElement('td');
                valueCell.className = 'text-right';
                valueCell.dataset.role = 'value';

                if (row.status === 'ok' && row.value) {
                    valueCell.textContent = row.value.f;
                } else {
                    const status = document.createElement('span');
                    status.className = 'text-muted';
                    status.textContent = this.translate('status' + row.status.charAt(0).toUpperCase() +
                        row.status.slice(1), 'labels', 'ReportMetricSet');
                    valueCell.appendChild(status);
                }

                tr.append(labelCell, valueCell);
                tbody.appendChild(tr);
            });

            table.appendChild(tbody);
            box.appendChild(table);
        }

        /** The records of a filter row: the standard list of its entity with the same where items. */
        openFilter(index) {
            const row = (this.rows || [])[index];

            if (!row || row.source !== 'filter' || row.status !== 'ok') {
                return;
            }

            this.createView('records', 'itvolga:views/report/modals/drill-down', {
                entityType: row.entityType,
                where: row.where,
                headerText: row.label,
            }, view => view.render());
        }
    };
});
