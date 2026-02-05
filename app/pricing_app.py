from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from flask import Flask, render_template_string, request

from src.pricing_engine.elasticity import estimate_elasticity_loglog
from src.pricing_engine.seasonality import fit_month_of_year_index, apply_seasonality_adjustment
from src.pricing_engine.simulator import recommend_prices

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = ROOT / "data" / "sample"

HTML = """<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>Pricing Optimization Demo</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 24px; }
    .box { padding: 14px; border: 1px solid #ddd; border-radius: 10px; margin-bottom: 16px; }
    table { border-collapse: collapse; width: 100%; font-size: 13px; }
    th, td { border: 1px solid #eee; padding: 8px; text-align: right; }
    th { background: #f5f5f5; }
    td:first-child, th:first-child { text-align: left; }
    .muted { color: #666; font-size: 13px; }
    code { background: #f7f7f7; padding: 2px 6px; border-radius: 6px; }
  </style>
</head>
<body>
  <h1>Pricing Optimization Engine — Demo</h1>
  <p class="muted">
    Reads <code>data/sample/*.csv</code>, detects month-of-year seasonality, estimates deseasonalized elasticity per SKU, and recommends profit-maximizing prices
    under ladder constraints. No DB / secrets are used.
  </p>

  <div class="box">
    <form method="get">
      Top N rows:
      <input name="top" type="number" value="{{top}}" min="5" max="500"/>
      <button type="submit">Run</button>
    </form>
  </div>

  <div class="box">
    <b>Summary</b><br/>
    <span class="muted">SKUs: {{n_skus}} | Modeled: {{n_modeled}} | Avg uplift (modeled): {{avg_uplift}}</span>
  </div>

  <div class="box">
    <b>Recommendations (Top {{top}} by uplift %)</b>
    {{table | safe}}
  </div>
</body>
</html>"""


def load_demo() -> tuple[pd.DataFrame, pd.DataFrame]:
    sales = pd.read_csv(SAMPLE_DIR / "sample_sales.csv")
    ladders = pd.read_csv(SAMPLE_DIR / "sample_price_ladders.csv")
    return sales, ladders


def run_engine() -> pd.DataFrame:
    sales, ladders = load_demo()
    seasonality = fit_month_of_year_index(sales)
    sales_adj = apply_seasonality_adjustment(sales, seasonality)
    elasticity = estimate_elasticity_loglog(sales_adj, qty_col="qty_deseasonalized")
    recs = recommend_prices(sales_adj, elasticity, ladders, seasonality_df=seasonality, qty_col="qty_deseasonalized")
    return recs


app = Flask(__name__)


@app.get("/")
def index():
    top = int(request.args.get("top", 25))
    recs = run_engine()

    n_skus = recs["sku"].nunique()
    n_modeled = int((recs["status"] == "ok").sum())
    avg_uplift = recs.loc[recs["status"] == "ok", "uplift_pct"].mean()
    avg_uplift = f"{avg_uplift:,.2f}%" if pd.notna(avg_uplift) else "N/A"

    show = recs.head(top).copy()
    for c in ["current_price","optimal_price","expected_demand_current","expected_demand_optimal","current_profit","optimal_profit","uplift_pct"]:
        show[c] = show[c].map(lambda x: f"{x:,.2f}")

    table = show.to_html(index=False, escape=True)

    return render_template_string(
        HTML, table=table, top=top, n_skus=n_skus, n_modeled=n_modeled, avg_uplift=avg_uplift
    )


if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", "8055"))
    app.run(host="0.0.0.0", port=port, debug=True)
