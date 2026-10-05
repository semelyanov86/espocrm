/**
 * The mark of a report with an active mailing in the reports list (05.3): an envelope with the next run as its title.
 */
define('itvolga:views/report/fields/mailing-next-run', ['views/fields/base'], (BaseFieldView) => {

    return class extends BaseFieldView {

        listTemplateContent = `{{#if value}}<span class="fas fa-envelope text-muted" title="{{title}}"></span>{{/if}}`
        detailTemplateContent = `{{#if value}}{{text}}{{else}}<span class="none-value">{{none}}</span>{{/if}}`

        data() {
            const value = this.model.get(this.name);
            const text = value ? this.getDateTime().toDisplay(value) : '';

            return {
                value: value,
                text: text,
                title: this.translate('mailingNextRunAt', 'fields', 'Report') + ': ' + text,
                none: this.translate('mailingOff', 'labels', 'Report'),
            };
        }
    };
});
