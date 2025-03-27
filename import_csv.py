import pandas as pd
import sqlite3
from werkzeug.security import generate_password_hash

# Define database and CSV file paths
DB_PATH = r"/Users/melisha/Desktop/karaval project/KKA_WEBSITE/database.db"
CSV_PATH = r"/Users/melisha/Desktop/karaval project/KKA_WEBSITE/KKA.csv"

# Load CSV data
df = pd.read_csv(CSV_PATH)

# Debug: Print first few rows to check data
print("✅ Loaded", len(df), "users from CSV.")
print(df.info())  # Check for missing values and data types
print(df.head())  # Preview first few rows

# Convert phone numbers and passwords to strings
df["phone"] = df["phone"].astype(str)
df["password"] = df["password"].astype(str)

# Remove duplicate emails before inserting
df = df.drop_duplicates(subset=["email"])

# Hash passwords before storing them in the database
df["password"] = df["password"].apply(generate_password_hash)

# Connect to SQLite database
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Ensure the table exists with the correct schema
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    phone TEXT NOT NULL
);
""")

# *Delete any conflicting emails before inserting*
for index, row in df.iterrows():
    cursor.execute("DELETE FROM users WHERE email = ?", (row["email"],))

# Insert data row by row (avoiding conflicts with auto-increment `user_id`)
for _, row in df.iterrows():
    cursor.execute(
        "INSERT INTO users (name, email, password, phone) VALUES (?, ?, ?, ?)",
        (row["name"], row["email"], row["password"], row["phone"])
    )

# Commit and close connection
conn.commit()
conn.close()

print("✅ CSV data successfully added to the database!")
