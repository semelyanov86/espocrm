/**
 * «+» on the document panels of an account, a contact and an opportunity (clientDefs relationshipPanels createHandler;
 * the account and the contact come from createAttributeMap; D-179): the new document gets the billing and shipping
 * addresses of the account — the parent itself, or the account of the contact or the opportunity. The core waits for
 * it before it opens the form. An account the user cannot read, or a removed one, leaves the addresses empty.
 */
define('itvolga:handlers/finance/account-address', ['itvolga:finance/account-address'], (AccountAddress) => {

    return class {

        /**
         * @param {import('view-helper').default} viewHelper
         */
        constructor(viewHelper) {
            this.viewHelper = viewHelper;
        }

        /**
         * @param {import('model').default} model the parent record
         * @param {string} link
         * @return {Promise<Record<string, string|null>>}
         */
        async getAttributes(model, link) {
            const account = model.entityType === 'Account' ?
                model.attributes :
                await this.loadAccount(model.get('accountId'));

            if (!account) {
                return {};
            }

            const forbiddenFieldList = this.viewHelper.acl
                .getScopeForbiddenFieldList(model.getLinkParam(link, 'entity'), 'edit');

            return AccountAddress.fromAccount(account, forbiddenFieldList) ?? {};
        }

        /**
         * @param {string|null} id
         * @return {Promise<Record<string, *>|null>}
         */
        async loadAccount(id) {
            if (!id) {
                return null;
            }

            try {
                return await Espo.Ajax.getRequest(`Account/${encodeURIComponent(id)}`);
            } catch (xhr) {
                // Any other error keeps the core message; the form opens anyway.
                if (xhr.status === 403 || xhr.status === 404) {
                    xhr.errorIsHandled = true;
                }

                return null;
            }
        }
    };
});
