# Шрифт печатных форм

Liberation Sans 2.1.5 (Regular, Bold, Italic, BoldItalic) — метрически совместим с Arial, которым набраны печатные
формы SalesPlatform, поэтому ширины колонок и переносы строк форм совпадают с источником (этап 05, D-82). Кириллица,
«№» и неразрывный пробел есть; знака «₽» нет — формы пишут «руб.».

Происхождение: пакет Ubuntu 24.04 `fonts-liberation` 1:2.1.5-3 (`/usr/share/fonts/truetype/liberation/`), файлы без
изменений. Лицензия — SIL Open Font License 1.1, текст и правообладатели — `OFL.txt`.

| Файл | sha256 |
|---|---|
| `LiberationSans-Regular.ttf` | `4659bc0c58c5028dd488ec928d41d9265db43d9b669fc14ca8b0832daca7b144` |
| `LiberationSans-Bold.ttf` | `3973aa5054fb467dd5627245d3dc82e37bf16fe075756156a570455871351582` |
| `LiberationSans-Italic.ttf` | `830c5fa600505fb4c1a271b4271c53c44bae43f492b2a240d0e98a3a7a380121` |
| `LiberationSans-BoldItalic.ttf` | `c80fa7f2ffa0e01d4d8dcd6a6d1e43eda665222d1b4db597dde1174c456006cf` |

Регистрация в Dompdf — `metadata/app/pdfEngines.json` модуля; кэш метрик шрифтов (`data/cache/application/dompdf`)
очищает `task model:apply` (clear-cache), после развёртывания на сервере — то же.
