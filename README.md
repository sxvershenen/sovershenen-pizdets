# Sovershenen Pizdets

**v4 · Build 4.002** · SIL Open Font License 1.1

[Скачать TTF для установки](https://github.com/sxvershenen/sovershenen-pizdets/releases/download/v4/SovershenenPizdetsV4.ttf) · [Скачать WOFF2 для сайта](https://github.com/sxvershenen/sovershenen-pizdets/releases/download/v4/SovershenenPizdetsV4.woff2) · [Скачать статические OTF, TTF и WOFF2](https://github.com/sxvershenen/sovershenen-pizdets/releases/download/v4/SovershenenPizdetsV4-Static.zip) · [Описание релиза v4](https://github.com/sxvershenen/sovershenen-pizdets/releases/tag/v4)

**RU.** Квадратный гротеск на базе [Saira](https://github.com/Omnibus-Type/Saira) (Héctor Gatti, Omnibus-Type), которая распространяется под свободной лицензией SIL Open Font License 1.1. Добавлена полная кириллица (RU, UA, BY), перерисованы буквы и цифры, пересобраны метрики, веса и кернинг. Подходит для интерфейсов, навигации и техники.

**EN.** A square grotesque based on [Saira](https://github.com/Omnibus-Type/Saira) by Héctor Gatti / Omnibus-Type, which is free software under the SIL Open Font License 1.1. Adds full Cyrillic (Russian, Ukrainian, Belarusian), redraws letters and figures, and rebalances metrics, weights and kerning. Made for interfaces, wayfinding and technical use.

> Шрифт, возможно, будет обновляться, но это не обещание. / The font may get updates, but no promises.

## Установка / Installation

В меню шрифтов семейство называется **Sovershenen Pizdets**. При обновлении с 3.17 выберите замену установленного шрифта. / Install the variable TTF and replace the previous version when prompted.

[v4 · сборка 4.002](fonts/v4/) · [3.17 · архив](fonts/v3.17/)

| Версия | Вариативный TTF | Статические OTF | Статические TTF | WOFF2 для сайта |
|---|---|---|---|---|
| v4 | [Variable](fonts/v4/variable/) | [OTF](fonts/v4/otf/) | [TTF](fonts/v4/ttf/) | [Webfonts](fonts/v4/webfonts/) |
| 3.17 | [Variable](fonts/v3.17/variable/) | [OTF](fonts/v3.17/otf/) | [TTF](fonts/v3.17/ttf/) | [Webfonts](fonts/v3.17/webfonts/) |

Статические начертания v4 собраны из вариативного шрифта при ширине 107% и оптическом размере 16. Доступны Thin (100), Light (300), Regular (400), Medium (500), Bold (700), Heavy (800) и Black (900). Для настройки ширины до 175% и автоматического трекинга используйте вариативный файл.

Each version has its own folder. The seven v4 static styles use the named instances at width 107 and optical size 16. Choose one desktop format for installation: variable TTF, static TTF or static OTF.

## Оси v4 / Variable axes

| Ось | Диапазон | Назначение / Use |
|---|---|---|
| `wght` | 100–900 | Насыщенность / weight |
| `wdth` | 100–175% | Ширина / width |
| `opsz` | 8–48 | Трекинг для мелкого текста / size-dependent tracking |

Именованные начертания используют ширину 107%. При оптическом размере 8 трекинг раскрывается на 5,4% em, при 12 — на 3,8%, при 24 — на 2%, при 48 — на 0%. Между точками интервал меняется плавно.

```css
@font-face {
  font-family: "Sovershenen Pizdets";
  src: url("fonts/v4/webfonts/SovershenenPizdetsV4.woff2") format("woff2");
  font-weight: 100 900;
  font-stretch: 100% 175%;
}
.text {
  font-family: "Sovershenen Pizdets", sans-serif;
  font-stretch: 107%;
  font-optical-sizing: auto;
}
```

## License / Лицензия

SIL Open Font License 1.1, see [OFL.txt](OFL.txt). This is a Modified Version of Saira, © 2020 The Saira Project Authors (https://github.com/Omnibus-Type/Saira), released under the same license. Saira declares no Reserved Font Name. Not affiliated with or endorsed by Omnibus-Type.

Модифицированная версия Saira, © 2020 The Saira Project Authors, под той же лицензией OFL 1.1. Проект не связан с Omnibus-Type и не одобрен ими.
