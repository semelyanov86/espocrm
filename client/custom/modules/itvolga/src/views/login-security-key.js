/**
 * The second login step with a security key (D-128), opened when the server answers the first step with this view
 * (SecurityKeyLogin): the browser asks for a touch of one of the user's keys and the signed answer goes to the server
 * in `Espo-Authorization-Code`, with the credentials of the first step, as the core code step does. The browser is asked
 * at once and again by the button (Safari wants a click). A refused answer has burnt its challenge: the next attempt
 * repeats the first step for a fresh one, so the user does not type the password again. Contract of the controller as
 * the core `views/login-second-step`: options loginData, userName, password, anotherUser, headers; events login, back.
 */
define('itvolga:views/login-security-key', ['view', 'itvolga:security-key', 'itvolga:login-response'], (
    View,
    SecurityKey,
) => {

    /** A challenge lives 300 s on the server; an older one is replaced before the browser is asked. */
    const CHALLENGE_AGE = 240000;

    return class extends View {

        template = 'itvolga:login-security-key'

        views = {
            footer: {
                fullSelector: 'body > footer',
                view: 'views/site/footer',
            },
        }

        events = {
            /** @this {Object} */
            'click [data-action="useKey"]': function () {
                this.useKey();
            },
            /** @this {Object} */
            'click [data-action="backToLogin"]': function () {
                this.trigger('back');
            },
        }

        setup() {
            this.headers = this.options.headers || {};
            this.anotherUser = this.options.anotherUser || null;
            this.applyLoginData(this.options.loginData);

            this.createView('brand', 'itvolga:views/login/brand', {selector: '.itv-login__brand'});
        }

        data() {
            const available = SecurityKey.isAvailable();

            return {
                message: this.translate(this.loginData.message, 'messages', 'User'),
                hasKeys: !!this.publicKey,
                canUseKey: !!this.publicKey && available,
                isInsecure: !!this.publicKey && !available,
                isDark: !!this.getThemeManager().getParam('isDark'),
            };
        }

        afterRender() {
            this.cardElement = this.element.querySelector('[data-role="key-card"]');
            this.statusElement = this.element.querySelector('[data-role="status"]');
            this.button = this.element.querySelector('[data-action="useKey"]');

            if (this.button && !this.asked) {
                this.asked = true;
                this.useKey();
            }
        }

        onRemove() {
            this.abortController?.abort();
        }

        /**
         * @private
         * @param {Object} loginData The answer of a first step.
         */
        applyLoginData(loginData) {
            this.loginData = loginData;
            this.publicKey = (loginData.data || {}).publicKey || null;
            this.receivedAt = Date.now();
            this.challengeUsed = false;
        }

        /** @private */
        async useKey() {
            if (this.busy) {
                return;
            }

            this.setBusy(true);

            try {
                if (this.challengeUsed || Date.now() - this.receivedAt > CHALLENGE_AGE) {
                    await this.refresh();
                }

                if (!this.publicKey || this.isRemoved()) {
                    return;
                }

                this.setStatus('itvolgaSecurityKeyWaiting');
                this.setWaiting(true);
                this.abortController = new AbortController();

                let code;

                try {
                    code = await SecurityKey.get(this.publicKey, this.abortController.signal);
                } catch (error) {
                    this.setStatus(SecurityKey.errorMessage(error), true);

                    return;
                } finally {
                    this.setWaiting(false);
                }

                this.challengeUsed = true;
                await this.send(code);
            } finally {
                this.setBusy(false);
            }
        }

        /**
         * @private
         * @param {string} code
         */
        async send(code) {
            const headers = this.requestHeaders();
            headers['Espo-Authorization-Code'] = code;

            try {
                const data = await Espo.Ajax.getRequest('App/user', null, {login: true, headers: headers});

                this.triggerLogin(data);
            } catch (xhr) {
                // 401: the key was not accepted; 403: the core limit of failed attempts.
                if (xhr.status === 403) {
                    xhr.errorIsHandled = true;
                    this.setStatus('itvolgaSecurityKeyTooManyAttempts', true);

                    return;
                }

                if (xhr.status === 401) {
                    const reason = xhr.getResponseHeader('X-Status-Reason');

                    this.setStatus(reason === 'error' ? 'loginError' : 'itvolgaSecurityKeyRejected', true);
                }
            }
        }

        /**
         * The first step again, without a code: a new challenge (or the sign-in itself if 2FA was turned off
         * meanwhile; back to the form when the password no longer passes or another method answers).
         *
         * @private
         */
        async refresh() {
            const headers = this.requestHeaders();
            headers['Espo-Authorization-By-Token'] = 'false';

            try {
                const data = await Espo.Ajax.getRequest('App/user', null, {login: true, headers: headers});

                this.publicKey = null;
                this.triggerLogin(data);
            } catch (xhr) {
                const loginData = xhr.responseJSON || {};

                if (xhr.status === 403) {
                    xhr.errorIsHandled = true;
                    this.publicKey = null;
                    this.setStatus('itvolgaSecurityKeyTooManyAttempts', true);

                    return;
                }

                if (
                    xhr.status === 401 &&
                    xhr.getResponseHeader('X-Status-Reason') === 'second-step-required' &&
                    loginData.view === this.loginData.view
                ) {
                    xhr.errorIsHandled = true;
                    this.applyLoginData(loginData);

                    if (!this.publicKey) {
                        await this.reRender();
                    }

                    return;
                }

                this.publicKey = null;
                this.trigger('back');
            }
        }

        /** @private */
        requestHeaders() {
            const headers = Espo.Utils.clone(this.headers);
            headers['Espo-Authorization-Create-Token-Secret'] = 'true';

            if (this.anotherUser !== null) {
                headers['X-Another-User'] = this.anotherUser;
            }

            return headers;
        }

        /** @private */
        triggerLogin(data) {
            if (this.anotherUser) {
                data.anotherUser = this.anotherUser;
            }

            this.trigger('login', this.options.userName || (data.user || {}).userName, data);
        }

        /** @private */
        setStatus(key, isError = false) {
            if (!this.statusElement || this.isRemoved()) {
                return;
            }

            this.statusElement.textContent = this.translate(key, 'messages', 'User');
            this.statusElement.dataset.kind = isError ? 'error' : '';
        }

        /**
         * The touch spot of the drawn key pulses while the browser waits for a touch.
         *
         * @private
         */
        setWaiting(waiting) {
            if (this.cardElement && !this.isRemoved()) {
                this.cardElement.dataset.state = waiting ? 'waiting' : '';
            }
        }

        /** @private */
        setBusy(busy) {
            this.busy = busy;

            if (this.button && !this.isRemoved()) {
                this.button.disabled = busy;
                this.button.textContent = this.translate(this.asked && !busy ? 'itvolgaSecurityKeyRetry' :
                    'itvolgaSecurityKeyUse');
            }
        }
    };
});
