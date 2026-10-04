/**
 * Step «Графики» of the builder (D-105…D-107): common settings — title, position above or below the table, the table
 * collapsed by default, the X axis (group 1, or group 1 with the values of group 2 as series), progress lines — and up
 * to three charts, each of a type and a data series (the record count or one of the aggregates). With the second-group
 * axis there is one chart, no funnel and no progress lines; parts that stop fitting after a change of the groups or
 * aggregates are adjusted here, the server checks the rules again on save.
 */
define('itvolga:views/report/fields/charts', ['itvolga:views/report/fields/base',
    'itvolga:views/report/fields/aggregate-options'], (BaseView, AggregateOptions) => {

    const TYPES = ['bar', 'stackedBar', 'horizontalBar', 'stackedHorizontalBar', 'line', 'pie', 'piePercent', 'funnel'];
    const PROGRESS = ['MIN', 'AVG', 'MAX'];
    const MAX_ITEMS = 3;

    return class extends BaseView {

        dependsOn = ['type', 'groups', 'aggregates']

        emptyValue() {
            return {title: '', position: 'top', collapseTable: false, axis: 'group1', progressLines: [], items: []};
        }

        readState() {
            return {...this.emptyValue(), ...super.readState()};
        }

        detailTemplateContent = `
            {{#if items.length}}
                {{#if title}}<div><strong>{{title}}</strong></div>{{/if}}
                {{#each items}}<div>{{typeLabel}} — {{aggregateLabel}}</div>{{/each}}
                <div class="text-muted small">{{axisLabel}}; {{positionLabel}}{{#if collapseTable}}; {{collapseLabel}}{{/if}}
                    {{#if progressLabel}}; {{progressLabel}}{{/if}}</div>
            {{else}}<span class="none-value">{{translate 'None'}}</span>{{/if}}`

        editTemplateContent = `
            <div class="row form-group">
                <div class="col-sm-6"><label class="control-label small">{{titleLabel}}</label>
                    <input type="text" class="form-control input-sm" data-key="title" value="{{title}}" maxlength="150"></div>
                <div class="col-sm-3"><label class="control-label small">{{positionTitle}}</label>
                    <select class="form-control input-sm" data-key="position">
                    {{#each positionOptions}}<option value="{{value}}" {{#if selected}}selected{{/if}}>{{label}}</option>{{/each}}
                </select></div>
                <div class="col-sm-3"><label class="control-label small">&nbsp;</label><div class="checkbox">
                    <label><input type="checkbox" data-key="collapseTable" {{#if collapseTable}}checked{{/if}}> {{collapseLabel}}</label>
                </div></div>
            </div>
            <div class="row form-group">
                <div class="col-sm-6"><label class="control-label small">{{axisTitle}}</label>
                    <select class="form-control input-sm" data-key="axis">
                    {{#each axisOptions}}<option value="{{value}}" {{#if selected}}selected{{/if}}>{{label}}</option>{{/each}}
                </select></div>
                <div class="col-sm-6"><label class="control-label small">{{progressTitle}}</label><div>
                    {{#each progressOptions}}<label class="checkbox-inline"><input type="checkbox" data-progress="{{value}}"
                        {{#if checked}}checked{{/if}} {{#if ../progressDisabled}}disabled{{/if}}> {{label}}</label>{{/each}}
                </div></div>
            </div>
            {{#each items}}<div class="row form-group" data-chart="{{@index}}">
                <div class="col-sm-4"><select class="form-control input-sm" data-index="{{@index}}" data-key="type">
                    {{#each typeOptions}}<option value="{{value}}" {{#if selected}}selected{{/if}}
                        {{#if disabled}}disabled{{/if}}>{{label}}</option>{{/each}}
                </select></div>
                <div class="col-sm-5"><select class="form-control input-sm" data-index="{{@index}}" data-key="aggregate">
                    {{#each aggregateOptions}}<option value="{{key}}" {{#if selected}}selected{{/if}}>{{label}}</option>{{/each}}
                </select></div>
                <div class="col-sm-3 text-nowrap">
                    <button type="button" class="btn btn-link btn-sm btn-icon" data-action="moveItem" data-index="{{@index}}"
                        data-step="-1" title="{{../upLabel}}"><span class="fas fa-arrow-up"></span></button>
                    <button type="button" class="btn btn-link btn-sm btn-icon" data-action="moveItem" data-index="{{@index}}"
                        data-step="1" title="{{../downLabel}}"><span class="fas fa-arrow-down"></span></button>
                    <button type="button" class="btn btn-link btn-sm btn-icon" data-action="removeItem" data-index="{{@index}}"
                        title="{{../removeLabel}}"><span class="fas fa-times"></span></button>
                </div>
            </div>{{/each}}
            {{#if canAdd}}<button type="button" class="btn btn-default btn-sm" data-action="addItem">
                <span class="fas fa-plus fa-sm"></span> {{addLabel}}</button>{{/if}}`

        setup() {
            super.setup();

            this.addActionHandler('addItem', () => {
                if (this.state.items.length < this.maxItems()) {
                    this.state.items.push({type: 'bar', aggregate: this.defaultAggregate()});
                    this.commit();
                }
            });

            this.addActionHandler('removeItem', (e, target) => {
                this.state.items.splice(Number(target.dataset.index), 1);
                this.commit();
            });

            this.addActionHandler('moveItem', (e, target) => {
                this.moveItem(this.state.items, Number(target.dataset.index), Number(target.dataset.step));
                this.commit();
            });

            this.addHandler('change', 'input[data-key="title"]', (e, target) => {
                this.state.title = target.value;
                this.commit(false);
            });

            this.addHandler('change', 'input[data-key="collapseTable"]', (e, target) => {
                this.state.collapseTable = target.checked;
                this.commit(false);
            });

            this.addHandler('change', 'input[data-progress]', () => {
                this.state.progressLines = PROGRESS.filter(fn =>
                    this.element.querySelector(`input[data-progress="${fn}"]`).checked);
                this.commit(false);
            });

            this.addHandler('change', 'select[data-key]', (e, target) => {
                const key = target.dataset.key;

                if (target.dataset.index !== undefined) {
                    this.state.items[Number(target.dataset.index)][key] = target.value;
                } else {
                    this.state[key] = target.value;
                }

                this.normalise();
                this.commit(['axis', 'type'].includes(key));
            });
        }

        /** The axis «group 1 → group 2»: summaries with two or more levels, or a matrix (D-106). */
        secondAxisAllowed() {
            const type = this.model.get('type');

            return type === 'matrix' || type === 'summaries' && (this.model.get('groups') || []).length >= 2;
        }

        maxItems() {
            return this.state.axis === 'group1group2' ? 1 : MAX_ITEMS;
        }

        aggregateOptions() {
            return [{key: 'COUNT', label: this.translateReport('Record count')},
                ...AggregateOptions.list(this).filter(a => a.key !== 'COUNT')];
        }

        defaultAggregate() {
            return 'COUNT';
        }

        /** Adjusts the state to the rules after a change of the axis, the type, the groups or the aggregates. */
        normalise() {
            const keys = this.aggregateOptions().map(a => a.key);

            if (this.state.axis === 'group1group2' && !this.secondAxisAllowed()) {
                this.state.axis = 'group1';
            }

            this.state.items.forEach(item => {
                if (!keys.includes(item.aggregate)) {
                    item.aggregate = 'COUNT';
                }
            });

            if (this.state.axis === 'group1group2') {
                this.state.items = this.state.items.slice(0, 1);
                this.state.items.forEach(item => item.type = item.type === 'funnel' ? 'bar' : item.type);
                this.state.progressLines = [];
            }
        }

        onDependencyChange() {
            this.normalise();
            this.commit(false);
        }

        data() {
            const lang = this.getLanguage();
            const option = (value, field) => lang.translateOption(value, field, 'Report');
            const aggregates = this.aggregateOptions();
            const second = this.state.axis === 'group1group2';

            return {
                ...super.data(),
                title: this.state.title,
                collapseTable: this.state.collapseTable,
                items: this.state.items.map(item => ({
                    typeLabel: option(item.type, 'chartType'),
                    aggregateLabel: (aggregates.find(a => a.key === item.aggregate) || {label: item.aggregate}).label,
                    typeOptions: TYPES.map(type => ({value: type, label: option(type, 'chartType'),
                        selected: type === item.type, disabled: second && type === 'funnel'})),
                    aggregateOptions: aggregates.map(a => ({...a, selected: a.key === item.aggregate})),
                })),
                positionOptions: ['top', 'bottom'].map(value => ({value: value, label: option(value, 'chartPosition'),
                    selected: value === this.state.position})),
                axisOptions: ['group1', ...(this.secondAxisAllowed() ? ['group1group2'] : [])].map(value => ({
                    value: value, label: option(value, 'chartAxis'), selected: value === this.state.axis})),
                progressOptions: PROGRESS.map(fn => ({value: fn, label: option(fn, 'progressLine'),
                    checked: this.state.progressLines.includes(fn)})),
                progressDisabled: second,
                canAdd: this.state.items.length < this.maxItems(),
                axisLabel: option(this.state.axis, 'chartAxis'),
                positionLabel: option(this.state.position, 'chartPosition'),
                progressLabel: this.state.progressLines.map(fn => option(fn, 'progressLine')).join(', '),
                titleLabel: this.translateReport('Chart title'),
                positionTitle: this.translateReport('Chart position'),
                collapseLabel: this.translateReport('Collapse table'),
                axisTitle: this.translateReport('X axis'),
                progressTitle: this.translateReport('Progress lines'),
                addLabel: this.translateReport('Add Chart'),
                upLabel: this.translateReport('Up'),
                downLabel: this.translateReport('Down'),
                removeLabel: this.translateReport('Remove'),
            };
        }
    };
});
