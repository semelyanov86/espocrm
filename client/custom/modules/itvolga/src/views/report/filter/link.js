/**
 * Condition on a link: the core link search plus its two exclusive operators that the core list leaves out — "none
 * of (and not empty)" and "is not (and not empty)" (bare notIn / notEquals, without records lacking the link). A stored
 * condition of that kind reopens as itself, and editing it does not add records without a link.
 */
define('itvolga:views/report/filter/link', ['views/fields/link'], (LinkView) => {

    return class extends LinkView {

        setup() {
            super.setup();
            this.searchTypeList = [...this.searchTypeList, 'isNotOneOfAndIsNotEmpty', 'isNotAndIsNotEmpty'];
        }
    };
});
