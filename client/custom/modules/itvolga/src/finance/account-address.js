/**
 * Billing and shipping addresses of a finance document copied from its account: the contract keeps them as a copy of
 * the account's address at the time of the document, as Vtiger did when an organization was chosen (D-179). Used by
 * the account field of a document (the chosen account) and by the document panels of an account, a contact and an
 * opportunity (the account of the parent record).
 */
define('itvolga:finance/account-address', [], () => {

    const FIELDS = ['billingAddress', 'shippingAddress'];
    const PARTS = ['Street', 'City', 'State', 'Country', 'PostalCode'];

    return {
        /** Account attributes to load with the account. */
        ATTRIBUTES: FIELDS.flatMap(field => PARTS.map(part => field + part)),

        /**
         * @param {Record<string, *>} account attributes of the account
         * @param {string[]} forbiddenFieldList document fields the user cannot edit: the server drops them on save
         * @return {Record<string, string|null>|null} null when there is nothing to copy (the document keeps its own)
         */
        fromAccount(account, forbiddenFieldList) {
            const attributes = {};

            for (const field of FIELDS.filter(field => !forbiddenFieldList.includes(field))) {
                for (const part of PARTS) {
                    const attribute = field + part;

                    // An attribute closed to the user is not in the account's data: the document keeps its value.
                    if (attribute in account) {
                        attributes[attribute] = account[attribute] ?? null;
                    }
                }
            }

            return Object.values(attributes).some(value => value !== null && value !== '') ? attributes : null;
        },
    };
});
