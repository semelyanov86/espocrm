<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Telephony;

/**
 * The facts of a telephony Call (owner decision 2026-10-13, D-168): only the Asterisk integration writes them, with
 * the save option SAVE_OPTION; users keep the name, the description, the parent, contacts, leads and participants.
 */
final class CallFacts
{
    public const SAVE_OPTION = 'itvolgaTelephony';
    public const KEY = 'cAsteriskLinkedId';

    public const ATTRIBUTES = [
        'status',
        'direction',
        'dateStart',
        'dateEnd',
        'cAsteriskLinkedId',
        'cPhoneNumber',
        'cCallStatusRaw',
        'cBillDuration',
        'cIncomingLine',
        'cLiveState',
        'cExtension',
        'cAnsweredAt',
        'cClickToCall',
        'cRecording',
        'cRecordingPath',
    ];
}
