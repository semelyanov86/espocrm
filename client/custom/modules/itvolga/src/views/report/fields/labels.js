/**
 * Overrides of headers: columns, group levels, aggregates and calculations; an empty label restores the standard one.
 * Keys: "c:<column>", "g:<level>", "a:<aggregate key>", "k:<calculation id>" (reports.md §2).
 */
define('itvolga:views/report/fields/labels', ['itvolga:views/report/fields/base',
    'itvolga:views/report/fields/aggregate-options'], (BaseView, AggregateOptions) => {

    return class extends BaseView {

        dependsOn = ['columns', 'groups', 'aggregates', 'calculations', 'type']

        emptyValue() {
            return {};
        }

        detailTemplateContent = `
            {{#if items.length}}{{#each items}}<div><span class="text-muted">{{standard}}</span> → {{value}}</div>{{/each}}
            {{else}}<span class="none-value">{{translate 'None'}}</span>{{/if}}`

        editTemplateContent = `
            {{#if rows.length}}<table class="table table-condensed table-bordered-inside"><tbody>
                {{#each rows}}<tr><td class="text-muted">{{standard}}</td><td><input type="text" class="form-control input-sm"
                    data-key="{{key}}" value="{{value}}" placeholder="{{standard}}" maxlength="150"></td></tr>{{/each}}
            </tbody></table>{{else}}<span class="text-muted">{{translate 'None'}}</span>{{/if}}`

        keys() {
            const type = this.model.get('type');
            const result = [];

            if (['tabular', 'summariesWithDetails'].includes(type)) {
                (this.model.get('columns') || []).forEach(ref => result.push({key: 'c:' + ref, standard: this.label(ref)}));
            }

            if (type !== 'tabular') {
                (this.model.get('groups') || []).forEach((group, i) => result.push({key: 'g:' + (i + 1),
                    standard: this.label(group.field)}));
                AggregateOptions.list(this).forEach(a => result.push({key: 'a:' + a.key, standard: a.label}));
            }

            if (type === 'tabular') {
                (this.model.get('calculations') || []).forEach((c, i) => result.push({
                    key: 'k:' + (c.id || 'k' + (i + 1)), standard: c.label || ('k' + (i + 1))}));
            }

            return result;
        }

        setup() {
            super.setup();

            this.addHandler('change', 'input[data-key]', () => {
                this.syncInputs();
                this.commit(false);
            });
        }

        syncInputs() {
            if (!this.element || !this.isEditMode()) {
                return;
            }

            this.element.querySelectorAll('input[data-key]').forEach(input => {
                const value = input.value.trim();

                if (value) {
                    this.state[input.dataset.key] = value;
                } else {
                    delete this.state[input.dataset.key];
                }
            });
        }

        fetch() {
            this.syncInputs();
            const keys = this.keys().map(k => k.key);
            const result = {};

            Object.keys(this.state).filter(key => keys.includes(key)).forEach(key => result[key] = this.state[key]);

            return {[this.name]: result};
        }

        data() {
            const rows = this.keys().map(k => ({...k, value: this.state[k.key] || ''}));

            return {
                ...super.data(),
                rows: rows,
                items: rows.filter(row => row.value),
            };
        }
    };
});
