from sqlalchemy import create_engine, text
engine = create_engine('postgresql+psycopg2://postgres:1234567@localhost:5432/fixed_asset_test_db')
with engine.connect() as conn:
    result = conn.execute(text('SELECT COUNT(*) FROM assets'))
    print(f'Assets in DB: {result.scalar()}')
