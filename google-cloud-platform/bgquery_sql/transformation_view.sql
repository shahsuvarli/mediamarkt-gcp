CREATE OR REPLACE VIEW `mediamarkt-466920.website_data.v_mm_products`
AS
SELECT
  brand_name,
  category_name,
  product_title,
  product_price as price_eur,

  SAFE_CAST(
    REGEXP_EXTRACT(product_rating_aria_label, r'([0-9]+\.[0-9]+)') AS FLOAT64
  ) AS rating_out_of_5

FROM (
  SELECT DISTINCT *
  FROM `mediamarkt-466920.website_data.mm_products`
)
WHERE brand_name IS NOT NULL
  AND product_title IS NOT NULL