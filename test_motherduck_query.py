#!/usr/bin/env python3
"""Query the actual MotherDuck newsletter_selections table."""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
import duckdb

# Load environment variables
load_dotenv()

def query_newsletter_selections():
    """Query the newsletter_selections table."""
    
    token = os.getenv("MOTHERDUCK_TOKEN")
    database = os.getenv("MOTHERDUCK_DATABASE", "newsletter-data")
    
    print(f"🔄 Connecting to MotherDuck database: {database}")
    
    try:
        conn = duckdb.connect(f"md:{database}?motherduck_token={token}")
        print("✅ Connected successfully!")
        
        # Get table schema
        schema = conn.execute("DESCRIBE newsletter_selections").fetchall()
        print("\n📋 Table schema for newsletter_selections:")
        for col in schema[:10]:  # Show first 10 columns
            print(f"   {col[0]}: {col[1]}")
        
        # Get record count
        count = conn.execute("SELECT COUNT(*) FROM newsletter_selections").fetchone()[0]
        print(f"\n📚 Total records: {count}")
        
        # Check for date columns
        date_cols = [col[0] for col in schema if 'date' in col[0].lower() or 'time' in col[0].lower()]
        print(f"\n📅 Date/time columns found: {date_cols}")
        
        # Sample recent records
        print("\n📰 Sample records (last 5):")
        sample = conn.execute("""
            SELECT * FROM newsletter_selections 
            LIMIT 5
        """).fetchall()
        
        if sample:
            # Get column names
            col_names = [col[0] for col in schema]
            
            for row in sample:
                print("\n" + "-"*40)
                for i, value in enumerate(row[:10]):  # Show first 10 fields
                    if i < len(col_names):
                        print(f"   {col_names[i]}: {str(value)[:100]}")
        
        # Check if there's a date range
        if date_cols:
            date_col = date_cols[0]
            date_range = conn.execute(f"""
                SELECT 
                    MIN({date_col}) as earliest,
                    MAX({date_col}) as latest
                FROM newsletter_selections
            """).fetchone()
            
            print(f"\n📆 Date range in {date_col}:")
            print(f"   Earliest: {date_range[0]}")
            print(f"   Latest: {date_range[1]}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🦆 MOTHERDUCK NEWSLETTER_SELECTIONS QUERY")
    print("="*60 + "\n")
    
    query_newsletter_selections()