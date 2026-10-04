/**
 * Result of a report (reports.md §7) under the report info panel of the record page: the conditions (the builder's
 * condition editor on a copy of the report, so a change applies to one run until «Сохранить условия»), quick filter
 * blocks, the counters and limit notes, and the table of the report type — tabular with pages, totals and
 * calculations; summaries as nested group rows; summaries with details as group headers with records; matrix with row
 * and column totals. Values come formatted by the server (cell.f); links lead to the records; a group row opens the
 * standard record list of its records (drill-down). Only standard classes of EspoCRM are used.
 */
define('itvolga:views/report/result', ['view', 'ui/multi-select', 'itvolga:report/result-table'],
    (View, MultiSelect, ResultTable) => {


    return class extends View {

        templateContent = `
            <div class="itv-report-result">
                <div class="button-container clearfix">
                    <div class="btn-group">
                        <button type="button" class="btn btn-default btn-sm" data-action="toggleInfo">{{infoLabel}}</button>
                        <button type="button" class="btn btn-default btn-sm" data-action="toggleConditions">{{conditionsLabel}}</button>
                        <button type="button" class="btn btn-default btn-sm hidden" data-action="toggleTable"></button>
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
                <div data-role="charts-top"></div>
                <div class="panel panel-default" data-role="table-panel">
                    <div class="panel-body" data-role="table"><span class="text-muted">…</span></div>
                </div>
                <div data-role="charts-bottom"></div>
            </div>`

        setup() {
            this.result = null;
            this.offset = 0;
            this.maxSize = 50;
            this.generation = 0;
            this.quick = {};
            // Dictionaries without a prototype: a value such as '__proto__' is a plain key.
            this.quickTexts = Object.create(null);
            this.conditionsModel = this.model.clone();
            this.resultTable = new ResultTable(this);
            // Whether the table is shown under charts: the report's «collapse table» first, then the user's toggle.
            this.tableShown = null;

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
            this.addActionHandler('toggleTable', () => {
                this.tableShown = !this.tableShown;
                this.applyTableShown();
            });

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
                .map(([field, q]) => ({field: field, mode: q.mode, values: q.values, includeEmpty: q.includeEmpty}))
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
            return this.resultTable.make(tag, className, text);
        }

        renderResult() {
            const result = this.result;
            const tableBox = this.element.querySelector('[data-role="table"]');
            const notes = this.element.querySelector('[data-role="notes"]');
            const counters = this.element.querySelector('[data-role="counters"]');

            counters.textContent = ' ' + this.translate('Total records', 'labels', 'Report') + ': ' + result.recordCount;
            notes.innerHTML = '';
            this.resultTable.limitNotes(result).forEach(text => notes.appendChild(this.resultTable.make('div', null,
                text)));
            tableBox.innerHTML = '';

            const table = this.resultTable.build(result);

            if (table) {
                const wrapper = this.resultTable.make('div', 'list');
                wrapper.appendChild(table);
                tableBox.appendChild(wrapper);
            }

            if (result.type === 'tabular') {
                const pager = this.resultTable.pager(result);

                if (pager) {
                    tableBox.appendChild(pager);
                }
            }

            this.renderQuickFilters(result.quickFilters || []);
            this.renderCharts(result.charts || null);
        }

        /**
         * Charts above or below the table (D-105); a click on a chart opens the records of its group like the button
         * of a group row. The table of a report with «collapse table» starts hidden.
         */
        async renderCharts(chart) {
            this.clearView('charts');
            ['top', 'bottom'].forEach(position =>
                this.element.querySelector(`[data-role="charts-${position}"]`).innerHTML = '');
            this.element.querySelector('[data-action="toggleTable"]').classList.toggle('hidden', !chart);

            if (!chart) {
                this.tableShown = true;
                this.applyTableShown();

                return;
            }

            if (this.tableShown === null) {
                this.tableShown = !chart.collapseTable;
            }

            this.applyTableShown();

            const view = await this.createView('charts', 'itvolga:views/report/charts', {
                selector: `[data-role="charts-${chart.position}"]`,
                chart: chart,
            });

            this.listenTo(view, 'drill-down', path => this.drillDown(path));
            await view.render();
        }

        applyTableShown() {
            const button = this.element.querySelector('[data-action="toggleTable"]');

            this.element.querySelector('[data-role="table-panel"]').classList.toggle('hidden', !this.tableShown);
            button.textContent = this.translate(this.tableShown ? 'Hide table' : 'Show table', 'labels', 'Report');
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
                const state = this.quick[filter.field] || {mode: 'in', values: [], includeEmpty: false};
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

                // Options go to the widget under opaque ids ('e' — the empty item, 'v<n>' — a value): any text, also
                // one looking like a marker or holding the delimiter, stays a value. Values stay strings; the server
                // reads 'true'/'false' of a flag itself.
                // A chosen value the new conditions no longer produce stays chosen (with its last text): the shown
                // selection is the one the result was made with.
                const texts = this.quickTexts[filter.field] = this.quickTexts[filter.field] || Object.create(null);
                const values = Object.create(null);
                const items = filter.options.map((option, i) => {
                    const id = option.empty ? 'e' : 'v' + i;

                    if (!option.empty) {
                        values[id] = String(option.v);
                        texts[values[id]] = option.f;
                    } else {
                        texts[''] = option.f;
                    }

                    return {value: id, text: option.f};
                });

                state.values.filter(value => !Object.values(values).includes(value)).forEach((value, j) => {
                    const id = 'v' + (filter.options.length + j);
                    values[id] = value;
                    items.push({value: id, text: texts[value] ?? value});
                });

                if (state.includeEmpty && !items.some(item => item.value === 'e')) {
                    items.push({value: 'e', text: texts[''] ?? this.translate('None')});
                }

                MultiSelect.init(input, {items: items, delimiter: ',', values: [
                    ...Object.keys(values).filter(id => state.values.includes(values[id])),
                    ...(state.includeEmpty ? ['e'] : [])]});

                const update = () => {
                    const chosen = input.value ? input.value.split(',') : [];
                    this.quick[filter.field] = {
                        mode: mode.value,
                        values: chosen.filter(id => id !== 'e').map(id => values[id]).filter(v => v !== undefined),
                        includeEmpty: chosen.includes('e'),
                    };
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
