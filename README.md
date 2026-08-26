# Peer Prep Academy — Meta carousel ads

Five 1080×1080 carousel cards plus a contact sheet, generated with Python + Pillow.

## Regenerate

```
pip install Pillow
./fetch_fonts.sh          # Instrument Serif + Inter variable, from google/fonts
python3 generate_cards.py
```

Outputs land in `output/`: `card1.png` … `card5.png` and `preview_strip.png`.

## Brand system

| role            | value                                          |
| --------------- | ---------------------------------------------- |
| background      | `#0F1E30` navy                                 |
| primary text    | `#F7F3EA` warm paper                           |
| accent          | `#CBA254` gold                                 |
| secondary text  | `#A8B2C0` muted slate                          |
| display type    | Instrument Serif                               |
| label/body type | Inter variable, weights via `set_variation_by_axes` |

Every card carries the tracked-out `PEER PREP ACADEMY` wordmark top-left over a
short gold underline, 92px margins, and the scantron A–E bubble strip
bottom-right — the filled gold bubble advances one position per card, so the
strip doubles as a position indicator across the carousel.

Photos are EXIF-corrected, square-cropped, mapped to a navy duotone
(`#091320` shadows → soft blue-grey highlights) and scrimmed so type stays
legible without hiding the picture.

## Quality gate

`check_safe_area()` records the bounding box of every mark drawn and fails the
build if anything lands within 60px of an edge. Current minimum edge gap is
88px on every card. Cards were also reviewed at feed-thumbnail size.
