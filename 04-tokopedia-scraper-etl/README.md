# Tokopedia Product Scraper and ETL Pipeline

A Selenium scraper that collects product listings from Tokopedia (Indonesia's largest
marketplace), and an ETL pipeline that turns the raw page text into a queryable warehouse
for inventory analysis.

## 1. Scraper

`notebooks/tokopedia_scraper.ipynb`

Headless Chrome via Selenium, driven by `webdriver-manager` so no manual driver setup is
needed. The scraper opens a search URL, scrolls to trigger lazy loading, and parses each
product card with BeautifulSoup into seven fields:

| Field | Example |
|---|---|
| Produk | "MOFT 2-in-1 Tas Laptop Sleeve & Stand" |
| Harga | `Rp2.000.000` |
| Promo | promotional label, often absent |
| Rating | `4.9` |
| Terjual | `100+ terjual` |
| Penjual | `naladda_store` |
| Lokasi | `Jakarta Barat` |

**Live scraping is opt-in.** It runs only with `LIVE_SCRAPE=1`; otherwise the notebook
loads the archived scrape. Two reasons: Tokopedia's markup changes frequently, so a
notebook pinned to today's DOM would break; and repeatedly scraping a live commercial site
is not a reasonable thing for a portfolio demo to do on every run.

`data/tokopedia_raw.csv` holds **60 listings** for the search term "macbook", scraped
September 2025.

## 2. ETL pipeline

`etl.py`, run with `python etl.py`

The scrape captures page text, which is not analysable as-is. The transform step:

- **Price**: `Rp2.000.000` to `2000000`. Indonesian formatting uses `.` as the thousands
  separator, so a naive numeric cast yields 2.0
- **Units sold**: `100+ terjual` to `100`, handling the `rb` (thousand) and `jt` (million)
  suffixes. The `+` means "at least", so the field is named `units_sold_min` rather than
  implying an exact count
- **Rating**: to float, preserving genuine missingness (new listings have no rating)
- **Promo**: presence of a label becomes a boolean, text retained separately
- **Revenue floor**: `price x units_sold_min`, a lower bound on gross revenue

Load is into SQLite (`data/tokopedia.db`) as a small star schema: `dim_seller` and
`fact_listing`, with two analysis views.

### Output

```
loaded 60 listings

price (IDR):  min 59,000   median 550,547   max 44,799,000
promo listings: 27/60
rating present: 58/60      sales figure present: 58/60

listings by location:
   Jakarta Pusat      21 listings   avg Rp3,077,621
   Jakarta Barat      19 listings   avg Rp629,105
   Bekasi             11 listings   avg Rp308,809

top sellers by floor revenue:
   WiWU Official         11 listings   >= Rp212,903,200
   naladda_store          1 listings   >= Rp200,000,000
   Incase Indonesia      19 listings   >= Rp191,927,050
```

Two things the data shows: listings concentrate heavily in Greater Jakarta, and Jakarta
Pusat's average price is five times Jakarta Barat's; official brand stores cluster there,
while the cheaper locations sell accessories. The `naladda_store` row is a caution about
the metric: a single listing with a high "100+ sold" floor ranks near the top, so floor
revenue rewards one popular item as much as a broad catalogue.

## Running it

```bash
pip install -r requirements.txt
python etl.py                                    # transform + load + summary
jupyter notebook notebooks/tokopedia_scraper.ipynb

LIVE_SCRAPE=1 jupyter notebook ...               # to scrape fresh (needs Chrome)
```

`etl.py` asserts its own parsing on known cases and fails loudly if a price goes missing or
non-positive, so a Tokopedia format change surfaces as a failed assertion rather than
silently wrong numbers.

## Notes

Coursework for E-commerce, Semester 5. Individual work.

**The scraper is the original submission; `etl.py` is new.** The coursework ended at
`df.to_csv(...)`; there was no cleaning, transformation or warehouse load. The ETL here
was written to complete the pipeline the project implies, and is clearly separated from the
original notebook rather than folded into it.

The archived scrape is 60 listings. Scraping more is a matter of raising `max_scroll` and
widening the search terms; the pipeline is not row-count dependent.
