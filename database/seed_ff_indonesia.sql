-- Первичное наполнение доната Free Fire — Индонезия.
-- Замените :ff_game_id на id игры Free Fire из таблицы games.
-- После миграции subcategory товары СНГ: subcategory = 'cis' (или NULL).

-- ALTER TABLE products ADD COLUMN subcategory TEXT DEFAULT 'cis';  -- если колонки ещё нет

INSERT INTO products (game_id, label, price_tjs, is_popular, is_best_value, is_active, sort_order, subcategory)
SELECT :ff_game_id, label, price_tjs, 0, 0, 1, sort_order, 'indonesia'
FROM (
  SELECT '💎 100 Diamond' AS label, 12.00 AS price_tjs, 1 AS sort_order
  UNION ALL SELECT '💎 150 Diamond', 17.00, 2
  UNION ALL SELECT '💎 210 Diamond', 22.00, 3
  UNION ALL SELECT '💎 420 Diamond', 45.00, 4
  UNION ALL SELECT '💎 500 Diamond', 55.00, 5
  UNION ALL SELECT '💎 800 Diamond', 90.00, 6
  UNION ALL SELECT '💎 1000 Diamond', 105.00, 7
  UNION ALL SELECT '🗓️ Ваучери ҳафтагӣ', 25.00, 8
  UNION ALL SELECT '🎫 Ваучери моҳона', 85.00, 9
) AS seed
WHERE NOT EXISTS (
  SELECT 1 FROM products
  WHERE game_id = :ff_game_id AND subcategory = 'indonesia'
);
