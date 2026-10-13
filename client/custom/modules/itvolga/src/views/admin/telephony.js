/**
 * Administration → Телефония (stage 07.1): the extension whose user gets the calls hung up in the voice menu. The
 * PBX connection and its secrets are system settings (itvolga-setup-telephony from stdin), not shown here.
 */
define('itvolga:views/admin/telephony', ['views/settings/record/edit'], (SettingsEditView) => {

    return class extends SettingsEditView {

        layoutName = 'itvolgaTelephony';
        saveAndContinueEditingAction = false;
    };
});
