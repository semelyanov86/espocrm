<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Finance\Source;

/**
 * Stored line margin against net − purchase cost (the Vtiger 7 edit form formula).
 */
enum MarginCheck: string
{
    case Ok = 'ok';
    /** Stored 0 on a line with a non-zero sum: the margin was never computed (documents before 2018-07 and some others). */
    case NotComputed = 'notComputed';
    case Mismatch = 'mismatch';
    /** The line has no stored margin. */
    case Absent = 'absent';
}
