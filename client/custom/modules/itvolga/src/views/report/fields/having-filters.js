/**
 * Filters by aggregates of the level-1 groups (SQL HAVING): aggregate, numeric operator, value; combined with AND.
 */
define('itvolga:views/report/fields/having-filters', ['itvolga:views/report/fields/base',
    'itvolga:views/report/fields/aggregate-options'], (BaseView, AggregateOptions) => {

    const OPERATORS = ['greaterThan', 'greaterThanOrEquals', 'lessThan', 'lessThanOrEquals', 'equals', 'notEquals',
        'between'];

    return class extends BaseView {

        dependsOn = ['aggregates']

        detailTemplateContent = `
            {{#if items.length}}{{#each items}}<div>{{label}} {{operatorLabel}} {{valueText}}</div>{{/each}}
            {{else}}<span class="none-value">{{translate 'None'}}</span>{{/if}}`

        editTemplateContent = `
            {{#each items}}<div class="row form-group">
                <div class="col-sm-5"><select class="form-control input-sm" data-index="{{@index}}" data-key="aggregate">
                    {{#each aggregateOptions}}<option value="{{key}}" {{#if selected}}selected{{/if}}>{{label}}</option>{{/each}}
                </select></div>
                <div class="col-sm-2"><select class="form-control input-sm" data-index="{{@index}}" data-key="operator">
                    {{#each operatorOptions}}<option value="{{value}}" {{#if selected}}selected{{/if}}>{{label}}</option>{{/each}}
                </select></div>
                <div class="col-sm-2"><input type="text" inputmode="decimal" class="form-control input-sm"
                    data-index="{{@index}}" data-key="value0" value="{{value0}}"></div>
                <div class="col-sm-2">{{#if isBetween}}<input type="text" inputmode="decimal" class="form-control input-sm"
                    data-index="{{@index}}" data-key="value1" value="{{value1}}">{{/if}}</div>
                <div class="col-sm-1"><button type="button" class="btn btn-link btn-sm btn-icon" data-action="removeItem"
                    data-index="{{@index}}" title="{{../removeLabel}}"><span class="fas fa-times"></span></button></div>
            </div>{{/each}}
            {{#if hasAggregates}}<button type="button" class="btn btn-default btn-sm" data-action="addItem">
                <span class="fas fa-plus fa-sm"></span> {{addLabel}}</button>{{/if}}`

        onDependencyChange() {
            const keys = AggregateOptions.list(this).map(a => a.key);
            const kept = this.state.filter(item => keys.includes(item.aggregate));

            if (kept.length !== this.state.length) {
                this.state = kept;
                this.commit(false);
            }
        }

        setup() {
            super.setup();

            this.addActionHandler('addItem', () => {
                const first = AggregateOptions.list(this)[0];

                if (first) {
                    this.syncInputs();
                    this.state.push({aggregate: first.key, operator: 'greaterThan', value: '0'});
                    this.commit();
                }
            });

            this.addActionHandler('removeItem', (e, target) => {
                this.syncInputs();
                this.state.splice(Number(target.dataset.index), 1);
                this.commit();
            });

            this.addHandler('change', 'select[data-key], input[data-key]', (e, target) => {
                this.syncInputs();
                const item = this.state[Number(target.dataset.index)];

                if (target.dataset.key === 'operator') {
                    item.value = target.value === 'between' ? [this.first(item.value), ''] : this.first(item.value);
                }

                this.commit(target.tagName === 'SELECT');
            });
        }

        first(value) {
            return Array.isArray(value) ? value[0] : (value ?? '');
        }

        /** Decimal input in the user's notation → canonical string («1 500,5» → "1500.5"); kept as typed if not a number. */
        normalize(text) {
            const value = String(text || '').replace(/[\s ]/g, '').replace(',', '.');

            return value;
        }

        syncInputs() {
            if (!this.element || !this.isEditMode()) {
                return;
            }

            this.element.querySelectorAll('select[data-key], input[data-key]').forEach(input => {
                const item = this.state[Number(input.dataset.index)];

                if (!item) {
                    return;
                }

                if (input.dataset.key === 'aggregate' || input.dataset.key === 'operator') {
                    item[input.dataset.key] = input.value;
                } else if (item.operator === 'between') {
                    const pair = Array.isArray(item.value) ? item.value : [item.value, ''];
                    pair[input.dataset.key === 'value0' ? 0 : 1] = this.normalize(input.value);
                    item.value = pair;
                } else if (input.dataset.key === 'value0') {
                    item.value = this.normalize(input.value);
                }
            });
        }

        fetch() {
            this.syncInputs();

            return super.fetch();
        }

        data() {
            const options = AggregateOptions.list(this);
            const operatorLabel = op => this.getLanguage().translateOption(op, 'havingOperator', 'Report');

            return {
                ...super.data(),
                hasAggregates: options.length > 0,
                items: this.state.map(item => ({
                    label: (options.find(a => a.key === item.aggregate) || {}).label || item.aggregate,
                    operatorLabel: operatorLabel(item.operator),
                    valueText: Array.isArray(item.value) ? item.value.join(' — ') : item.value,
                    isBetween: item.operator === 'between',
                    value0: this.first(item.value),
                    value1: Array.isArray(item.value) ? item.value[1] : '',
                    aggregateOptions: options.map(a => ({...a, selected: a.key === item.aggregate})),
                    operatorOptions: OPERATORS.map(op => ({value: op, label: operatorLabel(op),
                        selected: op === item.operator})),
                })),
                addLabel: this.translateReport('Add'),
                removeLabel: this.translateReport('Remove'),
            };
        }
    };
});
