<?php

declare(strict_types=1);

namespace Itvolga\Tests\Reports;

use Espo\Modules\Itvolga\Tools\Report\Core\Definition\DefinitionParser;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\FieldInfo;
use Espo\Modules\Itvolga\Tools\Report\Core\Info\ConditionText;
use Espo\Modules\Itvolga\Tools\Report\Core\Info\ConditionWords;
use Espo\Modules\Itvolga\Tools\Report\Core\Mailing\LetterBody;
use Itvolga\Tests\Finance\TestCase;

/**
 * The report info of a letter (D-124): the condition text from the canonical where items only — the names kept by the
 * author's interface in `advanced` never appear, record names come from the words of the reader — and the escaped
 * letter body.
 */
final class InfoTest extends TestCase
{
    private function words(): ConditionWords
    {
        return new class implements ConditionWords {
            public function joiner(string $type): string
            {
                return $type === 'or' ? 'ИЛИ' : 'И';
            }

            public function field(FieldInfo $field): string
            {
                return $field->ref->toString();
            }

            public function operator(string $type): string
            {
                return "[$type]";
            }

            public function compare(string $operator, string $otherField): string
            {
                return "$operator $otherField";
            }

            public function values(FieldInfo $field, array $values): array
            {
                // A reader who may read the record r1 only.
                return array_map(fn ($v) => $field->family() === FieldInfo::FAMILY_LINK ?
                    ($v === 'r1' ? 'Видимая' : '(нет доступа)') : (string) $v, $values);
            }
        };
    }

    public function testConditionText(): void
    {
        $definition = (new DefinitionParser(new FakeSchema()))->parse([
            'type' => 'tabular', 'entityType' => 'Invoice', 'columns' => ['name'],
            'filters' => ['type' => 'and', 'items' => [
                ['field' => 'status', 'where' => ['type' => 'in', 'attribute' => 'status', 'value' => ['Draft', 'Sent']]],
                ['field' => 'account', 'where' => ['type' => 'in', 'attribute' => 'accountId', 'value' => ['r1', 'r2']],
                    'advanced' => ['data' => ['oneOfNameHash' => ['r1' => 'Видимая', 'r2' => 'Секретная']]]],
                ['type' => 'or', 'items' => [
                    ['field' => 'dateInvoiced', 'where' => ['type' => 'lastXDays', 'attribute' => 'dateInvoiced',
                        'value' => 7]],
                    ['field' => 'dateInvoiced', 'where' => ['type' => 'currentMonth', 'attribute' => 'dateInvoiced']],
                ]],
                ['field' => 'dateDue', 'where' => ['type' => 'compareField', 'attribute' => 'dateDue',
                    'value' => ['operator' => 'lessThan', 'field' => 'dateInvoiced']]],
                ['field' => 'grandTotal', 'where' => ['type' => 'between', 'attribute' => 'grandTotal',
                    'value' => ['10', '20.5']]],
                ['field' => 'description', 'where' => ['type' => 'isNull', 'attribute' => 'description']],
            ]],
        ]);
        $text = ConditionText::describe($definition->filters, $definition->filterFields, $this->words());

        $this->assertSame('status: [in] Draft, Sent И account: [in] Видимая, (нет доступа) И ' .
            '(dateInvoiced: [lastXDays]: 7 ИЛИ dateInvoiced: [currentMonth]) И dateDue: lessThan dateInvoiced И ' .
            'grandTotal: [between] 10 — 20.5 И description: [isNull]', $text);
        $this->assertTrue(!str_contains($text, 'Секретная'), 'a hidden record stays out of the text');
        $this->assertSame('', ConditionText::describe(['type' => 'and', 'items' => []], [], $this->words()));
    }

    public function testLetterBody(): void
    {
        $this->assertSame('Свой заголовок', LetterBody::subject('Свой заголовок', 'Отчёт', '05.10.2026 09:00'));
        $this->assertSame('Отчёт — 05.10.2026 09:00', LetterBody::subject('', 'Отчёт', '05.10.2026 09:00'));
        $this->assertSame('Отчёт x — 1', LetterBody::subject('', "Отчёт\r\nx", '1'));

        $html = LetterBody::html("Привет <b>\nвторая", [['Условия', 'a < b']], ['Ограничено'], 'Открыть отчёт',
            'http://crm.example.test/#Report/view/1"x');

        $this->assertSame('<p>Привет &lt;b&gt;<br>' . "\n" . 'вторая</p><table cellpadding="3" cellspacing="0" ' .
            'border="0"><tr><td valign="top"><b>Условия</b></td><td>a &lt; b</td></tr></table><p><i>Ограничено</i>' .
            '</p><p><a href="http://crm.example.test/#Report/view/1&quot;x">Открыть отчёт</a></p>', $html);
        $this->assertTrue(!str_contains(LetterBody::html('x', [], [], null, null), '<a '), 'no link');
    }
}
