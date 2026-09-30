<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Finance\Exceptions;

use RuntimeException;

/**
 * An spcompany value that is not one of the known spellings of the single legal entity (D-04).
 * The value is not interpreted as a new company: the caller stops and reports it.
 */
class UnknownLegalEntity extends RuntimeException {}
