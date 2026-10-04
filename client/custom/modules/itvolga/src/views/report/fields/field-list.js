/**
 * A list of fields (columns of a report, quick filters): a field is picked from the catalog with a search by
 * substring and added to the selected ones; selected fields move up and down or are removed; a field is added once.
 */
define('itvolga:views/report/fields/field-list', ['itvolga:views/report/fields/base'], (BaseView) => {

    return class extends BaseView {

        detailTemplateContent = `
            {{#if items.length}}<ol class="list-unstyled">{{#each items}}<li>{{label}}</li>{{/each}}</ol>
            {{else}}<span class="none-value">{{translate 'None'}}</span>{{/if}}`

        editTemplateContent = `
            <div class="row">
                <div class="col-sm-6">
                    <div class="input-group input-group-sm">
                        <select class="form-control itv-search" data-role="picker">
                            <option value=""></option>
                            {{#each options}}<option value="{{value}}">{{label}}</option>{{/each}}
                        </select>
                        <span class="input-group-btn"><button type="button" class="btn btn-default"
                            data-action="addItem">{{addLabel}}</button></span>
                    </div>
                </div>
                <div class="col-sm-6">
                    {{#if items.length}}
                    <table class="table table-condensed table-bordered-inside">
                        <tbody>{{#each items}}<tr>
                            <td>{{label}}</td>
                            <td class="text-right text-nowrap">
                                <button type="button" class="btn btn-link btn-sm btn-icon" data-action="moveItem"
                                    data-index="{{@index}}" data-step="-1" title="{{../upLabel}}"><span
                                    class="fas fa-arrow-up"></span></button>
                                <button type="button" class="btn btn-link btn-sm btn-icon" data-action="moveItem"
                                    data-index="{{@index}}" data-step="1" title="{{../downLabel}}"><span
                                    class="fas fa-arrow-down"></span></button>
                                <button type="button" class="btn btn-link btn-sm btn-icon" data-action="removeItem"
                                    data-index="{{@index}}" title="{{../removeLabel}}"><span
                                    class="fas fa-times"></span></button>
                            </td>
                        </tr>{{/each}}</tbody>
                    </table>
                    {{else}}<span class="text-muted">{{translate 'None'}}</span>{{/if}}
                </div>
            </div>`

        /** Which catalog fields the list accepts. */
        accepts(field) {
            return field.column;
        }

        setup() {
            super.setup();

            this.addActionHandler('addItem', () => {
                const picker = this.element.querySelector('[data-role="picker"]');
                const ref = picker ? picker.value : '';

                if (ref && !this.state.includes(ref)) {
                    this.state.push(ref);
                    this.commit();
                }
            });

            this.addActionHandler('removeItem', (e, target) => {
                this.state.splice(Number(target.dataset.index), 1);
                this.commit();
            });

            this.addActionHandler('moveItem', (e, target) => {
                this.moveItem(this.state, Number(target.dataset.index), Number(target.dataset.step));
                this.commit();
            });
        }

        data() {
            return {
                ...super.data(),
                items: this.state.map(ref => ({ref: ref, label: this.label(ref)})),
                options: this.fieldOptions(field => this.accepts(field) && !this.state.includes(field.ref)),
                addLabel: this.translateReport('Add'),
                upLabel: this.translateReport('Up'),
                downLabel: this.translateReport('Down'),
                removeLabel: this.translateReport('Remove'),
            };
        }

        validateRequired() {
            if (this.isRequired() && this.state.length === 0) {
                this.showValidationMessage(this.translate('fieldIsRequired', 'messages')
                    .replace('{field}', this.getLabelText()));

                return true;
            }

            return false;
        }
    };
});
