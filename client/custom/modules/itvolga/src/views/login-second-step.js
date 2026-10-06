/**
 * The code step of the core 2FA methods (TOTP, e-mail, SMS) in the frame of the company login page (D-128): only the
 * template and the brand panel change; reading the code, the request, the errors and the return to the form are the
 * core's (`views/login-second-step`), so the template keeps the core ids and actions.
 */
define('itvolga:views/login-second-step', ['views/login-second-step'], (LoginSecondStepView) => {

    return class extends LoginSecondStepView {

        template = 'itvolga:login-second-step'

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
    };
});
