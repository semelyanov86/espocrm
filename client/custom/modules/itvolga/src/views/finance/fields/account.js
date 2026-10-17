/**
 * The account of a finance document (Quote, SalesOrder, Invoice, Act; D-179): choosing an account in the select dialog
 * or by autocomplete copies its billing and shipping addresses into the document together with the account. The
 * addresses come with the chosen record (no request of its own), so a quick save or a second choice never pairs one
 * account with another's address, and cancelling an inline edit restores both. An account without an address keeps
 * the document's addresses.
 */
define('itvolga:views/finance/fields/account', ['views/fields/link', 'itvolga:finance/account-address'], (
    LinkFieldView,
    AccountAddress,
) => {

    return class extends LinkFieldView {

        getMandatorySelectAttributeList() {
            return [...super.getMandatorySelectAttributeList(), ...AccountAddress.ATTRIBUTES];
        }

        select(model) {
            const result = super.select(model);

            if (this.isEditMode()) {
                const forbiddenFieldList = this.getAcl().getScopeForbiddenFieldList(this.model.entityType, 'edit');
                const attributes = AccountAddress.fromAccount(model.attributes, forbiddenFieldList);

                if (attributes) {
                    this.model.setMultiple(attributes, {fromField: this.name});
                }
            }

            return result;
        }
    };
});
