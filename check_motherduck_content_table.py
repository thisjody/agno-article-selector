#!/usr/bin/env python3
"""Check for the content table in MotherDuck that ADK uses."""

import os
from dotenv import load_dotenv
import duckdb
from datetime import datetime

load_dotenv()

def check_content_table():
    """Check for newsletter_data.content table in MotherDuck."""
    
    token = os.getenv("MOTHERDUCK_TOKEN")
    database = os.getenv("MOTHERDUCK_DATABASE", "newsletter-data")
    
    print(f"🔄 Connecting to MotherDuck database: {database}")
    
    try:
        # Connect to MotherDuck
        conn = duckdb.connect(f"md:{database}?motherduck_token={token}")
        print("✅ Connected!")
        
        # Try the exact query ADK uses
        print("\n🔍 Checking for 'newsletter_data.content' table (ADK's table)...")
        try:
            # Try with schema qualification
            query = """
                SELECT COUNT(*) as count 
                FROM newsletter_data.content 
                WHERE timestamp IS NOT NULL
            """
            result = conn.execute(query).fetchone()
            print(f"   ✅ Found newsletter_data.content table with {result[0]} rows!")
            
            # Get sample
            sample_query = """
                SELECT title, url, body, timestamp 
                FROM newsletter_data.content 
                WHERE timestamp IS NOT NULL 
                AND body IS NOT NULL 
                AND LENGTH(body) > 0
                ORDER BY timestamp DESC
                LIMIT 3
            """
            samples = conn.execute(sample_query).fetchall()
            
            print("\n📰 Recent articles from content table:")
            for row in samples:
                title, url, body, timestamp = row
                print(f"\n   Title: {title[:80]}...")
                print(f"   URL: {url[:80]}...")
                print(f"   Body: {body[:150]}...")
                print(f"   Timestamp: {timestamp}")
                
            # Check date range
            date_range_query = """
                SELECT 
                    MIN(timestamp) as earliest,
                    MAX(timestamp) as latest,
                    COUNT(*) as total
                FROM newsletter_data.content
                WHERE timestamp >= '2025-08-13' 
                AND timestamp <= '2025-08-20'
            """
            date_result = conn.execute(date_range_query).fetchone()
            earliest, latest, count = date_result
            
            print(f"\n📅 Articles from Aug 13-20, 2025:")
            print(f"   Count: {count}")
            print(f"   Earliest: {earliest}")
            print(f"   Latest: {latest}")
            
        except Exception as e:
            print(f"   ❌ Error accessing newsletter_data.content: {e}")
            
            # Try without schema
            print("\n🔍 Trying 'content' table without schema...")
            try:
                result = conn.execute("SELECT COUNT(*) FROM content").fetchone()
                print(f"   ✅ Found content table with {result[0]} rows!")
            except:
                print("   ❌ No 'content' table found")
        
        # List all available tables
        print("\n📊 All available tables:")
        tables = conn.execute("SHOW TABLES").fetchall()
        for table in tables:
            print(f"   - {table[0]}")
            
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🦆 MOTHERDUCK CONTENT TABLE CHECK (ADK's Source)")
    print("="*60 + "\n")
    
    check_content_table()
    
    print("\n📝 The ADK version uses:")
    print("   - Table: newsletter_data.content")
    print("   - Columns: title, body (as content), url, timestamp")
    print("   - This is the raw articles source!")