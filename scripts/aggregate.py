"""Turn one day's crawler output for a chain into a compact price catalog.

Input:  <out>/<YYYY-MM-DD>/<chain>/{stores,products,prices}.csv  (cijene-api crawler format)
Output: data/<chain>.csv   one row per product with chain-wide price statistics
        data/meta.json     per chain: crawl date and row counts
"""
import csv, json, statistics, sys
from pathlib import Path

def main(out_root: str, data_dir: str, chain: str) -> None:
    days = sorted(p for p in Path(out_root).iterdir() if p.is_dir())
    if not days:
        sys.exit("no crawl output found")
    day = days[-1]
    src = day / chain
    products = {}
    with open(src / "products.csv", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            products[r["product_id"]] = r
    stores = set()
    prices, specials, avail = {}, {}, {}
    with open(src / "prices.csv", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            stores.add(r["store_id"])
            pid = r["product_id"]
            if r.get("available") == "0":
                continue
            try:
                p = float(r["price"])
            except (TypeError, ValueError):
                continue
            if p <= 0:
                continue
            prices.setdefault(pid, []).append(p)
            sp = r.get("special_price") or ""
            try:
                if sp and float(sp) > 0:
                    specials.setdefault(pid, []).append(float(sp))
            except ValueError:
                pass
    out = Path(data_dir); out.mkdir(parents=True, exist_ok=True)
    cols = ["barcode", "product_id", "name", "brand", "category", "unit", "quantity",
            "price_median", "price_min", "price_max", "special_min", "stores"]
    rows = 0
    with open(out / f"{chain}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for pid, ps in sorted(prices.items(), key=lambda kv: products.get(kv[0], {}).get("name", "")):
            pr = products.get(pid)
            if not pr:
                continue
            sp = specials.get(pid)
            w.writerow([pr.get("barcode", ""), pid, pr.get("name", ""), pr.get("brand", ""),
                        pr.get("category", ""), pr.get("unit", ""), pr.get("quantity", ""),
                        f"{statistics.median(ps):.2f}", f"{min(ps):.2f}", f"{max(ps):.2f}",
                        f"{min(sp):.2f}" if sp else "", len(ps)])
            rows += 1
    meta_path = out / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    meta[chain] = {"date": day.name, "stores": len(stores), "products": rows}
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{chain} {day.name}: {rows} products, {len(stores)} stores")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
