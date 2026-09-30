/**
 * Read-only view of the JSON archive of source Vtiger values (vtigerData, VtigerArchive.data).
 * The field is readOnly and, for vtigerData, visible to administrators only (entityAcl onlyAdmin).
 */
define('itvolga:views/fields/vtiger-data', ['views/fields/base'], (BaseFieldView) => {

    return class extends BaseFieldView {

        listTemplateContent = `{{#if isSet}}<span class="text-muted">{ … }</span>{{/if}}`
        detailTemplateContent =
            `{{#if isSet}}<pre class="itv-vtiger-data" style="max-height: 24em; overflow: auto; white-space: pre-wrap;` +
            ` word-break: break-word;">{{json}}</pre>{{else}}<span class="none-value">{{translate 'None'}}</span>{{/if}}`
        editTemplateContent = this.detailTemplateContent

        data() {
            const value = this.model.get(this.name);
            const isSet = value !== null && value !== undefined &&
                !(typeof value === 'object' && Object.keys(value).length === 0);

            return {
                ...super.data(),
                isSet: isSet,
                json: isSet ? JSON.stringify(value, null, 2) : '',
            };
        }

        setup() {
            super.setup();

            // vtigerData is onlyAdmin (entityAcl): the API does not send it to other users, and the record view
            // would show an empty «None» cell. Hide the whole cell instead.
            this.adminOnly = this.name === 'vtigerData' && !this.getUser().isAdmin();
        }

        afterRender() {
            super.afterRender();

            if (this.adminOnly && this.element) {
                this.element.closest('.cell')?.classList.add('hidden-cell');
            }
        }

        fetch() {
            return {};
        }
    };
});
