/**
 * Every phone field (metadata fields.phone.view, stage 07.1 D-170): a click on a number rings the user's own desk
 * phone through the CRM (POST Telephony/dial) and the PBX dials the number once the user picks up. Only when the
 * telephony is on and the user has an extension; a click with a modifier key, or for a user without an extension,
 * keeps the usual tel: link. The server checks the extension, the number and the record again.
 */
define('itvolga:views/fields/phone', ['views/fields/phone'], (PhoneFieldView) => {

    const PAUSE_MS = 5000;

    return class extends PhoneFieldView {

        setup() {
            super.setup();

            this.addHandler('click', 'a[data-action="dial"]', (event, target) => this.dialFromCrm(event, target));
        }

        canDialFromCrm() {
            return Boolean(this.getConfig().get('itvolgaTelephonyEnabled')) &&
                Boolean(this.getUser().get('cPhoneExtension')) &&
                !this.getUser().isPortal();
        }

        /**
         * @param {MouseEvent} event
         * @param {HTMLElement} target
         */
        dialFromCrm(event, target) {
            if (!this.canDialFromCrm() || event.button !== 0 ||
                event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) {
                return;
            }

            event.preventDefault();
            event.stopPropagation();

            if (this.isDialing) {
                return;
            }

            this.isDialing = true;
            setTimeout(() => this.isDialing = false, PAUSE_MS);

            const model = this.model;

            Espo.Ui.notify(this.translate('Calling…', 'labels', 'Call'));

            Espo.Ajax
                .postRequest('Telephony/dial', {
                    phoneNumber: target.dataset.phoneNumber,
                    entityType: model && model.id ? model.entityType : null,
                    entityId: model && model.id ? model.id : null,
                })
                .then(result => {
                    Espo.Ui.success(
                        this.translate('telephonyCallInitiated', 'messages', 'Call')
                            .replace('{extension}', result.extension),
                        {suppress: true}
                    );
                });
        }
    };
});
