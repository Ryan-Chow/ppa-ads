# Peer Prep Academy — pitch deck (UCSD Basement LaunchPad)

Title + 5 content slides, 16:9 (1600×900), blueprint brand.

- `deck.html` — source, one `<section class="slide">` per slide
- `peer-prep-pitch-deck.pdf` — final deck
- `previews/` — PNG render of each PDF page

## Rebuild

```
NODE_PATH=$(npm root -g) node render.mjs   # writes the PDF, prints any overflow/clipping
python3 -c "import pypdfium2 as p; d=p.PdfDocument('peer-prep-pitch-deck.pdf'); [d[i].render(scale=4/3).to_pil().save(f'previews/{i:02d}.png') for i in range(len(d))]"
```

Use pdfium (Chrome's renderer) for previews: poppler's `pdftoppm` washes out the CSS gradients.
