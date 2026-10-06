<?php

declare(strict_types=1);

/*
 * A software security key for the stand acceptance tests (D-128), driven by tests/security_key_stand/authenticator.py:
 * one JSON request per input line, one JSON answer per output line. Key pairs live in this process only (the unit-test
 * SoftAuthenticator); binary values travel as base64url. Requests:
 *
 *   {"op": "new", "alg": -7}                          → {"handle": 1, "id": "<credential id>"}
 *   {"op": "attest", "handle": 1, "rpId", "origin", "challenge", "o": {…}}
 *                                                     → {"id", "clientDataJSON", "attestationObject"}
 *   {"op": "assert", "handle": 1, "rpId", "origin", "challenge", "signCount", "o": {…}}
 *                                                     → {"code": "<Espo-Authorization-Code value>"}
 *
 * Options "o" are those of SoftAuthenticator; challenge, credentialId, userHandle and trailing are base64url.
 */

use Espo\Modules\Itvolga\Tools\SecurityKey\Core\Base64Url;
use Itvolga\Tests\SecurityKey\Support\SoftAuthenticator;

require dirname(__DIR__) . '/security_key/bootstrap.php';

/** @var array<int, SoftAuthenticator> $authenticators */
$authenticators = [];

while (($line = fgets(STDIN)) !== false) {
    $request = json_decode($line, true, 8, JSON_THROW_ON_ERROR);
    $o = $request['o'] ?? [];

    foreach (['challenge', 'credentialId', 'userHandle', 'trailing'] as $name) {
        if (isset($o[$name])) {
            $o[$name] = Base64Url::decode($o[$name], 8192);
        }
    }

    if ($request['op'] === 'new') {
        $authenticator = SoftAuthenticator::create($request['alg']);
        $authenticators[count($authenticators) + 1] = $authenticator;
        $answer = ['handle' => count($authenticators), 'id' => Base64Url::encode($authenticator->credentialId)];
    } elseif ($request['op'] === 'attest') {
        $authenticator = $authenticators[$request['handle']];
        $challenge = Base64Url::decode($request['challenge'], 64);
        $response = $authenticator->attestation($request['rpId'], $request['origin'], $challenge, $o);
        $answer = [
            'id' => Base64Url::encode($authenticator->credentialId),
            'clientDataJSON' => Base64Url::encode($response['clientDataJSON']),
            'attestationObject' => Base64Url::encode($response['attestationObject']),
        ];
    } else {
        $authenticator = $authenticators[$request['handle']];
        $challenge = Base64Url::decode($request['challenge'], 64);
        $assertion = $authenticator->assertion($request['rpId'], $request['origin'], $challenge, $request['signCount'], $o);
        $answer = ['code' => SoftAuthenticator::code($assertion)];
    }

    echo json_encode($answer), "\n";
}
