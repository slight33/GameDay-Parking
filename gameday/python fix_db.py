# One-time fix: adds any columns the users table is missing, without deleting anything.
import sqlite3

con = sqlite3.connect("gameday.db")
# Ask the database which columns the users table already has.
have = {row[1] for row in con.execute("PRAGMA table_info(users)")}
# Add each column the app expects if it isn't there yet.
for col, kind in [("role", "VARCHAR DEFAULT 'guest'"), ("address", "VARCHAR"), ("lat", "FLOAT"), ("lng", "FLOAT")]:
    if col not in have:
        con.execute(f"ALTER TABLE users ADD COLUMN {col} {kind}")
        print("Added", col)
con.commit()
print("Done.")