<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Finance\Source;

/**
 * Stored value against the value recomputed from the lines.
 */
enum TotalCheck: string
{
    /** Equal exactly. */
    case Exact = 'exact';
    /** Differs only by rounding: the recomputed value rounded half up to kopecks equals the stored one. */
    case Rounded = 'rounded';
    /** Real discrepancy: reported, never corrected (D-05). */
    case Mismatch = 'mismatch';
}
