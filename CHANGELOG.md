# Changelog

Updates may follow, no promises. / Обновления возможны, но не обещаны.

## v4 — 2026-11-25

- Build 4.001 refines lowercase a/а and e/е crossbars and the wide s. The a/а bowl blends into the upright above width 125. The crossbar study opens at the released 110% setting.
- Extended the variable width range from 100–125 to 100–175. The weight range is 100–900.
- Reworked extended Latin and Cyrillic strokes, counters and joins, including Z, K/К, Жж, У, м, Ю and X/Х. Retuned pair spacing for wide settings, including YA, AT and АТ.
- Added optical-size tracking with linear interpolation through 8, 12, 24 and 48. The corresponding additions are 0.054, 0.038, 0.020 and 0 em.
- Added a local playground with reference overlays, editable tracking and TTF export. The release font uses the low У junction and stroke setting 80.
- Shipped variable TTF and WOFF2 under the separate family name Sovershenen Pizdets v4 for side-by-side installation with 3.17.

[Описание обновления на русском](docs/v4.ru.md)

## 3.17 — 2026-10-29
- Default width narrowed: statics and named instances at `wdth` 107 (was 116); Black at ≈ `wdth` 110 (was 127). Weights re-fitted for the narrower default.
- Soft-sign bowls Ь Б Ъ Ы (and ь ъ ы) raised and evened out across weights.
- Д д: narrower span of feet and base overhang in the middle weights; thicknesses unchanged.

## 3.16 — 2026-10-26
First public release as Sovershenen Pizdets (based on Saira, SIL OFL 1.1).
- Full Cyrillic (RU/UA/BY) built on Saira's own masters; redrawn Б В Д Ж З Л У Ф Ы Ь Ъ Ю Я, breve for Й Ў, lowercase counterparts.
- Redrawn Latin letters and figures; square-grotesque terminals.
- Scaled to cap height 667, x-height 75% of cap, tracking −5% built in.
- Weights rebalanced for even colour; Heavy → Black widens gradually (Black ≈ wdth 127).
- Weight-aware construction for У Л Д Ы Ю and bowls (stable shapes from Thin to Black).
- Figures 2 3 5 6 8 9 and З з С с tuned per weight: corner fullness, bar weights, apertures.
- Cyrillic kerning and collision fixes across all masters.
