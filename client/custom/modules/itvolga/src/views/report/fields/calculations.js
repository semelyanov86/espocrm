/**
 * Custom calculations of a tabular report: label, expression over numeric columns ({grandTotal} - {paidAmount},
 * round(x, n)) and the totals to show. The server parses the expression (reports.md §3) and reports the position of
 * an error; the builder only collects the input.
 */
define('itvolga:views/report/fields/calculations', ['itvolga:views/report/fields/base'], (BaseView) => {

    const FUNCTIONS = ['SUM', 'AVG', 'MIN', 'MAX'];

    return class extends BaseView {

        dependsOn = ['columns']

        detailTemplateContent = `
            {{#if items.length}}{{#each items}}<div><strong>{{label}}</strong> = <code>{{expression}}</code>{{#if functions}}
                <span class="text-muted">({{functions}})</span>{{/if}}</div>{{/each}}
            {{else}}<span class="none-value">{{translate 'None'}}</span>{{/if}}`

        editTemplateContent = `
            {{#each items}}<div class="row form-group">
                <div class="col-sm-3"><input type="text" class="form-control input-sm" data-index="{{@index}}" data-key="label"
                    value="{{label}}" placeholder="{{../labelLabel}}" maxlength="150"></div>
                <div class="col-sm-5"><input type="text" class="form-control input-sm" data-index="{{@index}}" data-key="expression"
                    value="{{expression}}" placeholder="{{../expressionLabel}}" maxlength="500"></div>
                <div class="col-sm-3">{{#each checks}}<label class="checkbox-inline"><input type="checkbox" data-index="{{../index}}"
                    data-function="{{fn}}" {{#if checked}}checked{{/if}}> {{label}}</label>{{/each}}</div>
                <div class="col-sm-1"><button type="button" class="btn btn-link btn-sm btn-icon" data-action="removeItem"
                    data-index="{{@index}}" title="{{../removeLabel}}"><span class="fas fa-times"></span></button></div>
            </div>{{/each}}
            <div class="text-muted small">{{hint}}</div>
            <button type="button" class="btn btn-default btn-sm" data-action="addItem">
                <span class="fas fa-plus fa-sm"></span> {{addLabel}}</button>`

        setup() {
            super.setup();

            this.addActionHandler('addItem', () => {
                this.syncInputs();
                this.state.push({label: '', expression: '', functions: []});
                this.commit();
            });

            this.addActionHandler('removeItem', (e, target) => {
                this.syncInputs();
                this.state.splice(Number(target.dataset.index), 1);
                this.commit();
            });

            this.addHandler('change', 'input[data-key]', () => {
                this.syncInputs();
                this.commit(false);
            });

            this.addHandler('change', 'input[data-function]', (e, target) => {
                const item = this.state[Number(target.dataset.index)];
                item.functions = FUNCTIONS.filter(fn => fn === target.dataset.function ? target.checked :
                    item.functions.includes(fn));
                this.commit(false);
            });
        }

        /** Inputs typed without a change event (Ctrl+S): read them into the state. */
        syncInputs() {
            if (!this.element || !this.isEditMode()) {
                return;
            }

            this.element.querySelectorAll('input[data-key]').forEach(input => {
                const item = this.state[Number(input.dataset.index)];

                if (item) {
                    item[input.dataset.key] = input.value;
                }
            });
        }

        fetch() {
            this.syncInputs();

            return super.fetch();
        }

        data() {
            const lang = this.getLanguage();

            return {
                ...super.data(),
                items: this.state.map((item, index) => ({
                    index: index,
                    label: item.label,
                    expression: item.expression,
                    functions: (item.functions || []).map(fn => lang.translateOption(fn, 'aggregateFunction', 'Report'))
                        .join(', '),
                    checks: FUNCTIONS.map(fn => ({fn: fn, label: lang.translateOption(fn, 'aggregateFunction', 'Report'),
                        checked: (item.functions || []).includes(fn)})),
                })),
                hint: this.translate('calculations', 'tooltips', 'Report'),
                labelLabel: this.translateReport('Label'),
                expressionLabel: this.translateReport('Expression'),
                addLabel: this.translateReport('Add'),
                removeLabel: this.translateReport('Remove'),
            };
        }
    };
});
