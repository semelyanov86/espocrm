/**
 * Setting up the security-key method (D-128; app.authentication2FAMethods.ItvolgaSecurityKey.userApplyView), opened
 * by the core security modal after the password: the user registers one or several keys (primary and backup) with the
 * setup challenge, names them, and Apply saves the whole set with the security model in one request (the server
 * verifies every key, then turns the method on). Like the core TOTP modal, it saves the model itself and triggers
 * `done`, which also closes the forced-setup dialog. While a key is being registered or the set saved, nothing else can
 * be changed. A failed save is checked against the server first — the set may have been stored with only the answer
 * lost (the security modal is opened only when the method is not on yet); when it was not, the used challenge is
 * replaced and the list starts again, and when the check fails too, only closing the dialog is left.
 */
define('itvolga:views/user-security/modals/security-key', ['views/modal', 'itvolga:security-key'], (ModalView, SecurityKey) => {

    const METHOD = 'ItvolgaSecurityKey';

    return class extends ModalView {

        className = 'dialog dialog-record'

        templateContent = `
            <div class="itv-security-key-setup">
                <p>{{intro}}</p>
                {{#if resetNote}}<p class="text-warning">{{resetNote}}</p>{{/if}}
                {{#if keys.length}}
                <ul class="list-group" data-role="keys">
                    {{#each keys}}
                    <li class="list-group-item itv-security-key-setup__key">
                        <span class="fas fa-key text-soft" aria-hidden="true"></span>
                        <input
                            type="text"
                            class="form-control input-sm"
                            data-index="{{@index}}"
                            value="{{name}}"
                            maxlength="100"
                            placeholder="{{../namePlaceholder}}"
                            aria-label="{{../nameLabel}}"
                            {{#if ../busy}}disabled{{/if}}
                        >
                        <button type="button" class="btn btn-link btn-sm" data-action="removeKey"
                            data-index="{{@index}}"{{#if ../busy}} disabled{{/if}}>{{../removeLabel}}</button>
                    </li>
                    {{/each}}
                </ul>
                {{/if}}
                <button type="button" class="btn btn-default" data-action="addKey"{{#if addDisabled}} disabled{{/if}}>
                    <span class="fas fa-plus"></span> {{addLabel}}
                </button>
                <p class="itv-security-key-setup__status" data-role="status" role="status" aria-live="polite">{{status}}</p>
            </div>`

        events = {
            /** @this {Object} */
            'click [data-action="addKey"]': function () {
                this.addKey();
            },
            /** @this {Object} */
            'click [data-action="removeKey"]': function (e) {
                if (this.busy) {
                    return;
                }

                this.keys.splice(Number(e.currentTarget.dataset.index), 1);
                this.status = '';
                this.update();
            },
            /** @this {Object} */
            'input input[data-index]': function (e) {
                this.keys[Number(e.currentTarget.dataset.index)].name = e.currentTarget.value;
            },
        }

        setup() {
            this.headerText = this.getLanguage().translateOption(METHOD, 'auth2FAMethodList', 'Settings');
            this.buttonList = [
                {name: 'apply', label: 'Apply', style: 'danger', disabled: true},
                {name: 'cancel', label: 'Cancel'},
            ];

            /** @type {{name: string, id: string, clientDataJSON: string, attestationObject: string, transports: string[]}[]} */
            this.keys = [];
            this.status = '';
            this.busy = false;
            this.resetPending = !!this.options.reset;

            this.wait(this.loadOptions());
        }

        data() {
            return {
                intro: this.translate('itvolgaSecurityKeySetupIntro', 'messages'),
                resetNote: this.options.reset ? this.translate('itvolgaSecurityKeyResetNote', 'messages') : null,
                keys: this.keys,
                busy: this.busy,
                addDisabled: this.busy || this.keys.length >= this.maxKeys,
                addLabel: this.translate('itvolgaSecurityKeyAdd'),
                removeLabel: this.translate('itvolgaSecurityKeyRemove'),
                nameLabel: this.translate('itvolgaSecurityKeyName'),
                namePlaceholder: this.translate('itvolgaSecurityKeyNamePlaceholder'),
                status: this.status,
            };
        }

        onRemove() {
            this.abortController?.abort();
        }

        /**
         * The creation options with a setup challenge (the core checks the password again; the first request of a
         * Reset also turns 2FA off).
         *
         * @private
         */
        async loadOptions() {
            const {password} = this.model.attributes;

            const data = await Espo.Ajax.postRequest('UserSecurity/action/getTwoFactorUserSetupData', {
                id: this.model.id,
                password,
                auth2FAMethod: this.model.get('auth2FAMethod'),
                reset: this.resetPending,
            });

            this.resetPending = false;
            this.publicKey = data.publicKey;
            this.maxKeys = data.maxKeys;
        }

        /** @private */
        async addKey() {
            if (this.busy) {
                return;
            }

            if (!SecurityKey.isAvailable()) {
                this.status = this.translate('itvolgaSecurityKeyInsecure', 'messages');
                this.update();

                return;
            }

            this.status = this.translate('itvolgaSecurityKeyWaiting', 'messages');
            this.setBusy(true);
            this.abortController = new AbortController();

            try {
                const key = await SecurityKey.create(
                    this.publicKey,
                    this.keys.map(item => item.id),
                    this.abortController.signal,
                );

                this.keys.push({name: this.defaultName(), ...key});
                this.status = this.keys.length >= this.maxKeys ?
                    this.translate('itvolgaSecurityKeyMax', 'messages').replace('{max}', String(this.maxKeys)) :
                    '';
            } catch (error) {
                this.status = this.translate(SecurityKey.errorMessage(error), 'messages');
            }

            if (!this.isRemoved()) {
                this.setBusy(false);
            }
        }

        async actionApply() {
            if (this.busy) {
                return;
            }

            if (!this.keys.length) {
                this.status = this.translate('itvolgaSecurityKeyNeedOne', 'messages');
                this.update();

                return;
            }

            this.model.set('itvolgaSecurityKeys', this.keys.map(item => ({...item})));
            this.status = '';
            this.setBusy(true);
            this.disableButton('cancel');
            Espo.Ui.notifyWait();

            try {
                await this.model.save();

                Espo.Ui.notify(false);
                this.trigger('done');
            } catch (xhr) {
                if (xhr && xhr.status === 403) {
                    xhr.errorIsHandled = true;
                }

                Espo.Ui.notify(false);
                this.model.unset('itvolgaSecurityKeys');

                const saved = await this.isSaved();

                if (saved) {
                    this.trigger('done');

                    return;
                }

                if (saved === null) {
                    // Neither the save nor the check answered: registering another set now could be ignored by the
                    // server (the method may be on already), so only closing the dialog is left.
                    this.status = this.translate('itvolgaSecurityKeySetupUnknown', 'messages');
                    this.enableButton('cancel');
                    this.update();

                    return;
                }

                this.keys = [];
                this.status = this.translate('itvolgaSecurityKeySetupFailed', 'messages');

                try {
                    await this.loadOptions();
                } finally {
                    this.setBusy(false);
                    this.enableButton('cancel');
                }
            }
        }

        /**
         * Whether the method is on now: then the failed save was stored and only its answer was lost. Null when the
         * server could not be asked.
         *
         * @private
         * @return {Promise<boolean|null>}
         */
        async isSaved() {
            try {
                const state = await Espo.Ajax.getRequest('UserSecurity/' + this.model.id);

                return !!state.auth2FA && state.auth2FAMethod === METHOD;
            } catch (xhr) {
                if (xhr) {
                    xhr.errorIsHandled = true;
                }

                return null;
            }
        }

        /** @private */
        defaultName() {
            const index = this.keys.length;

            if (index < 2) {
                return this.translate(index === 0 ? 'itvolgaSecurityKeyPrimary' : 'itvolgaSecurityKeyBackup');
            }

            return this.translate('itvolgaSecurityKeyN').replace('{n}', String(index + 1));
        }

        /** @private */
        setBusy(busy) {
            this.busy = busy;
            this.update();
        }

        /** @private */
        update() {
            if (this.keys.length && !this.busy) {
                this.enableButton('apply');
            } else {
                this.disableButton('apply');
            }

            this.reRender();
        }
    };
});
