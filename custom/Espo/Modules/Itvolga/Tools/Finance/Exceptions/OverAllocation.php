<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Finance\Exceptions;

use RuntimeException;

/**
 * Allocations of a payment add up to more than the payment amount.
 */
class OverAllocation extends RuntimeException {}
