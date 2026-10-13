<?php

declare(strict_types=1);

namespace Itvolga\Tests\Telephony;

use Espo\Modules\Itvolga\Tools\Telephony\Core\ByteRange;
use Espo\Modules\Itvolga\Tools\Telephony\Core\ParentChooser;
use Espo\Modules\Itvolga\Tools\Telephony\Core\RecordingPath;
use Espo\Modules\Itvolga\Tools\Telephony\Core\TrackerSettings;
use InvalidArgumentException;
use Itvolga\Tests\Finance\TestCase;

final class HelpersTest extends TestCase
{
    public function testByteRange(): void
    {
        $cases = [
            [null, 'full', 0, 999],
            ['bytes=0-', 'partial', 0, 999],
            ['bytes=100-199', 'partial', 100, 199],
            ['bytes=900-5000', 'partial', 900, 999],
            ['bytes=-100', 'partial', 900, 999],
            ['bytes=-5000', 'partial', 0, 999],
            ['bytes=1000-', 'unsatisfiable', 0, 0],
            ['bytes=-0', 'unsatisfiable', 0, 0],
            ['bytes=200-100', 'full', 0, 999],
            ['bytes=0-1,5-6', 'full', 0, 999],
            ['items=0-1', 'full', 0, 999],
            ['bytes=-', 'full', 0, 999],
            ['bytes=9999999999999999999-', 'full', 0, 999],
        ];

        foreach ($cases as [$header, $kind, $start, $end]) {
            $range = ByteRange::parse($header, 1000);
            $this->assertSame([$kind, $start, $end], [$range->kind, $range->start, $range->end], (string) $header);
        }

        $this->assertSame(100, ByteRange::parse('bytes=100-199', 1000)->length());
        $this->assertSame('unsatisfiable', ByteRange::parse('bytes=0-', 0)->kind);
    }

    public function testRecordingPath(): void
    {
        $root = '/var/spool/asterisk/monitor';
        $this->assertSame('2026/10/13/2026.10.13_18-04_From.79990000001_To.+79990000002.wav',
            RecordingPath::relative($root, "$root/2026/10/13/2026.10.13_18-04_From.79990000001_To.+79990000002.wav"));
        $this->assertSame('2026/10/13/a.wav', RecordingPath::relative("$root/", "$root/2026/10/13/a.wav"));

        foreach ([
            '/etc/passwd', "$root/../x/2026/10/13/a.wav", "$root/2026/10/13/../a.wav", "$root/2026/10/13/.a.wav",
            "$root/2026/10/13/a.mp3", "$root/2026/10/a.wav", "$root/x/2026/10/13/a.wav", "$root/2026/10/13/a\0.wav",
            "{$root}x/2026/10/13/a.wav", "$root/2026/10/13/a\\b.wav",
        ] as $absolute) {
            $this->assertSame(null, RecordingPath::relative($root, $absolute), $absolute);
        }

        $this->assertSame(false, RecordingPath::isSafe('2026/10/13/../../etc.wav'));
        $this->assertSame(false, RecordingPath::isSafe('/2026/10/13/a.wav'));
    }

    public function testParentChooser(): void
    {
        $this->assertSame(['Account', 'a1'], ParentChooser::choose(['a1'], [], []));
        $this->assertSame(['Account', 'a1'], ParentChooser::choose([], ['c1' => 'a1', 'c2' => 'a1'], ['l1']),
            'the contacts of one account → the account');
        $this->assertSame(['Account', 'a1'], ParentChooser::choose(['a1'], ['c1' => 'a1'], []));
        $this->assertSame(['Contact', 'c1'], ParentChooser::choose(['a1', 'a2'], ['c1' => null], []),
            'two accounts, one contact → the contact');
        $this->assertSame(['Contact', 'c1'], ParentChooser::choose([], ['c1' => null], ['l1']));
        $this->assertSame(['Lead', 'l1'], ParentChooser::choose([], [], ['l1']));
        $this->assertSame(null, ParentChooser::choose([], ['c1' => null, 'c2' => null], ['l1']));
        $this->assertSame(null, ParentChooser::choose(['a1', 'a2'], [], []));
        $this->assertSame(null, ParentChooser::choose([], [], ['l1', 'l2']));
        $this->assertSame(null, ParentChooser::choose([], [], []));
    }

    public function testTrackerSettings(): void
    {
        $s = TrackerSettings::fromArray([]);
        $this->assertSame('105', $s->endpointOf('PJSIP/105-0000000a'));
        $this->assertSame('trunk-russia', $s->endpointOf('PJSIP/trunk-russia-00000004'));
        $this->assertSame(null, $s->endpointOf('Local/811@conf-room-00000032;1'));
        $this->assertSame(true, $s->isExtension('208'));
        $this->assertSame(false, $s->isExtension('808'));
        $this->assertSame(false, $s->isExtension('1050'));
        $this->assertSame('ignored', $s->trunkClass('trunk-easybell'));

        foreach ([
            ['extensionPattern' => '(('], ['extensionPattern' => 'a~b'], ['trunks' => []],
            ['trunks' => ['trunk x' => 'inbound']], ['trunks' => ['t' => 'other']], ['inboundContexts' => []],
            ['originatePrefix' => 'CRM'], ['localAreaCode' => '12a'],
        ] as $bad) {
            $this->assertThrows(InvalidArgumentException::class, fn () => TrackerSettings::fromArray($bad));
        }
    }

    /**
     * The core must not depend on EspoCRM: the stand side is a thin adapter (D-166).
     */
    public function testCoreIsPure(): void
    {
        $dir = ITVOLGA_REPO . '/custom/Espo/Modules/Itvolga/Tools/Telephony/Core';
        $files = new \RecursiveIteratorIterator(new \RecursiveDirectoryIterator($dir, \FilesystemIterator::SKIP_DOTS));

        foreach ($files as $file) {
            $code = (string) file_get_contents((string) $file);
            preg_match_all('/^use ([^;]+);/m', $code, $m);

            foreach ($m[1] as $import) {
                $this->assertTrue(!str_starts_with($import, 'Espo\\') ||
                    str_starts_with($import, 'Espo\\Modules\\Itvolga\\Tools\\Telephony\\Core\\'), "$file imports $import");
            }
        }
    }
}
