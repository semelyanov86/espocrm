<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Finance\Exceptions;

use InvalidArgumentException;

/**
 * A value the finance core cannot accept: float, malformed number, wrong sign or too many decimals.
 */
class InvalidValue extends InvalidArgumentException {}
