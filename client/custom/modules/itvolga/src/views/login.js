/**
 * Login page of the company (D-127; metadata clientDefs.App.loginView): the core login view with its own template —
 * a brand panel (the logo for dark backgrounds over a mosaic of the logo's squares) beside the form. Sign-in, errors,
 * the second step and password recovery stay the core's: the form keeps the core ids, cells and actions.
 */
define('itvolga:views/login', ['views/login'], (LoginView) => {

    return class extends LoginView {

        template = 'itvolga:login'

        data() {
            return {
                ...super.data(),
                brandLogoSrc: this.getBasePath() + 'client/custom/modules/itvolga/img/logo-dark.svg',
                isDark: !!this.getThemeManager().getParam('isDark'),
            };
        }
    };
});
