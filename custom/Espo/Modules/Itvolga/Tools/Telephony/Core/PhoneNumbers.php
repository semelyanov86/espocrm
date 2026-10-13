<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Telephony\Core;

/**
 * Telephone numbers of the live telephony (stage 07.1, D-167): one canonical form for a caller id, a dialled number
 * and a number stored in EspoCRM, the PhoneNumber.numeric keys that hold the same number, and the string the
 * production dialplan accepts for dialling.
 *
 * The canonical rules are those of the Vtiger import (scripts/import/transforms.py, phone()): 11 digits starting with
 * 7 or 8 → +7 and 10 digits; 10 digits starting with 3, 4, 8 or 9 → +7; «+» and 7–15 digits stay international; plus
 * «00» as the international prefix and the six-digit local numbers of the local area, which the dialplan dials as
 * +7<area><6 digits> (`_XXXXXX` → 78352XXXXXX). A value with several numbers or an internal extension («доб.», «ext»,
 * «,;/») has no canonical form: it is never dialled and only a «possible» match.
 */
final class PhoneNumbers
{
    private const MULTI = '/[,;\/]|доб|ext|\bд\./iu';

    public static function canonical(?string $raw, string $localAreaCode): ?string
    {
        $raw = trim((string) $raw);

        if ($raw === '' || preg_match(self::MULTI, $raw) || preg_match('/[^0-9+()\s.\-]/u', $raw)) {
            return null;
        }

        $digits = preg_replace('/\D/', '', $raw) ?? '';
        $length = strlen($digits);

        if (str_starts_with($raw, '+')) {
            return $length >= 7 && $length <= 15 ? '+' . $digits : null;
        }

        if (str_starts_with($digits, '00') && $length >= 9 && $length <= 17) {
            return '+' . substr($digits, 2);
        }

        if ($length === 11 && ($digits[0] === '7' || $digits[0] === '8')) {
            return '+7' . substr($digits, 1);
        }

        if ($length === 10 && str_contains('3489', $digits[0])) {
            return '+7' . $digits;
        }

        if ($length === 6 && $localAreaCode !== '') {
            return '+7' . $localAreaCode . $digits;
        }

        return null;
    }

    /**
     * PhoneNumber.numeric values (all digits of the stored string) that hold the same canonical number.
     *
     * @return list<string>
     */
    public static function numericCandidates(string $canonical, string $localAreaCode): array
    {
        $digits = substr($canonical, 1);

        if (str_starts_with($canonical, '+7') && strlen($digits) === 11) {
            $national = substr($digits, 1);
            $list = ['7' . $national, '8' . $national];

            if (str_contains('3489', $national[0])) {
                $list[] = $national;
            }

            if ($localAreaCode !== '' && str_starts_with($national, $localAreaCode)
                && strlen($national) - strlen($localAreaCode) === 6) {
                $list[] = substr($national, strlen($localAreaCode));
            }

            return array_values(array_unique($list));
        }

        return [$digits, '00' . $digits];
    }

    /**
     * The last ten digits for the «possible» search inside non-standard stored strings; null for a shorter number.
     */
    public static function tail(string $canonical): ?string
    {
        $digits = substr($canonical, 1);

        return strlen($digits) >= 10 ? substr($digits, -10) : null;
    }

    /**
     * What to put into Originate «Exten» so that the `phones-out` patterns of the production dialplan take the number
     * exactly as if the user had dialled it on the desk phone: a local six-digit number as six digits (`_XXXXXX`),
     * a Russian number as +7… (`_+7XXXXXXXXXX`, `_+78352XXXXXX`), any other country with the dialplan's exit prefix 0
     * (`_0[1-689]XXXX.` → «+» and the rest). Null: the number cannot be dialled from the CRM.
     */
    public static function dialString(?string $raw, string $localAreaCode): ?string
    {
        $canonical = self::canonical($raw, $localAreaCode);

        if ($canonical === null) {
            return null;
        }

        $digits = preg_replace('/\D/', '', (string) $raw) ?? '';

        if (strlen($digits) === 6 && !str_starts_with(trim((string) $raw), '+')) {
            return $digits;
        }

        if (str_starts_with($canonical, '+7')) {
            return strlen($canonical) === 12 ? $canonical : null;
        }

        $international = substr($canonical, 1);

        return preg_match('/^[1-689][0-9]{5,14}$/', $international) ? '0' . $international : null;
    }
}
