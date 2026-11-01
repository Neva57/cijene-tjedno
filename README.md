# cijene-tjedno

Every Thursday, a GitHub Action runs the open-source [cijene-api](https://github.com/senko/cijene-api) crawler for two Croatian retail chains (Lidl and Kaufland). It saves a compact price catalog to `data/`.

- `data/lidl.csv` and `data/kaufland.csv`: one row per product: barcode, name, brand, category, unit, quantity, and the median/min/max shelf price across stores, plus the lowest special price.
- `data/meta.json`: the crawl date and counts.

The source is the price lists that chains have to publish under NN 75/2025. Only public price data is stored here.

To run it now, go to Actions → "Tjedne cijene" → "Run workflow".
