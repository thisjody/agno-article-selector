#!/usr/bin/env python3
"""Explore MotherDuck to find the articles source table."""

import os
from dotenv import load_dotenv
import duckdb

load_dotenv()

def explore_motherduck():
    """Explore MotherDuck databases and tables."""
    
    token = os.getenv("MOTHERDUCK_TOKEN")
    
    print("🔄 Connecting to MotherDuck...")
    
    try:
        # Connect without specifying database to see all databases
        conn = duckdb.connect(f"md:?motherduck_token={token}")
        print("✅ Connected!")
        
        # List all databases
        databases = conn.execute("SHOW DATABASES").fetchall()
        print(f"\n📚 Available databases:")
        for db in databases:
            print(f"   - {db[0]}")
        
        # Check each database for tables
        for db in databases:
            db_name = db[0]
            if db_name not in ['system', 'temp']:  # Skip system databases
                print(f"\n📁 Database: {db_name}")
                try:
                    conn.execute(f"USE {db_name}")
                    tables = conn.execute("SHOW TABLES").fetchall()
                    if tables:
                        print(f"   Tables:")
                        for table in tables:
                            print(f"      - {table[0]}")
                            # Get row count
                            try:
                                count = conn.execute(f"SELECT COUNT(*) FROM {table[0]}").fetchone()[0]
                                print(f"        ({count} rows)")
                            except:
                                pass
                    else:
                        print(f"   No tables")
                except Exception as e:
                    print(f"   Error accessing: {e}")
        
        # Check for article-related tables in newsletter-data
        print("\n🔍 Checking newsletter-data database in detail...")
        conn.execute("USE `newsletter-data`")
        
        # Look for any table with article/news/feed in the name
        all_tables = conn.execute("SHOW TABLES").fetchall()
        print(f"\nAll tables in newsletter-data:")
        for table in all_tables:
            table_name = table[0]
            print(f"\n  Table: {table_name}")
            
            # Get schema for each table
            try:
                schema = conn.execute(f"DESCRIBE {table_name}").fetchall()
                print(f"  Columns: {', '.join([col[0] for col in schema[:5]])}...")
                
                # Get sample data
                sample = conn.execute(f"SELECT * FROM {table_name} LIMIT 1").fetchone()
                if sample and len(sample) > 0:
                    print(f"  Sample: {str(sample[0])[:100]}...")
            except Exception as e:
                print(f"  Error: {e}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🦆 MOTHERDUCK EXPLORATION")
    print("="*60 + "\n")
    
    explore_motherduck()