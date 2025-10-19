#!/usr/bin/env python3
import psycopg2
import sys

print("Starting database connection test...")

try:
    print("Attempting to connect to database...")
    conn = psycopg2.connect(
        dbname="hubdb",
        user="admin",
        password="password",
        host="localhost",
        port="5432"
    )
    print("Connection established!")
    
    cur = conn.cursor()
    print("Executing test query...")
    cur.execute("SELECT NOW();")
    result = cur.fetchone()
    print("✅ Database connected successfully! Current time:", result)
    
    # Test if tables exist
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
    tables = cur.fetchall()
    print("📋 Available tables:", [table[0] for table in tables])
    
except Exception as e:
    print("❌ Connection failed:", e)
    sys.exit(1)
finally:
    if 'conn' in locals():
        conn.close()
        print("🔌 Connection closed.")

print("✅ Test completed successfully!")