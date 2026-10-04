/**
 * Grouping: up to three levels «group by → then by → finally by», each with its direction and, for dates, the
 * granularity; level N is offered only after level N-1. Summaries with details have one level, a matrix exactly two
 * (the second one is the column axis).
 */
define('itvolga:views/report/fields/groups', ['itvolga:views/report/fields/base'], (BaseView) => {

    const GRANULARITIES = ['day', 'week', 'month', 'quarter', 'halfYear', 'year'];

    return class extends BaseView {

        dependsOn = ['type']

        detailTemplateContent = `
            {{#if items.length}}{{#each items}}<div><span class="text-muted">{{levelLabel}}:</span> {{label}}{{#if granularityLabel}}
                ({{granularityLabel}}){{/if}} — {{directionLabel}}</div>{{/each}}
            {{else}}<span class="none-value">{{translate 'None'}}</span>{{/if}}`

        editTemplateContent = `
            {{#each items}}<div class="row form-group">
                <div class="col-sm-2"><label class="control-label">{{levelLabel}}</label></div>
                <div class="col-sm-4"><select class="form-control input-sm itv-search" data-index="{{@index}}" data-key="field">
                    {{#each fieldOptions}}<option value="{{value}}" {{#if selected}}selected{{/if}}>{{label}}</option>{{/each}}
                </select></div>
                <div class="col-sm-2">{{#if isDate}}<select class="form-control input-sm" data-index="{{@index}}" data-key="granularity">
                    {{#each granularityOptions}}<option value="{{value}}" {{#if selected}}selected{{/if}}>{{label}}</option>{{/each}}
                </select>{{/if}}</div>
                <div class="col-sm-3"><select class="form-control input-sm" data-index="{{@index}}" data-key="direction">
                    {{#each directionOptions}}<option value="{{value}}" {{#if selected}}selected{{/if}}>{{label}}</option>{{/each}}
                </select></div>
                <div class="col-sm-1">{{#if isLast}}<button type="button" class="btn btn-link btn-sm btn-icon"
                    data-action="removeItem" title="{{../removeLabel}}"><span class="fas fa-times"></span></button>{{/if}}</div>
            </div>{{/each}}
            {{#if canAdd}}<button type="button" class="btn btn-default btn-sm" data-action="addItem">
                <span class="fas fa-plus fa-sm"></span> {{addLabel}}</button>{{/if}}`

        maxLevels() {
            return {tabular: 0, summaries: 3, summariesWithDetails: 1, matrix: 2}[this.model.get('type')] ?? 3;
        }

        onDependencyChange() {
            if (this.state.length > this.maxLevels()) {
                this.state = this.state.slice(0, this.maxLevels());
                this.commit(false);
            }
        }

        setup() {
            super.setup();

            this.addActionHandler('addItem', () => {
                const first = this.catalog.fields.find(field => field.group) ||
                    Object.values(this.catalog.byRef).find(field => field.group);

                if (first && this.state.length < this.maxLevels()) {
                    this.state.push({field: first.ref, granularity: first.date ? 'month' : null, direction: 'asc'});
                    this.commit();
                }
            });

            this.addActionHandler('removeItem', () => {
                this.state.pop();
                this.commit();
            });

            this.addHandler('change', 'select[data-key]', (e, target) => {
                const item = this.state[Number(target.dataset.index)];
                item[target.dataset.key] = target.value;

                if (target.dataset.key === 'field') {
                    const field = this.catalog.byRef[target.value];
                    item.granularity = field && field.date ? (item.granularity || 'month') : null;
                }

                this.commit(target.dataset.key === 'field');
            });
        }

        levelLabel(index) {
            if (this.model.get('type') === 'matrix') {
                return this.translateReport(index === 0 ? 'Rows axis' : 'Columns axis');
            }

            return this.translateReport(['Group by', 'Then by', 'Finally by'][index]);
        }

        data() {
            const lang = this.getLanguage();

            return {
                ...super.data(),
                items: this.state.map((item, index) => {
                    const field = this.catalog.byRef[item.field] || {};

                    return {
                        levelLabel: this.levelLabel(index),
                        label: this.label(item.field),
                        isDate: !!field.date,
                        isLast: index === this.state.length - 1,
                        granularityLabel: item.granularity ? lang.translateOption(item.granularity, 'granularity', 'Report') : null,
                        directionLabel: lang.translateOption(item.direction, 'direction', 'Report'),
                        fieldOptions: this.fieldOptions(f => f.group, item.field),
                        granularityOptions: GRANULARITIES.map(g => ({value: g,
                            label: lang.translateOption(g, 'granularity', 'Report'), selected: g === item.granularity})),
                        directionOptions: ['asc', 'desc'].map(d => ({value: d,
                            label: lang.translateOption(d, 'direction', 'Report'), selected: d === item.direction})),
                    };
                }),
                canAdd: this.state.length < this.maxLevels(),
                addLabel: this.translateReport('Add'),
                removeLabel: this.translateReport('Remove'),
            };
        }
    };
});
