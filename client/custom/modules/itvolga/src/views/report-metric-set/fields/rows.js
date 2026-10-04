/**
 * Rows of a key-metrics set (D-111): a label and a source — a tabular report with the record count or SUM/AVG/MIN/MAX
 * of one of its numeric columns, or a list filter of an entity (the record count): a system filter of the entity, or
 * one of the author's saved filters, whose conditions are copied into the row when chosen (core search manager → where
 * items). Rows are moved up and down; the order is the order of the dashlet. Report names are looked up for the user
 * and never stored in the set; the server checks every new or changed row on save.
 */
define('itvolga:views/report-metric-set/fields/rows', ['itvolga:views/report/fields/base', 'itvolga:report/catalog',
    'search-manager'], (BaseView, Catalog, SearchManagerModule) => {

    const SearchManager = SearchManagerModule.default || SearchManagerModule;
    const FUNCTIONS = ['COUNT', 'SUM', 'AVG', 'MIN', 'MAX'];

    return class extends BaseView {

        /** Reports of the rows as the user may read them: id → {name, columns}. */
        reports = {}
        entityTypes = []

        detailTemplateContent = `
            {{#if rows.length}}{{#each rows}}<div>{{label}} — <span class="text-muted">{{source}}</span></div>{{/each}}
            {{else}}<span class="none-value">{{noRowsLabel}}</span>{{/if}}`

        editTemplateContent = `
            {{#each rows}}<div class="panel panel-default" data-row="{{@index}}"><div class="panel-body">
                <div class="row form-group">
                    <div class="col-sm-5"><input type="text" class="form-control input-sm" data-index="{{@index}}"
                        data-key="label" value="{{label}}" maxlength="150" placeholder="{{../labelTitle}}"></div>
                    <div class="col-sm-4"><select class="form-control input-sm" data-index="{{@index}}" data-key="source">
                        {{#each sourceOptions}}<option value="{{value}}" {{#if selected}}selected{{/if}}>{{label}}</option>{{/each}}
                    </select></div>
                    <div class="col-sm-3 text-nowrap text-right">
                        <button type="button" class="btn btn-link btn-sm btn-icon" data-action="moveItem" data-index="{{@index}}"
                            data-step="-1" title="{{../upLabel}}"><span class="fas fa-arrow-up"></span></button>
                        <button type="button" class="btn btn-link btn-sm btn-icon" data-action="moveItem" data-index="{{@index}}"
                            data-step="1" title="{{../downLabel}}"><span class="fas fa-arrow-down"></span></button>
                        <button type="button" class="btn btn-link btn-sm btn-icon" data-action="removeItem" data-index="{{@index}}"
                            title="{{../removeLabel}}"><span class="fas fa-times"></span></button>
                    </div>
                </div>
                {{#if isReport}}<div class="row">
                    <div class="col-sm-5"><button type="button" class="btn btn-default btn-sm" data-action="selectReport"
                        data-index="{{@index}}"><span class="fas fa-search fa-sm"></span> {{../selectReportLabel}}</button>
                        <span data-role="report-name">{{reportName}}</span></div>
                    <div class="col-sm-3"><select class="form-control input-sm" data-index="{{@index}}" data-key="function">
                        {{#each functionOptions}}<option value="{{value}}" {{#if selected}}selected{{/if}}>{{label}}</option>{{/each}}
                    </select></div>
                    <div class="col-sm-4">{{#unless isCount}}<select class="form-control input-sm" data-index="{{@index}}"
                        data-key="column">{{#each columnOptions}}<option value="{{value}}" {{#if selected}}selected{{/if}}>{{label}}</option>{{/each}}
                    </select>{{/unless}}</div>
                </div>{{else}}<div class="row">
                    <div class="col-sm-5"><select class="form-control input-sm" data-index="{{@index}}" data-key="entityType">
                        <option value=""></option>
                        {{#each entityOptions}}<option value="{{value}}" {{#if selected}}selected{{/if}}>{{label}}</option>{{/each}}
                    </select></div>
                    <div class="col-sm-7"><select class="form-control input-sm" data-index="{{@index}}" data-key="filter">
                        <option value=""></option>
                        {{#each filterGroups}}<optgroup label="{{label}}">{{#each options}}<option value="{{value}}"
                            {{#if selected}}selected{{/if}}>{{label}}</option>{{/each}}</optgroup>{{/each}}
                    </select></div>
                </div>{{/if}}
            </div></div>{{/each}}
            <button type="button" class="btn btn-default btn-sm" data-action="addItem">
                <span class="fas fa-plus fa-sm"></span> {{addLabel}}</button>`

        setup() {
            super.setup();

            this.addActionHandler('addItem', () => {
                this.state.push({label: '', source: 'report', reportId: null, function: 'COUNT', column: null});
                this.commit();
            });

            this.addActionHandler('removeItem', (e, target) => {
                this.state.splice(Number(target.dataset.index), 1);
                this.commit();
            });

            this.addActionHandler('moveItem', (e, target) => {
                this.moveItem(this.state, Number(target.dataset.index), Number(target.dataset.step));
                this.commit();
            });

            this.addActionHandler('selectReport', (e, target) => this.selectReport(Number(target.dataset.index)));

            this.addHandler('change', 'input[data-key="label"]', (e, target) => {
                this.state[Number(target.dataset.index)].label = target.value;
                this.commit(false);
            });

            this.addHandler('change', 'select[data-key]', (e, target) => this.change(Number(target.dataset.index),
                target.dataset.key, target.value));
        }

        /** The set has no main entity: the catalogs are those of the sources. */
        loadCatalog() {
            return Promise.all([
                Catalog.entityTypes().then(list => this.entityTypes = list).catch(() => this.entityTypes = []),
                ...this.state.filter(row => row.source === 'report' && row.reportId)
                    .map(row => this.loadReport(row.reportId)),
            ]);
        }

        /** A report of a row: its name, entity and numeric columns, as the user may read it. */
        async loadReport(id) {
            if (this.reports[id]) {
                return this.reports[id];
            }

            try {
                const report = await Espo.Ajax.getRequest('Report/' + encodeURIComponent(id));
                const catalog = await Catalog.get(report.entityType);

                this.reports[id] = {
                    name: report.name,
                    columns: (report.columns || []).filter(ref => catalog.byRef[ref] && catalog.byRef[ref].aggregate)
                        .map(ref => ({value: ref, label: Catalog.label(catalog, ref)})),
                };
            } catch (xhr) {
                if (xhr && typeof xhr === 'object') {
                    xhr.errorIsHandled = true;
                }

                this.reports[id] = {name: null, columns: []};
            }

            return this.reports[id];
        }

        selectReport(index) {
            this.createView('selectReport', 'views/modals/select-records', {
                entityType: 'Report',
                multiple: false,
                createButton: false,
                filters: {type: {type: 'in', value: ['tabular'], data: {type: 'anyOf', valueList: ['tabular']}}},
            }, view => {
                view.render();
                this.listenToOnce(view, 'select', async model => {
                    const selected = Array.isArray(model) ? model[0] : model;
                    await this.loadReport(selected.id);
                    const row = this.state[index];
                    Object.assign(row, {reportId: selected.id, function: 'COUNT', column: null});

                    if (!row.label) {
                        row.label = this.reports[selected.id].name || selected.get('name');
                    }

                    this.commit();
                });
            });
        }

        change(index, key, value) {
            const row = this.state[index];

            if (key === 'source') {
                this.state[index] = value === 'report' ?
                    {id: row.id, label: row.label, source: 'report', reportId: null, function: 'COUNT', column: null} :
                    {id: row.id, label: row.label, source: 'filter', entityType: null, function: 'COUNT', filter: null,
                        where: []};
            } else if (key === 'function') {
                const columns = (this.reports[row.reportId] || {columns: []}).columns;
                row.function = value;
                row.column = value === 'COUNT' ? null : (row.column || (columns[0] ? columns[0].value : null));
            } else if (key === 'column') {
                row.column = value;
            } else if (key === 'entityType') {
                Object.assign(row, {entityType: value || null, filter: null, where: []});
            } else if (key === 'filter') {
                this.chooseFilter(row, value);
            }

            this.commit(key !== 'column');
        }

        /**
         * A system filter is kept by name; a saved filter of the author is copied: its conditions as the core list
         * would send them, its label only for showing.
         */
        chooseFilter(row, value) {
            const [kind, name] = [value.slice(0, value.indexOf(':')), value.slice(value.indexOf(':') + 1)];

            if (kind === 'system') {
                row.filter = {kind: 'system', name: name};
                row.where = [{type: 'primary', value: name}];

                return;
            }

            const preset = this.presets(row.entityType).find(p => p.id === name);

            if (!preset) {
                row.filter = null;
                row.where = [];

                return;
            }

            const manager = new SearchManager(null, {scope: row.entityType, defaultData: {
                advanced: Espo.Utils.cloneDeep(preset.data || {}), primary: preset.primary || null, bool: {},
                textFilter: ''}});

            row.filter = {kind: 'preset', name: preset.label || preset.name};
            row.where = manager.getWhere();
        }

        presets(entityType) {
            return ((this.getPreferences().get('presetFilters') || {})[entityType] || []).filter(p => p && p.id);
        }

        systemFilters(entityType) {
            return (this.getMetadata().get(['clientDefs', entityType, 'filterList']) || [])
                .map(item => typeof item === 'string' ? item : item && item.name)
                .filter(name => name && name !== 'all');
        }

        filterGroups(row) {
            if (!row.entityType) {
                return [];
            }

            const current = row.filter || {};
            const system = this.systemFilters(row.entityType).map(name => ({value: 'system:' + name,
                label: this.translate(name, 'presetFilters', row.entityType),
                selected: current.kind === 'system' && current.name === name}));
            const presets = this.presets(row.entityType).map(p => ({value: 'preset:' + p.id, label: p.label || p.name,
                selected: false}));

            // The copy stored in the row stays shown as chosen: the preset itself may have changed or gone.
            if (current.kind === 'preset') {
                presets.unshift({value: 'kept:', label: current.name, selected: true});
            }

            return [
                {label: this.translate('System filters', 'labels', 'ReportMetricSet'), options: system},
                {label: this.translate('My filters', 'labels', 'ReportMetricSet'), options: presets},
            ].filter(group => group.options.length);
        }

        sourceText(row) {
            const lang = this.getLanguage();

            if (row.source === 'report') {
                const report = this.reports[row.reportId] || {};
                const name = report.name || this.translate('statusForbidden', 'labels', 'ReportMetricSet');
                const fn = lang.translateOption(row.function, 'aggregateFunction', 'Report');
                const column = row.column ? ((report.columns || []).find(c => c.value === row.column) || {label: row.column})
                    .label : null;

                return `${this.translate('Report', 'labels', 'ReportMetricSet')} «${name}»: ${fn}` +
                    (column ? ` (${column})` : '');
            }

            const entity = (this.entityTypes.find(e => e.entityType === row.entityType) || {}).label ||
                this.translate(row.entityType || '', 'scopeNamesPlural');
            const filter = row.filter ? (row.filter.kind === 'system' ?
                this.translate(row.filter.name, 'presetFilters', row.entityType) : row.filter.name) : '';

            return `${entity}: ${filter}`;
        }

        fetch() {
            return {[this.name]: this.state.map(row => {
                const clean = {...row};

                if (!clean.id) {
                    delete clean.id;
                }

                return clean;
            })};
        }

        data() {
            const lang = this.getLanguage();

            return {
                ...super.data(),
                rows: this.state.map(row => {
                    const report = this.reports[row.reportId] || {columns: []};

                    return {
                        label: row.label,
                        source: this.sourceText(row),
                        isReport: row.source === 'report',
                        isCount: row.function === 'COUNT',
                        reportName: row.reportId ? (report.name || '…') : '',
                        sourceOptions: ['report', 'filter'].map(value => ({value: value,
                            label: lang.translateOption(value, 'source', 'ReportMetricSet'), selected: value === row.source})),
                        functionOptions: FUNCTIONS.map(fn => ({value: fn,
                            label: lang.translateOption(fn, 'aggregateFunction', 'Report'), selected: fn === row.function})),
                        columnOptions: report.columns.map(c => ({...c, selected: c.value === row.column})),
                        entityOptions: this.entityTypes.map(e => ({value: e.entityType, label: e.label,
                            selected: e.entityType === row.entityType})),
                        filterGroups: this.filterGroups(row),
                    };
                }),
                labelTitle: this.translate('Label', 'labels', 'ReportMetricSet'),
                selectReportLabel: this.translate('Select report', 'labels', 'ReportMetricSet'),
                addLabel: this.translate('Add Row', 'labels', 'ReportMetricSet'),
                upLabel: this.translate('Up', 'labels', 'ReportMetricSet'),
                downLabel: this.translate('Down', 'labels', 'ReportMetricSet'),
                removeLabel: this.translate('Remove', 'labels', 'ReportMetricSet'),
                noRowsLabel: this.translate('No rows', 'labels', 'ReportMetricSet'),
            };
        }
    };
});
