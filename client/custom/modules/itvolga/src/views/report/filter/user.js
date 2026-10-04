/**
 * Condition on a link to users (owner, creator …): the core link search plus "current user" / "not current user",
 * resolved by the server to the user who runs the report (a mailing per recipient in 05.3 gets his own slice).
 */
define('itvolga:views/report/filter/user', ['views/fields/link'], (LinkView) => {

    const OWN = ['isCurrentUser', 'isNotCurrentUser'];

    return class extends LinkView {

        setup() {
            super.setup();
            this.searchTypeList = [...OWN, ...this.searchTypeList];
        }

        handleSearchType(type) {
            super.handleSearchType(type);

            if (OWN.includes(type)) {
                this.$el.find('div.primary, div.one-of-container').addClass('hidden');
            }
        }

        fetchSearch() {
            const type = this.$el.find('select.search-type').val();

            if (OWN.includes(type)) {
                return {type: type, attribute: this.idName, data: {type: type}};
            }

            return super.fetchSearch();
        }
    };
});
