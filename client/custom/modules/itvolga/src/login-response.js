/**
 * The answer of the first sign-in step that asks for a second factor (HTTP 401, X-Status-Reason: second-step-required,
 * a JSON body with the method's message, view and data) as `xhr.responseJSON`, which the core login view reads (D-128).
 * EspoCRM 10.0.9 sends that body as text/html and its request object (`util/ajax` Xhr, an XMLHttpRequest) has no
 * `responseJSON` — the jQuery property the login view was written for — so the core loses the message of its code step
 * and the step a method asks for (the security key). Only that answer is parsed; every other response is untouched.
 */
define('itvolga:login-response', ['util/ajax'], ({Xhr}) => {

    if (!Object.getOwnPropertyDescriptor(Xhr.prototype, 'responseJSON')) {
        Object.defineProperty(Xhr.prototype, 'responseJSON', {
            configurable: true,
            get() {
                if (this.status !== 401 || this.getResponseHeader('X-Status-Reason') !== 'second-step-required') {
                    return undefined;
                }

                try {
                    return JSON.parse(this.responseText);
                } catch (e) {
                    return undefined;
                }
            },
        });
    }

    return Xhr;
});
