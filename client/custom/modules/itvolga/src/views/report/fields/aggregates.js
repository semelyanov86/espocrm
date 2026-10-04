/**
 * Aggregates of the groups: the record count and SUM/AVG/MIN/MAX of numeric fields of the main or linked entities;
 * several, ordered. Stored as {"function", "link", "field"} (reports.md §2).
 */
define('itvolga:views/report/fields/aggregates', ['itvolga:views/report/fields/base'], (BaseView) => {

    const FUNCTIONS = ['COUNT', 'SUM', 'AVG', 'MIN', 'MAX'];

    return class extends BaseView {

        detailTemplateContent = `
            {{#if items.length}}{{#each items}}<div>{{label}}</div>{{/each}}
            {{else}}<span class="none-value">{{translate 'None'}}</span>{{/if}}`

        editTemplateContent = `
            {{#each items}}<div class="row form-group">
                <div class="col-sm-3"><select class="form-control input-sm" data-index="{{@index}}" data-key="function">
                    {{#each functionOptions}}<option value="{{value}}" {{#if selected}}selected{{/if}}>{{label}}</option>{{/each}}
                </select></div>
                <div class="col-sm-6">{{#unless isCount}}<select class="form-control input-sm itv-search" data-index="{{@index}}"
                    data-key="field">{{#each fieldOptions}}<option value="{{value}}" {{#if selected}}selected{{/if}}>{{label}}</option>{{/each}}
                </select>{{/unless}}</div>
                <div class="col-sm-3 text-nowrap">
                    <button type="button" class="btn btn-link btn-sm btn-icon" data-action="moveItem" data-index="{{@index}}"
                        data-step="-1" title="{{../upLabel}}"><span class="fas fa-arrow-up"></span></button>
                    <button type="button" class="btn btn-link btn-sm btn-icon" data-action="moveItem" data-index="{{@index}}"
                        data-step="1" title="{{../downLabel}}"><span class="fas fa-arrow-down"></span></button>
                    <button type="button" class="btn btn-link btn-sm btn-icon" data-action="removeItem" data-index="{{@index}}"
                        title="{{../removeLabel}}"><span class="fas fa-times"></span></button>
                </div>
            </div>{{/each}}
            <button type="button" class="btn btn-default btn-sm" data-action="addItem">
                <span class="fas fa-plus fa-sm"></span> {{addLabel}}</button>`

        static ref(item) {
            return item.field ? (item.link ? item.link + '.' + item.field : item.field) : null;
        }

        static key(item) {
            const ref = this.ref(item);

            return ref ? item.function + ':' + ref : item.function;
        }

        setup() {
            super.setup();

            this.addActionHandler('addItem', () => {
                this.state.push(this.state.some(item => item.function === 'COUNT') ?
                    this.numericItem('SUM') : {function: 'COUNT', link: null, field: null});
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

            this.addHandler('change', 'select[data-key]', (e, target) => {
                const index = Number(target.dataset.index);

                if (target.dataset.key === 'function') {
                    const item = this.state[index];
                    this.state[index] = target.value === 'COUNT' ? {function: 'COUNT', link: null, field: null} :
                        (item.field ? {...item, function: target.value} : this.numericItem(target.value));
                } else {
                    const [first, second] = target.value.split('.');
                    this.state[index] = {...this.state[index], link: second ? first : null, field: second || first};
                }

                this.commit();
            });
        }

        numericItem(fn) {
            const field = Object.values(this.catalog.byRef).find(f => f.aggregate);
            const [first, second] = field ? field.ref.split('.') : [null, null];

            return {function: fn, link: second ? first : null, field: second || first};
        }

        data() {
            const lang = this.getLanguage();

            return {
                ...super.data(),
                items: this.state.map(item => {
                    const ref = this.constructor.ref(item);
                    const fnLabel = lang.translateOption(item.function, 'aggregateFunction', 'Report');

                    return {
                        label: ref ? fnLabel + ': ' + this.label(ref) : fnLabel,
                        isCount: item.function === 'COUNT',
                        functionOptions: FUNCTIONS.map(f => ({value: f,
                            label: lang.translateOption(f, 'aggregateFunction', 'Report'), selected: f === item.function})),
                        fieldOptions: this.fieldOptions(f => f.aggregate, ref),
                    };
                }),
                addLabel: this.translateReport('Add'),
                upLabel: this.translateReport('Up'),
                downLabel: this.translateReport('Down'),
                removeLabel: this.translateReport('Remove'),
            };
        }
    };
});
