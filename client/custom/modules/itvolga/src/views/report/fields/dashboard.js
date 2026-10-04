/**
 * Step «Дашборд» of the builder (D-109): the field of the main filter of the dashlet «Отчёт» — an enum field or the
 * owner of the main entity, its value is chosen in the dashlet header — and the default mode of a new dashlet (the
 * chart for summary reports with charts, else the table).
 */
define('itvolga:views/report/fields/dashboard', ['itvolga:views/report/fields/base'], (BaseView) => {

    return class extends BaseView {

        dependsOn = ['type', 'charts']

        emptyValue() {
            return {filterField: null, mode: null};
        }

        readState() {
            return {...this.emptyValue(), ...super.readState()};
        }

        detailTemplateContent = `
            <div>{{filterTitle}}: {{#if filterLabel}}{{filterLabel}}{{else}}<span class="none-value">{{noneLabel}}</span>{{/if}}</div>
            <div>{{modeTitle}}: {{modeLabel}}</div>`

        editTemplateContent = `
            <div class="row">
                <div class="col-sm-6"><label class="control-label small">{{filterTitle}}</label>
                    <select class="form-control input-sm" data-key="filterField">
                    <option value="">{{noneLabel}}</option>
                    {{#each filterOptions}}<option value="{{value}}" {{#if selected}}selected{{/if}}>{{label}}</option>{{/each}}
                </select></div>
                <div class="col-sm-6"><label class="control-label small">{{modeTitle}}</label>
                    <select class="form-control input-sm" data-key="mode">
                    {{#each modeOptions}}<option value="{{value}}" {{#if selected}}selected{{/if}}>{{label}}</option>{{/each}}
                </select></div>
            </div>`

        setup() {
            super.setup();

            this.addHandler('change', 'select[data-key]', (e, target) => {
                this.state[target.dataset.key] = target.value || null;
                this.commit(false);
            });
        }

        /** Enum fields and the owner of the main entity (the quick filters the dashlet header can offer). */
        filterFields() {
            return this.catalog.fields.filter(field => field.quickFilter && !field.ref.includes('.') &&
                (field.family === 'enum' || field.ref === 'assignedUser' && field.foreignEntityType === 'User'));
        }

        hasCharts() {
            const charts = this.model.get('charts');

            return this.model.get('type') !== 'tabular' && !!charts && (charts.items || []).length > 0;
        }

        dashletMode() {
            if (this.model.get('type') === 'tabular') {
                return 'table';
            }

            return this.state.mode || (this.hasCharts() ? 'chart' : 'table');
        }

        onDependencyChange() {
            if (this.model.get('type') === 'tabular' && this.state.mode === 'chart') {
                this.state.mode = 'table';
                this.commit(false);
            }
        }

        fetch() {
            return {[this.name]: {filterField: this.state.filterField || null, mode: this.dashletMode()}};
        }

        data() {
            const lang = this.getLanguage();
            const fields = this.filterFields();
            const current = fields.find(f => f.ref === this.state.filterField);
            const modes = this.model.get('type') === 'tabular' ? ['table'] : ['chart', 'table'];

            return {
                ...super.data(),
                filterLabel: current ? current.label : (this.state.filterField || null),
                modeLabel: lang.translateOption(this.dashletMode(), 'dashboardMode', 'Report'),
                filterOptions: fields.map(f => ({value: f.ref, label: f.label, selected: f.ref === this.state.filterField})),
                modeOptions: modes.map(m => ({value: m, label: lang.translateOption(m, 'dashboardMode', 'Report'),
                    selected: m === this.dashletMode()})),
                filterTitle: this.translateReport('Main filter'),
                modeTitle: this.translateReport('Default mode'),
                noneLabel: this.translateReport('No main filter'),
            };
        }
    };
});
