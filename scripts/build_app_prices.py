"""Turn the weekly chain catalogs into the price list the meal-plan app reads.

Reads  mapping.json, data/meta.json, data/<chain>.csv
Writes data/app-prices.json        current price per shopping-list item and chain
       history/prices.csv          one line per item, chain and price date (appended once per date)
"""
import csv, json, re, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MIN_AVAIL = 0.5   # replacement products must be listed in at least half the chain's stores

def norm(s):
    return unicodedata.normalize("NFKD", s.lower()).encode("ascii", "ignore").decode()

def main():
    mapping = json.loads((ROOT / "mapping.json").read_text(encoding="utf-8"))
    meta = json.loads((ROOT / "data/meta.json").read_text(encoding="utf-8"))
    out = {"chains": {}}
    hist_rows = []
    for ch, label in mapping["chains"].items():
        f = ROOT / f"data/{ch}.csv"
        if ch not in meta or not f.exists():
            continue
        rows = list(csv.DictReader(f.open(encoding="utf-8")))
        by_id = {r["product_id"]: r for r in rows}
        n_stores = max(1, meta[ch]["stores"])
        date = meta[ch]["date"]
        items = {}
        for key, m in mapping["items"].items():
            spec = m.get(ch)
            if not spec:
                continue
            r = by_id.get(spec["id"])
            replaced = False
            if r is None and m.get("find"):
                # same kind of product, closest pack size, cheapest per unit, widely stocked
                pat = re.compile(m["find"])
                cands = [x for x in rows if pat.search(norm(x["name"])) and int(x["stores"] or 0) / n_stores >= MIN_AVAIL]
                def per_unit(x):
                    try:
                        return float(x["price_median"]) / float(x["quantity"])
                    except (ValueError, ZeroDivisionError):
                        return 1e9
                cands.sort(key=per_unit)
                if cands:
                    r, replaced = cands[0], True
            if r is None:
                continue
            price = float(r["price_median"])
            name = r["name"].strip() + (f" ({spec['note']})" if spec.get("note") else "") + (" · zamjena" if replaced else "")
            avail = min(1.0, int(r["stores"] or 0) / n_stores)
            if spec.get("loose"):
                item = {"n": name, "loose": 1, "st": spec.get("st", 100), "perKg": price}
            else:
                pk = spec["pk"]
                if replaced:
                    try:
                        q = float(r["quantity"])
                        pk = round(q * 1000) if q < 50 and spec["pk"] >= 50 else spec["pk"]
                    except ValueError:
                        pass
                item = {"n": name, "pk": pk, "pp": price}
            if avail < MIN_AVAIL:
                item["n"] += " · u malo poslovnica"
            item["id"] = r["product_id"]
            items[key] = item
            hist_rows.append([date, ch, key, r["product_id"], r["name"].strip(), item.get("pk", "kg"), f"{price:.2f}", r["price_min"]])
        out["chains"][ch] = {"name": label, "date": date, "items": items}
    dates = [c["date"] for c in out["chains"].values()]
    out["date"] = max(dates) if dates else None
    (ROOT / "data/app-prices.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    hist = ROOT / "history/prices.csv"
    hist.parent.mkdir(exist_ok=True)
    seen = set()
    if hist.exists():
        for r in csv.DictReader(hist.open(encoding="utf-8")):
            seen.add((r["date"], r["chain"]))
    new = [r for r in hist_rows if (r[0], r[1]) not in seen]
    write_header = not hist.exists()
    with hist.open("a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if write_header:
            w.writerow(["date", "chain", "item", "product_id", "product", "pack", "price_median", "price_min"])
        w.writerows(new)
    print(f"app-prices: {sum(len(c['items']) for c in out['chains'].values())} items; history +{len(new)} rows")

if __name__ == "__main__":
    main()
