/**
 * Billing and shipping addresses of a finance document come from its account: the contract keeps them as a copy of the
 * account's address at the time of the document, as Vtiger did when an organization was chosen. Two core contracts:
 * - createHandler of the document panels of an account, a contact and an opportunity (clientDefs relationshipPanels;
 *   the account and the contact themselves come from createAttributeMap) — getAttributes(parent record);
 * - selectFieldHandler of the account field of a document (clientDefs relationshipPanels.account) —
 *   getAttributes(chosen account), replacing the addresses of the previous account.
 * An account without any address, or one the user cannot read, changes nothing.
 */
define('itvolga:handlers/finance/account-address', [], () => {

    const FIELDS = ['billingAddress', 'shippingAddress'];
    const PARTS = ['Street', 'City', 'State', 'Country', 'PostalCode'];

    return class {

        /**
         * @param {import('model').default} model a parent record or a chosen account
         * @return {Promise<Record<string, string|null>>}
         */
        async getAttributes(model) {
            const accountId = model.entityType === 'Account' ? model.id : model.get('accountId');

            if (!accountId) {
                return {};
            }

            let account;

            try {
                account = await Espo.Ajax.getRequest(`Account/${encodeURIComponent(accountId)}`);
            } catch (xhr) {
                xhr.errorIsHandled = true;

                return {};
            }

            const attributes = {};

            for (const field of FIELDS) {
                for (const part of PARTS) {
                    const attribute = field + part;

                    // Fields closed to the user are not in the response: the document keeps its own value.
                    if (attribute in account) {
                        attributes[attribute] = account[attribute] ?? null;
                    }
                }
            }

            if (Object.values(attributes).every(value => value === null || value === '')) {
                return {};
            }

            return attributes;
        }

        /**
         * @return {Promise<Record<string, *>>}
         */
        async getClearAttributes() {
            return {};
        }
    };
});
