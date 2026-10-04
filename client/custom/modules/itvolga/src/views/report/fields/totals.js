/**
 * Totals of the numeric columns of a tabular report: SUM, AVG, MIN, MAX over all the rows of the conditions (the row
 * limit and the page do not apply).
 */
define('itvolga:views/report/fields/totals', ['itvolga:views/report/fields/base'], (BaseView) => {

    const FUNCTIONS = ['SUM', 'AVG', 'MIN', 'MAX'];

    return class extends BaseView {

        dependsOn = ['columns']

        detailTemplateContent = `
            {{#if items.length}}{{#each items}}<div>{{label}}: {{functions}}</div>{{/each}}
            {{else}}<span class="none-value">{{translate 'None'}}</span>{{/if}}`

        editTemplateContent = `
            {{#if rows.length}}<table class="table table-condensed table-bordered-inside">
                <thead><tr><th>{{columnLabel}}</th>{{#each functionLabels}}<th class="text-center">{{this}}</th>{{/each}}</tr></thead>
                <tbody>{{#each rows}}<tr><td>{{label}}</td>{{#each checks}}<td class="text-center"><input type="checkbox"
                    data-ref="{{../ref}}" data-function="{{fn}}" {{#if checked}}checked{{/if}}></td>{{/each}}</tr>{{/each}}</tbody>
            </table>{{else}}<span class="text-muted">{{noNumericLabel}}</span>{{/if}}`

        numericColumns() {
            return (this.model.get('columns') || []).filter(ref => (this.catalog.byRef[ref] || {}).aggregate);
        }

        onDependencyChange() {
            const allowed = this.numericColumns();
            const kept = this.state.filter(item => allowed.includes(item.column));

            if (kept.length !== this.state.length) {
                this.state = kept;
                this.commit(false);
            }
        }

        setup() {
            super.setup();

            this.addHandler('change', 'input[data-function]', (e, target) => {
                const ref = target.dataset.ref;
                let item = this.state.find(i => i.column === ref);

                if (!item) {
                    item = {column: ref, functions: []};
                    this.state.push(item);
                }

                item.functions = FUNCTIONS.filter(fn => fn === target.dataset.function ? target.checked :
                    item.functions.includes(fn));
                this.state = this.state.filter(i => i.functions.length);
                this.commit(false);
            });
        }

        data() {
            const lang = this.getLanguage();

            return {
                ...super.data(),
                items: this.state.map(item => ({label: this.label(item.column),
                    functions: item.functions.map(fn => lang.translateOption(fn, 'aggregateFunction', 'Report')).join(', ')})),
                rows: this.numericColumns().map(ref => {
                    const item = this.state.find(i => i.column === ref) || {functions: []};

                    return {ref: ref, label: this.label(ref),
                        checks: FUNCTIONS.map(fn => ({fn: fn, checked: item.functions.includes(fn)}))};
                }),
                functionLabels: FUNCTIONS.map(fn => lang.translateOption(fn, 'aggregateFunction', 'Report')),
                columnLabel: this.translateReport('Column'),
                noNumericLabel: this.translateReport('noNumericColumns'),
            };
        }
    };
});
