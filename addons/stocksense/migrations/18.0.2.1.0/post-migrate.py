def migrate(cr, version):
    """Turn the former free-text product category into category records."""
    cr.execute("""
        SELECT 1 FROM information_schema.columns
         WHERE table_name = 'stocksense_product' AND column_name = 'category'
    """)
    if not cr.fetchone():
        return
    cr.execute("""
        INSERT INTO stocksense_product_category (name, company_id, create_date, write_date)
        SELECT DISTINCT trim(category), company_id, NOW() AT TIME ZONE 'UTC', NOW() AT TIME ZONE 'UTC'
          FROM stocksense_product
         WHERE coalesce(trim(category), '') != ''
        ON CONFLICT DO NOTHING
    """)
    cr.execute("""
        UPDATE stocksense_product p
           SET category_id = c.id
          FROM stocksense_product_category c
         WHERE c.name = trim(p.category) AND c.company_id = p.company_id AND p.category_id IS NULL
    """)
    cr.execute("ALTER TABLE stocksense_product DROP COLUMN category")
