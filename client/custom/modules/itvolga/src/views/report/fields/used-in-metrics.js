/**
 * The mark of a report used by a key-metrics set (D-115): an icon in the reports list.
 */
define('itvolga:views/report/fields/used-in-metrics', ['views/fields/base'], (BaseFieldView) => {

    return class extends BaseFieldView {

        listTemplateContent = `{{#if used}}<span class="fas fa-tachometer-alt text-muted" title="{{title}}"></span>{{/if}}`
        detailTemplateContent = `{{#if used}}<span class="fas fa-tachometer-alt text-muted" title="{{title}}"></span>{{/if}}`

        data() {
            return {
                used: !!this.model.get(this.name),
                title: this.translate('usedInMetrics', 'labels', 'Report'),
            };
        }
    };
});
