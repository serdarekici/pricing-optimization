import pandas as pd

from src.pricing_engine.elasticity import estimate_elasticity_loglog
from src.pricing_engine.seasonality import fit_month_of_year_index, apply_seasonality_adjustment
from src.pricing_engine.simulator import recommend_prices


def test_pipeline_runs_with_seasonality():
    sales = pd.read_csv("data/sample/sample_sales.csv")
    ladders = pd.read_csv("data/sample/sample_price_ladders.csv")

    seas = fit_month_of_year_index(sales)
    sales_adj = apply_seasonality_adjustment(sales, seas)

    elast = estimate_elasticity_loglog(sales_adj, qty_col="qty_deseasonalized")
    recs = recommend_prices(
        sales_adj,
        elast,
        ladders,
        seasonality_df=seas,
        qty_col="qty_deseasonalized",
    )

    assert len(recs) > 0
    required = {
        "sku",
        "current_price",
        "optimal_price",
        "uplift_pct",
        "seasonality_index",
        "seasonality_strength",
        "current_profit_seasonal",
        "optimal_profit_seasonal",
    }
    assert required.issubset(set(recs.columns))
