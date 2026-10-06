/**
 * WebAuthn in the browser for the security-key second factor (D-128): the server's JSON options become the options the
 * browser takes (base64url → ArrayBuffer), the browser's answers become the JSON the server checks (ArrayBuffer →
 * base64url). The WebAuthn Level 3 JSON helpers (parseRequestOptionsFromJSON, toJSON) are not used: not every browser
 * the company uses has them.
 */
define('itvolga:security-key', [], () => {

    const toBuffer = text => {
        const base64 = text.replace(/-/g, '+').replace(/_/g, '/');
        const binary = atob(base64 + '='.repeat((4 - base64.length % 4) % 4));

        return Uint8Array.from(binary, char => char.charCodeAt(0)).buffer;
    };

    const toText = buffer => {
        let binary = '';

        new Uint8Array(buffer).forEach(byte => binary += String.fromCharCode(byte));

        return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
    };

    return {
        /**
         * A secure page (HTTPS, or an origin the browser is told to treat as secure) of a browser with WebAuthn.
         */
        isAvailable() {
            return window.isSecureContext && !!window.PublicKeyCredential && !!navigator.credentials;
        },

        /**
         * Asks for a touch of a registered key; resolves to the Espo-Authorization-Code value.
         *
         * @param {Object} publicKey Request options of the first login step.
         * @param {AbortSignal} signal
         * @return {Promise<string>}
         */
        async get(publicKey, signal) {
            const credential = await navigator.credentials.get({
                publicKey: {
                    ...publicKey,
                    challenge: toBuffer(publicKey.challenge),
                    allowCredentials: publicKey.allowCredentials.map(item => ({
                        type: item.type,
                        id: toBuffer(item.id),
                        ...(item.transports.length ? {transports: item.transports} : {}),
                    })),
                },
                signal: signal,
            });
            const response = credential.response;

            const answer = {
                id: toText(credential.rawId),
                clientDataJSON: toText(response.clientDataJSON),
                authenticatorData: toText(response.authenticatorData),
                signature: toText(response.signature),
                userHandle: response.userHandle && response.userHandle.byteLength ? toText(response.userHandle) : null,
            };

            return toText(new TextEncoder().encode(JSON.stringify(answer)));
        },

        /**
         * Registers a key; resolves to an item of the setup request.
         *
         * @param {Object} publicKey Creation options of the setup.
         * @param {string[]} excludeIds Keys already registered in this setup.
         * @param {AbortSignal} signal
         * @return {Promise<{id: string, clientDataJSON: string, attestationObject: string, transports: string[]}>}
         */
        async create(publicKey, excludeIds, signal) {
            const credential = await navigator.credentials.create({
                publicKey: {
                    ...publicKey,
                    challenge: toBuffer(publicKey.challenge),
                    user: {...publicKey.user, id: toBuffer(publicKey.user.id)},
                    excludeCredentials: excludeIds.map(id => ({type: 'public-key', id: toBuffer(id)})),
                },
                signal: signal,
            });
            const response = credential.response;

            return {
                id: toText(credential.rawId),
                clientDataJSON: toText(response.clientDataJSON),
                attestationObject: toText(response.attestationObject),
                transports: response.getTransports ? response.getTransports() : [],
            };
        },

        /**
         * The message (Global.messages) for a refused browser call.
         *
         * @param {Error} error
         * @return {string}
         */
        errorMessage(error) {
            switch (error && error.name) {
                case 'NotAllowedError':
                case 'AbortError':
                    return 'itvolgaSecurityKeyCancelled';
                case 'InvalidStateError':
                    return 'itvolgaSecurityKeyAlreadyAdded';
                case 'SecurityError':
                case 'NotSupportedError':
                    return 'itvolgaSecurityKeyInsecure';
                default:
                    return 'itvolgaSecurityKeyError';
            }
        },
    };
});
