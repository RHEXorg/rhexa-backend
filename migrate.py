from app.db.session import engine
from sqlalchemy import text

with engine.connect() as conn:
    try:
        conn.execute(text('ALTER TABLE organizations ADD COLUMN subscription_tier VARCHAR DEFAULT "free_trial"'))
        conn.execute(text('ALTER TABLE organizations ADD COLUMN trial_ends_at TIMESTAMP WITH TIME ZONE'))
        conn.execute(text('ALTER TABLE organizations ADD COLUMN billing_cycle VARCHAR'))
        conn.execute(text('ALTER TABLE organizations ADD COLUMN is_active INTEGER DEFAULT 1'))
        conn.commit()
        print('Columns added successfully')
    except Exception as e:
        print(f'Error or column already exists: {e}')
