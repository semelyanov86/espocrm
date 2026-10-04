/**
 * Sort of the level-1 groups by one aggregate (then the groups are ordered by it only: top-N with the group limit).
 * Empty — by the group values.
 */
define('itvolga:views/report/fields/group-sort', ['itvolga:views/report/fields/base',
    'itvolga:views/report/fields/aggregate-options'], (BaseView, AggregateOptions) => {

    return class extends BaseView {

        dependsOn = ['aggregates']

        emptyValue() {
            return {};
        }

        detailTemplateContent = `{{#if label}}{{label}} — {{directionLabel}}{{else}}<span class="none-value">{{translate 'None'}}</span>{{/if}}`

        editTemplateContent = `
            <div class="row">
                <div class="col-sm-7"><select class="form-control input-sm" data-key="aggregate">
                    <option value="">{{noneLabel}}</option>
                    {{#each aggregateOptions}}<option value="{{key}}" {{#if selected}}selected{{/if}}>{{label}}</option>{{/each}}
                </select></div>
                <div class="col-sm-5"><select class="form-control input-sm" data-key="direction">
                    {{#each directionOptions}}<option value="{{value}}" {{#if selected}}selected{{/if}}>{{label}}</option>{{/each}}
                </select></div>
            </div>`

        onDependencyChange() {
            if (this.state.aggregate && !AggregateOptions.list(this).some(a => a.key === this.state.aggregate)) {
                this.state = {};
                this.commit(false);
            }
        }

        setup() {
            super.setup();

            this.addHandler('change', 'select[data-key]', (e, target) => {
                if (target.dataset.key === 'aggregate' && !target.value) {
                    this.state = {};
                } else {
                    this.state = {direction: 'desc', ...this.state, [target.dataset.key]: target.value};
                }

                this.commit(false);
            });
        }

        fetch() {
            return {[this.name]: this.state.aggregate ? {...this.state} : null};
        }

        data() {
            const lang = this.getLanguage();
            const options = AggregateOptions.list(this);
            const current = options.find(a => a.key === this.state.aggregate);
            const direction = this.state.direction || 'desc';

            return {
                ...super.data(),
                label: current ? current.label : null,
                directionLabel: lang.translateOption(direction, 'direction', 'Report'),
                noneLabel: this.translate('None'),
                aggregateOptions: options.map(a => ({...a, selected: a.key === this.state.aggregate})),
                directionOptions: ['desc', 'asc'].map(d => ({value: d,
                    label: lang.translateOption(d, 'direction', 'Report'), selected: d === direction})),
            };
        }
    };
});
