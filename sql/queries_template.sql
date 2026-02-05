/*
TEMPLATE ONLY — do not paste real credentials here.

Replace placeholders with your own table names / filters if you later connect a warehouse.
*/

-- Example: monthly sales fact
SELECT
  sku,
  DATE_TRUNC('month', order_date) AS month,
  AVG(unit_price) AS ticket_price,
  SUM(quantity) AS qty_sold,
  SUM(CASE WHEN is_return = 1 THEN quantity ELSE 0 END) AS returns
FROM <FACT_SALES_TABLE>
WHERE order_date >= <START_DATE> AND order_date < <END_DATE>
GROUP BY 1, 2;

-- Example: unit cost
SELECT
  sku,
  MAX(unit_cost) AS unit_cost
FROM <COST_TABLE>
GROUP BY 1;
