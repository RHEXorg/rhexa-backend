import sqlite3

try:
    conn = sqlite3.connect("dev.db")
    cursor = conn.cursor()
    cursor.execute("ALTER TABLE widget_configs ADD COLUMN selected_sources JSON DEFAULT '{}';")
    conn.commit()
    print("Migration successful: Added selected_sources to widget_configs.")
except Exception as e:
    print(f"Error during migration (may already exist): {e}")
finally:
    conn.close()
