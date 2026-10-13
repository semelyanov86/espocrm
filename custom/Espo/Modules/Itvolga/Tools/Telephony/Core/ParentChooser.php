<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Telephony\Core;

/**
 * The parent of an automatic Call from the exact matches of its number (owner decision 2026-10-13, D-167): the single
 * Account among the matched accounts and the accounts of the matched contacts; otherwise the single matched Contact;
 * otherwise the single matched Lead when no contact matched; otherwise none. «Possible» matches never take part.
 */
final class ParentChooser
{
    /**
     * @param list<string> $accountIds
     * @param array<string, ?string> $contactAccountIds contact id => its account id
     * @param list<string> $leadIds
     * @return ?array{string, string} [entity type, id]
     */
    public static function choose(array $accountIds, array $contactAccountIds, array $leadIds): ?array
    {
        $accounts = array_values(array_unique(array_merge(
            $accountIds,
            array_values(array_filter($contactAccountIds, static fn (?string $id) => $id !== null && $id !== '')),
        )));

        if (count($accounts) === 1) {
            return ['Account', $accounts[0]];
        }

        if (count($contactAccountIds) === 1) {
            return ['Contact', (string) array_key_first($contactAccountIds)];
        }

        if ($contactAccountIds === [] && count(array_unique($leadIds)) === 1) {
            return ['Lead', $leadIds[0]];
        }

        return null;
    }
}
