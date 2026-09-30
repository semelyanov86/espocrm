/**
 * AnyDesk password of ContactAccess. The API never returns the value with the record (entityAcl internal);
 * «Показать пароль» calls POST /ContactAccess/:id/password, which checks access and writes an Action History
 * record. The revealed value lives only in the DOM for 30 seconds and is never put into the model; a value typed
 * in the form is removed from the model once it is saved.
 */
define('itvolga:views/contact-access/fields/password', ['views/fields/password'], (PasswordFieldView) => {

    const REVEAL_SECONDS = 30;

    return class extends PasswordFieldView {

        detailTemplateContent = `
            {{#if hasPassword}}
                <span data-role="value" class="text-monospace">••••••••</span>
                <span data-role="controls" style="margin-left: 0.5em;">
                    <a role="button" tabindex="0" data-action="revealPassword" class="small">
                        {{translate 'Show password' scope='ContactAccess'}}</a>
                    <a role="button" tabindex="0" data-action="copyPassword" class="small hidden"
                        style="margin-left: 0.5em;">{{translate 'Copy password' scope='ContactAccess'}}</a>
                    <a role="button" tabindex="0" data-action="hidePassword" class="small hidden"
                        style="margin-left: 0.5em;">{{translate 'Hide password' scope='ContactAccess'}}</a>
                </span>
            {{else}}
                <span class="none-value">{{translate 'Password is not set' scope='ContactAccess'}}</span>
            {{/if}}`

        listTemplateContent = `{{#if hasPassword}}••••••••{{/if}}`

        setup() {
            super.setup();

            this.revealed = null;
            this.hideTimer = null;

            this.addActionHandler('revealPassword', () => this.revealPassword());
            this.addActionHandler('hidePassword', () => this.hidePassword());
            this.addActionHandler('copyPassword', () => this.copyPassword());

            this.listenTo(this.model, 'change:hasAnydeskPassword', () => {
                if (this.isDetailMode()) {
                    this.reRender();
                }
            });

            this.once('remove', () => this.hidePassword());

            // A value typed in the form is sent once; it must not stay in the client model after saving.
            this.listenTo(this.model, 'sync', () => this.forgetPlainValue());
        }

        forgetPlainValue() {
            if (this.model.has(this.name)) {
                this.model.unset(this.name, {silent: true});
            }

            if (this.model._previousAttributes) {
                delete this.model._previousAttributes[this.name];
            }

            const input = this.element ? this.element.querySelector('input') : null;

            if (input) {
                input.value = '';
            }
        }

        data() {
            return {
                ...super.data(),
                hasPassword: Boolean(this.model.get('hasAnydeskPassword')),
            };
        }

        async revealPassword() {
            const response = await Espo.Ajax.postRequest(`ContactAccess/${this.model.id}/password`, {});

            if (!this.element) {
                return;
            }

            this.revealed = response.password ?? '';
            this.element.querySelector('[data-role="value"]').textContent = this.revealed;
            this.element.querySelector('[data-action="revealPassword"]').classList.add('hidden');
            this.element.querySelector('[data-action="copyPassword"]').classList.remove('hidden');
            this.element.querySelector('[data-action="hidePassword"]').classList.remove('hidden');

            clearTimeout(this.hideTimer);
            this.hideTimer = setTimeout(() => this.hidePassword(), REVEAL_SECONDS * 1000);
        }

        hidePassword() {
            clearTimeout(this.hideTimer);
            this.revealed = null;

            if (!this.element || !this.isDetailMode()) {
                return;
            }

            const value = this.element.querySelector('[data-role="value"]');

            if (!value) {
                return;
            }

            value.textContent = '••••••••';
            this.element.querySelector('[data-action="revealPassword"]').classList.remove('hidden');
            this.element.querySelector('[data-action="copyPassword"]').classList.add('hidden');
            this.element.querySelector('[data-action="hidePassword"]').classList.add('hidden');
        }

        copyPassword() {
            if (this.revealed === null) {
                return;
            }

            navigator.clipboard.writeText(this.revealed)
                .then(() => Espo.Ui.success(this.translate('Copied to clipboard')));
        }
    };
});
