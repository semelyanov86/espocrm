<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Mailing;

/**
 * Subject and HTML body of a report letter (D-123, D-124): the owner's text (or the default intro), the report info as
 * «label: value» lines, the notes of the limits and the link to the report (only for a reader who may open it). Every
 * text is escaped; the subject has no line breaks.
 */
final class LetterBody
{
    /**
     * The owner's subject, or «<title> — <date time>».
     */
    public static function subject(string $custom, string $title, string $when): string
    {
        $subject = $custom !== '' ? $custom : $title . ' — ' . $when;

        return trim(preg_replace('/[\x00-\x1F\x7F]+/u', ' ', $subject) ?? '');
    }

    /**
     * @param list<array{string, string}> $lines label and value
     * @param list<string> $notes
     */
    public static function html(string $intro, array $lines, array $notes, ?string $linkLabel, ?string $url): string
    {
        $html = '<p>' . nl2br(self::e($intro), false) . '</p>';

        if ($lines !== []) {
            $html .= '<table cellpadding="3" cellspacing="0" border="0">';

            foreach ($lines as [$label, $value]) {
                $html .= '<tr><td valign="top"><b>' . self::e($label) . '</b></td><td>' . nl2br(self::e($value), false) .
                    '</td></tr>';
            }

            $html .= '</table>';
        }

        foreach ($notes as $note) {
            $html .= '<p><i>' . self::e($note) . '</i></p>';
        }

        if ($url !== null && $linkLabel !== null) {
            $html .= '<p><a href="' . self::e($url) . '">' . self::e($linkLabel) . '</a></p>';
        }

        return $html;
    }

    private static function e(string $text): string
    {
        return htmlspecialchars($text, ENT_QUOTES | ENT_SUBSTITUTE | ENT_HTML5, 'UTF-8');
    }
}
