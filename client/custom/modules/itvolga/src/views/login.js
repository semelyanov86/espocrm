/**
 * Login page of the company (D-127; metadata clientDefs.App.loginView): the core login view with its own template —
 * a brand panel (the logo for dark backgrounds over a mosaic of the logo's squares) beside the form. Sign-in, errors
 * and password recovery stay the core's: the form keeps the core ids, cells and actions. The second step opens in the
 * same frame (D-128): the code step of the core methods becomes the module's branded one, a step the server names
 * (the security key) is kept; `itvolga:login-response` gives the core the answer of the first step it reads.
 */
define('itvolga:views/login', ['views/login', 'itvolga:login-response'], (LoginView) => {

    return class extends LoginView {

        template = 'itvolga:login'

        setup() {
            super.setup();

            this.createView('brand', 'itvolga:views/login/brand', {selector: '.itv-login__brand'});
        }

        data() {
            return {
                ...super.data(),
                isDark: !!this.getThemeManager().getParam('isDark'),
            };
        }

        onSecondStepRequired(headers, userName, password, data) {
            const view = !data.view || data.view === 'views/login-second-step' ?
                'itvolga:views/login-second-step' :
                data.view;

            this.trigger('redirect', view, headers, userName, password, data);
        }
    };
});
