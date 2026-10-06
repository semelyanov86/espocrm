/**
 * The brand panel of the login page (D-127): the logo for dark backgrounds over a mosaic of the logo's squares and one
 * line about the system. A child view of the login page and of the second login steps (D-128), so the markup lives once.
 */
define('itvolga:views/login/brand', ['view'], (View) => {

    return class extends View {

        template = 'itvolga:login/brand'

        data() {
            return {
                brandLogoSrc: this.getBasePath() + 'client/custom/modules/itvolga/img/logo-dark.svg',
            };
        }
    };
});
