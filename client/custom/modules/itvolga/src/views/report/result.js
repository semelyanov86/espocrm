/**
 * Result of a report (reports.md §7) under the report info panel of the record page: the conditions (the builder's
 * condition editor on a copy of the report, so a change applies to one run until «Сохранить условия»), quick filter
 * blocks, the counters and limit notes, and the table of the report type — tabular with pages, totals and
 * calculations; summaries as nested group rows; summaries with details as group headers with records; matrix with row
 * and column totals. Values come formatted by the server (cell.f); links lead to the records; a group row opens the
 * standard record list of its records (drill-down). Only standard classes of EspoCRM are used.
 */
define('itvolga:views/report/result', ['view', 'ui/multi-select'], (View, MultiSelect) => {

    const EMPTY = '__empty__';

    return class extends View {

        templateContent = `
            <div class="itv-report-result">
                <div class="button-container clearfix">
                    <div class="btn-group">
                        <button type="button" class="btn btn-default btn-sm" data-action="toggleInfo">{{infoLabel}}</button>
                        <button type="button" class="btn btn-default btn-sm" data-action="toggleConditions">{{conditionsLabel}}</button>
                    </div>
                    <span class="text-muted" data-role="counters"></span>
                </div>
                <div class="panel panel-default hidden" data-role="conditions-panel">
                    <div class="panel-heading"><h4 class="panel-title">{{conditionsLabel}}</h4></div>
                    <div class="panel-body">
                        <div class="cell form-group"><div class="field" data-name="filters"></div></div>
                        <div class="row" data-role="quick-filters"></div>
                        <div class="btn-group">
                            <button type="button" class="btn btn-primary btn-sm" data-action="run">{{runLabel}}</button>
                            {{#if canSave}}<button type="button" class="btn btn-default btn-sm" data-action="saveConditions">
                                {{saveConditionsLabel}}</button>{{/if}}
                        </div>
                    </div>
                </div>
                <div class="text-warning small" data-role="notes"></div>
                <div class="panel panel-default">
                    <div class="panel-body" data-role="table"><span class="text-muted">…</span></div>
                </div>
            </div>`

        setup() {
            this.result = null;
            this.offset = 0;
            this.maxSize = 50;
            this.generation = 0;
            this.quick = {};
            this.conditionsModel = this.model.clone();

            this.addActionHandler('run', () => this.run(true));
            this.addActionHandler('saveConditions', () => this.saveConditions());
            this.addActionHandler('toggleInfo', () => this.options.recordViewObject.toggleInfo());
            this.addActionHandler('toggleConditions', () =>
                this.element.querySelector('[data-role="conditions-panel"]').classList.toggle('hidden'));
            this.addActionHandler('page', (e, target) => {
                this.offset = Math.max(0, Number(target.dataset.offset));
                this.run(false);
            });
            this.addActionHandler('drillDown', (e, target) => this.drillDown(JSON.parse(target.dataset.path)));

            this.listenTo(this.model, 'sync', () => {
                this.conditionsModel.set('filters', this.model.get('filters'));
                this.conditionsModel.set('entityType', this.model.get('entityType'));
            });
        }

        /** The record view asks its bottom view for field views (none here). */
        getFieldViews() {
            return {};
        }

        getFieldView() {
            return null;
        }

        data() {
            return {
                infoLabel: this.translate('Report Info', 'labels', 'Report'),
                conditionsLabel: this.translate('Conditions', 'labels', 'Report'),
                runLabel: this.translate('Run', 'labels', 'Report'),
                saveConditionsLabel: this.translate('Save Conditions', 'labels', 'Report'),
                canSave: this.getAcl().checkModel(this.model, 'edit'),
            };
        }

        async afterRender() {
            this.clearView('conditions');
            const conditions = await this.createView('conditions', 'itvolga:views/report/fields/filters', {
                selector: '.field[data-name="filters"]',
                model: this.conditionsModel,
                name: 'filters',
                mode: 'edit',
            });

            await conditions.render();
            this.run(true);
        }

        quickFilterValues() {
            return Object.entries(this.quick)
                .map(([field, q]) => ({field: field, mode: q.mode, values: q.values.filter(v => v !== EMPTY),
                    includeEmpty: q.values.includes(EMPTY)}))
                .filter(q => q.values.length || q.includeEmpty);
        }

        async run(reset) {
            if (reset) {
                this.offset = 0;
            }

            const conditions = this.getView('conditions');
            const body = {
                offset: this.offset,
                maxSize: this.maxSize,
                quickFilters: this.quickFilterValues(),
                withQuickFilterOptions: true,
            };

            if (conditions && conditions.isRendered()) {
                // A copy: the editor keeps its condition objects and may change them before the drill-down of this
                // result, which must use the conditions the result was made with.
                body.filters = JSON.parse(JSON.stringify(conditions.fetch().filters));
            }

            const generation = ++this.generation;
            Espo.Ui.notifyWait();

            try {
                const result = await Espo.Ajax.postRequest(`Report/${this.model.id}/run`, body);

                if (generation !== this.generation || !this.isRendered()) {
                    return;
                }

                Espo.Ui.notify(false);
                this.result = result;
                this.lastRun = body;
                this.renderResult();
            } catch (e) {
                if (generation === this.generation) {
                    Espo.Ui.notify(false);
                }

                if (e instanceof Error) {
                    // A failed request is reported by the core error handler; an error of the rendering is a bug.
                    console.error(e);
                }
            }
        }

        async saveConditions() {
            const conditions = this.getView('conditions');

            if (!conditions) {
                return;
            }

            Espo.Ui.notifyWait();
            await this.model.save({filters: conditions.fetch().filters}, {patch: true});
            Espo.Ui.success(this.translate('Saved'));
            this.run(true);
        }

        make(tag, className, text) {
            const element = document.createElement(tag);

            if (className) {
                element.className = className;
            }

            if (text !== undefined && text !== null) {
                element.textContent = text;
            }

            return element;
        }

        /** A value cell: a link to the record for link values and for the name of the main record. */
        cell(value, recordId, isName, numeric) {
            const td = this.make('td', numeric ? 'text-right' : null);

            if (!value) {
                return td;
            }

            if (value.id && value.et) {
                const a = this.make('a', null, value.f);
                a.href = `#${value.et}/view/${value.id}`;
                td.appendChild(a);
            } else if (isName && recordId) {
                const a = this.make('a', null, value.f);
                a.href = `#${this.result.entityType}/view/${recordId}`;
                td.appendChild(a);
            } else {
                td.textContent = value.f;
            }

            if (value.mixed) {
                td.classList.add('text-warning');
            }

            return td;
        }

        renderResult() {
            const result = this.result;
            const tableBox = this.element.querySelector('[data-role="table"]');
            const notes = this.element.querySelector('[data-role="notes"]');
            const counters = this.element.querySelector('[data-role="counters"]');

            counters.textContent = ' ' + this.translate('Total records', 'labels', 'Report') + ': ' + result.recordCount;
            notes.innerHTML = '';
            this.limitNotes(result).forEach(text => notes.appendChild(this.make('div', null, text)));
            tableBox.innerHTML = '';

            const table = result.type === 'tabular' ? this.tabular(result) :
                result.type === 'matrix' ? this.matrix(result) : this.grouped(result);

            if (table) {
                const wrapper = this.make('div', 'list');
                wrapper.appendChild(table);
                tableBox.appendChild(wrapper);
            }

            if (result.type === 'tabular') {
                const pager = this.pager(result);

                if (pager) {
                    tableBox.appendChild(pager);
                }
            }

            this.renderQuickFilters(result.quickFilters || []);
        }

        limitNotes(result) {
            const limits = result.limits || {};
            const t = (label, n) => this.translate(label, 'labels', 'Report').replace('{n}', n);
            const list = [];

            if (limits.rowLimitHit) {
                list.push(t('limitedRows', limits.rowLimit));
            }

            if (limits.groupLimitHit) {
                list.push(t('limitedGroups', limits.groupLimit));
            }

            if (limits.capHit) {
                list.push(t('limitedCap', limits.maxRows));
            }

            if (limits.matrixColumnsHit) {
                list.push(t('limitedColumns', limits.maxMatrixColumns));
            }

            return list;
        }

        headerRow(labels, numericFlags) {
            const tr = this.make('tr');

            labels.forEach((label, i) => tr.appendChild(this.make('th', numericFlags && numericFlags[i] ? 'text-right' : null,
                label)));

            return tr;
        }

        tabular(result) {
            if (!result.rows.length) {
                return this.make('div', 'text-muted', this.translate('No data', 'labels', 'Report'));
            }

            const table = this.make('table', 'table table-bordered table-condensed');
            const thead = this.make('thead');
            const labels = [...result.columns.map(c => c.label), ...result.calculations.map(c => c.label)];
            const numeric = [...result.columns.map(c => c.numeric), ...result.calculations.map(() => true)];
            thead.appendChild(this.headerRow(labels, numeric));
            table.appendChild(thead);
            const tbody = this.make('tbody');

            result.rows.forEach(row => {
                const tr = this.make('tr');
                row.cells.forEach((value, i) => tr.appendChild(this.cell(value, row.id, result.columns[i].field === 'name',
                    result.columns[i].numeric)));
                row.calc.forEach(value => tr.appendChild(this.cell(value, null, false, true)));
                tbody.appendChild(tr);
            });

            table.appendChild(tbody);
            const totals = this.tabularTotals(result);

            if (totals) {
                table.appendChild(totals);
            }

            return table;
        }

        tabularTotals(result) {
            const functions = ['SUM', 'AVG', 'MIN', 'MAX'].filter(fn =>
                Object.values(result.totals || {}).some(t => t[fn]) ||
                Object.values(result.calculationTotals || {}).some(t => t[fn]));

            if (!functions.length) {
                return null;
            }

            const tfoot = this.make('tfoot');
            const capped = result.limits && result.limits.calculationsCapped;

            functions.forEach(fn => {
                const tr = this.make('tr');
                result.columns.forEach((column, i) => {
                    const total = (result.totals[column.key] || {})[fn];

                    if (i === 0 && !total) {
                        tr.appendChild(this.make('th', null, this.getLanguage().translateOption(fn, 'aggregateFunction',
                            'Report')));

                        return;
                    }

                    tr.appendChild(this.cell(total, null, false, true));
                });
                result.calculations.forEach(c => {
                    const td = this.cell((result.calculationTotals[c.key] || {})[fn], null, false, true);

                    if (capped && (result.calculationTotals[c.key] || {})[fn]) {
                        td.title = this.translate('calculationsCapped', 'labels', 'Report')
                            .replace('{n}', result.limits.maxRows);
                        td.classList.add('text-warning');
                    }

                    tr.appendChild(td);
                });
                tfoot.appendChild(tr);
            });

            return tfoot;
        }

        pager(result) {
            const total = result.availableRows;

            if (total <= result.maxSize && result.offset === 0) {
                return null;
            }

            const box = this.make('div', 'btn-group');
            const prev = this.make('button', 'btn btn-default btn-sm', '«');
            prev.type = 'button';
            prev.dataset.action = 'page';
            prev.dataset.offset = String(Math.max(0, result.offset - result.maxSize));
            prev.disabled = result.offset === 0;
            const next = this.make('button', 'btn btn-default btn-sm', '»');
            next.type = 'button';
            next.dataset.action = 'page';
            next.dataset.offset = String(result.offset + result.maxSize);
            next.disabled = result.offset + result.maxSize >= total;
            const info = this.make('span', 'btn btn-default btn-sm disabled',
                `${result.offset + 1}–${Math.min(total, result.offset + result.maxSize)} / ${total}`);
            box.append(prev, info, next);

            return box;
        }

        drillButton(path) {
            const button = this.make('button', 'btn btn-link btn-sm btn-icon');
            button.type = 'button';
            button.dataset.action = 'drillDown';
            button.dataset.path = JSON.stringify(path);
            button.title = this.translate('Show records', 'labels', 'Report');
            button.appendChild(this.make('span', 'fas fa-list fa-sm'));

            return button;
        }

        grouped(result) {
            if (!result.tree.length) {
                return this.make('div', 'text-muted', this.translate('No data', 'labels', 'Report'));
            }

            const table = this.make('table', 'table table-bordered table-condensed');
            const thead = this.make('thead');
            const tbody = this.make('tbody');
            const levels = result.groups.length;
            const details = result.type === 'summariesWithDetails';
            const columns = details ? result.columns : [];
            const width = Math.max(levels + result.aggregates.length, columns.length);

            if (details) {
                thead.appendChild(this.headerRow(columns.map(c => c.label), columns.map(c => c.numeric)));
            } else {
                thead.appendChild(this.headerRow([...result.groups.map(g => g.label), ...result.aggregates.map(a => a.label)],
                    [...result.groups.map(() => false), ...result.aggregates.map(() => true)]));
            }

            const addNode = (node, level, path) => {
                const nodePath = [...path, node.key.v];

                if (details) {
                    const header = this.make('tr', 'active');
                    const th = this.make('th');
                    th.colSpan = columns.length;
                    th.appendChild(document.createTextNode(result.groups[0].label + ' = '));
                    th.appendChild(this.cell(node.key).firstChild || document.createTextNode(node.key.f));
                    th.appendChild(document.createTextNode(` (${node.count})` + (result.aggregates.length ? ': ' : '') +
                        result.aggregates.map((a, i) => a.label + ' ' + node.values[i].f).join('; ')));
                    th.appendChild(this.drillButton(nodePath));
                    header.appendChild(th);
                    tbody.appendChild(header);

                    (node.rows || []).forEach(row => {
                        const tr = this.make('tr');
                        row.cells.forEach((value, i) => tr.appendChild(this.cell(value, row.id, columns[i].field === 'name',
                            columns[i].numeric)));
                        tbody.appendChild(tr);
                    });

                    return;
                }

                const tr = this.make('tr', level === 0 && levels > 1 ? 'active' : null);

                for (let i = 0; i < levels; i++) {
                    if (i === level) {
                        const td = this.cell(node.key);
                        td.appendChild(this.drillButton(nodePath));
                        tr.appendChild(td);
                    } else {
                        tr.appendChild(this.make('td'));
                    }
                }

                node.values.forEach(value => tr.appendChild(this.cell(value, null, false, true)));
                tbody.appendChild(tr);
                (node.children || []).forEach(child => addNode(child, level + 1, nodePath));
            };

            result.tree.forEach(node => addNode(node, 0, []));
            table.append(thead, tbody);

            const tfoot = this.make('tfoot');
            const total = this.make('tr');
            const label = this.make('th', null, this.translate('Total', 'labels', 'Report') + ` (${result.grandTotal.count})`);

            if (details) {
                label.colSpan = width;
                label.textContent += result.aggregates.length ? ': ' + result.aggregates
                    .map((a, i) => a.label + ' ' + result.grandTotal.values[i].f).join('; ') : '';
                total.appendChild(label);
            } else {
                label.colSpan = levels;
                total.appendChild(label);
                result.grandTotal.values.forEach(value => total.appendChild(this.cell(value, null, false, true)));
            }

            tfoot.appendChild(total);
            table.appendChild(tfoot);

            return table;
        }

        matrix(result) {
            const matrix = result.matrix;

            if (!matrix.rows.length) {
                return this.make('div', 'text-muted', this.translate('No data', 'labels', 'Report'));
            }

            const aggregates = result.aggregates;
            const span = aggregates.length;
            const table = this.make('table', 'table table-bordered table-condensed');
            const thead = this.make('thead');
            const top = this.make('tr');
            const corner = this.make('th', null, result.groups[0].label + ' \\ ' + result.groups[1].label);
            corner.rowSpan = span > 1 ? 2 : 1;
            top.appendChild(corner);

            matrix.columns.forEach(column => {
                const th = this.make('th', 'text-center');
                th.colSpan = span;
                th.appendChild(this.cell(column.key).firstChild || document.createTextNode(column.key.f));
                top.appendChild(th);
            });

            const totalHead = this.make('th', 'text-center', this.translate('Total', 'labels', 'Report'));
            totalHead.colSpan = span;
            top.appendChild(totalHead);
            thead.appendChild(top);

            if (span > 1) {
                const second = this.make('tr');
                [...matrix.columns, null].forEach(() => aggregates.forEach(a => second.appendChild(this.make('th',
                    'text-right', a.label))));
                thead.appendChild(second);
            }

            const tbody = this.make('tbody');

            matrix.rows.forEach((row, r) => {
                const tr = this.make('tr');
                const head = this.cell(row.key);
                head.appendChild(this.drillButton([row.key.v]));
                tr.appendChild(head);

                matrix.columns.forEach((column, c) => {
                    const cell = matrix.cells[r][c];
                    aggregates.forEach((a, i) => tr.appendChild(this.cell(cell ? cell.values[i] : null, null, false, true)));
                });

                row.values.forEach(value => tr.appendChild(this.cell(value, null, false, true)));
                tbody.appendChild(tr);
            });

            const tfoot = this.make('tfoot');
            const total = this.make('tr');
            total.appendChild(this.make('th', null, this.translate('Total', 'labels', 'Report')));
            matrix.columns.forEach(column => column.values.forEach(value => total.appendChild(this.cell(value, null, false,
                true))));
            result.grandTotal.values.forEach(value => total.appendChild(this.cell(value, null, false, true)));
            tfoot.appendChild(total);
            table.append(thead, tbody, tfoot);

            return table;
        }

        /**
         * Quick filter blocks: rebuilt when the options change (other conditions), the chosen values and modes kept.
         */
        renderQuickFilters(list) {
            const box = this.element.querySelector('[data-role="quick-filters"]');
            const signature = JSON.stringify(list);

            if (!box || box.dataset.signature === signature) {
                return;
            }

            box.dataset.signature = signature;
            box.innerHTML = '';

            list.forEach(filter => {
                const state = this.quick[filter.field] || {mode: 'in', values: []};
                const column = this.make('div', 'cell form-group col-sm-6');
                column.appendChild(this.make('label', 'control-label', filter.label));
                const row = this.make('div', 'input-group input-group-sm');
                const mode = this.make('select', 'form-control');

                ['in', 'notIn'].forEach(value => {
                    const option = this.make('option', null, this.translate(value === 'in' ? 'in list' : 'not in list',
                        'labels', 'Report'));
                    option.value = value;
                    option.selected = state.mode === value;
                    mode.appendChild(option);
                });

                const input = this.make('input', 'form-control');
                input.type = 'text';
                row.appendChild(input);
                column.append(row);
                const modeBox = this.make('div', 'small');
                modeBox.appendChild(mode);
                column.appendChild(modeBox);
                box.appendChild(column);

                const items = filter.options.map(option => ({
                    value: option.empty ? EMPTY : String(option.v),
                    text: option.f,
                }));
                const known = items.map(item => item.value);
                const kept = state.values.filter(value => known.includes(String(value)));

                if (this.quick[filter.field]) {
                    this.quick[filter.field].values = kept;
                }

                MultiSelect.init(input, {items: items, delimiter: ':,:', values: kept.map(String)});

                // Values stay strings: a text "false" is a text, the server reads 'true'/'false' of a flag itself.
                const update = () => {
                    const values = input.value ? input.value.split(':,:') : [];
                    this.quick[filter.field] = {mode: mode.value, values: values};
                };

                // Selectize reports a change through jQuery only; a native listener would never hear it.
                $(input).on('change', update);
                $(mode).on('change', update);
            });
        }

        drillDown(path) {
            this.createView('drillDown', 'itvolga:views/report/modals/drill-down', {
                reportId: this.model.id,
                entityType: this.result.entityType,
                path: path,
                filters: (this.lastRun || {}).filters,
                quickFilters: (this.lastRun || {}).quickFilters,
            }, view => view.render());
        }
    };
});
