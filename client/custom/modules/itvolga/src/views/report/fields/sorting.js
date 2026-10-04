/**
 * Sorting of the rows: any number of «column + direction» lines over the selected columns.
 */
define('itvolga:views/report/fields/sorting', ['itvolga:views/report/fields/base'], (BaseView) => {

    return class extends BaseView {

        dependsOn = ['columns']

        detailTemplateContent = `
            {{#if items.length}}{{#each items}}<div>{{label}} — {{directionLabel}}</div>{{/each}}
            {{else}}<span class="none-value">{{translate 'None'}}</span>{{/if}}`

        editTemplateContent = `
            {{#each items}}<div class="row form-group">
                <div class="col-sm-6"><select class="form-control input-sm" data-index="{{@index}}" data-key="column">
                    {{#each columnOptions}}<option value="{{value}}" {{#if selected}}selected{{/if}}>{{label}}</option>{{/each}}
                </select></div>
                <div class="col-sm-4"><select class="form-control input-sm" data-index="{{@index}}" data-key="direction">
                    {{#each directionOptions}}<option value="{{value}}" {{#if selected}}selected{{/if}}>{{label}}</option>{{/each}}
                </select></div>
                <div class="col-sm-2"><button type="button" class="btn btn-link btn-sm btn-icon" data-action="removeItem"
                    data-index="{{@index}}" title="{{../removeLabel}}"><span class="fas fa-times"></span></button></div>
            </div>{{/each}}
            {{#if canAdd}}<button type="button" class="btn btn-default btn-sm" data-action="addItem">
                <span class="fas fa-plus fa-sm"></span> {{addLabel}}</button>{{/if}}`

        sortable() {
            return (this.model.get('columns') || []).filter(ref => {
                const field = this.catalog.byRef[ref];

                return field && field.sort;
            });
        }

        onDependencyChange() {
            const allowed = this.sortable();
            const kept = this.state.filter(item => allowed.includes(item.column));

            if (kept.length !== this.state.length) {
                this.state = kept;
                this.commit(false);
            }
        }

        setup() {
            super.setup();

            this.addActionHandler('addItem', () => {
                const free = this.sortable().filter(ref => !this.state.some(item => item.column === ref));

                if (free.length) {
                    this.state.push({column: free[0], direction: 'asc'});
                    this.commit();
                }
            });

            this.addActionHandler('removeItem', (e, target) => {
                this.state.splice(Number(target.dataset.index), 1);
                this.commit();
            });

            this.addHandler('change', 'select[data-key]', (e, target) => {
                this.state[Number(target.dataset.index)][target.dataset.key] = target.value;
                this.commit(false);
            });
        }

        data() {
            const sortable = this.sortable();
            const directions = ['asc', 'desc'];

            return {
                ...super.data(),
                items: this.state.map(item => ({
                    label: this.label(item.column),
                    directionLabel: this.getLanguage().translateOption(item.direction, 'direction', 'Report'),
                    columnOptions: sortable.map(ref => ({value: ref, label: this.label(ref), selected: ref === item.column})),
                    directionOptions: directions.map(d => ({value: d,
                        label: this.getLanguage().translateOption(d, 'direction', 'Report'), selected: d === item.direction})),
                })),
                canAdd: sortable.length > this.state.length,
                addLabel: this.translateReport('Add'),
                removeLabel: this.translateReport('Remove'),
            };
        }
    };
});
