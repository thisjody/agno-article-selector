#!/usr/bin/env python3
"""Test MotherDuck connection and query articles for the last week."""

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
import duckdb

# Load environment variables
load_dotenv()

def test_motherduck_connection():
    """Test connection to MotherDuck and query recent articles."""
    
    # Get credentials
    token = os.getenv("MOTHERDUCK_TOKEN")
    database = os.getenv("MOTHERDUCK_DATABASE", "newsletter-data")
    
    if not token:
        print("❌ MOTHERDUCK_TOKEN not found in .env")
        return False
    
    print(f"🔄 Connecting to MotherDuck database: {database}")
    
    try:
        # Connect to MotherDuck
        conn = duckdb.connect(f"md:{database}?motherduck_token={token}")
        print("✅ Connected to MotherDuck successfully!")
        
        # Check available tables
        tables = conn.execute("SHOW TABLES").fetchall()
        print(f"\n📊 Available tables: {[t[0] for t in tables]}")
        
        # Try to query articles table
        try:
            # Get count of articles
            count = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
            print(f"\n📚 Total articles in database: {count}")
            
            # Query articles from last week (Aug 13-20, 2025)
            start_date = datetime(2025, 8, 13)
            end_date = datetime(2025, 8, 20)
            
            query = """
                SELECT 
                    id,
                    title,
                    domain,
                    published_date,
                    LENGTH(content) as content_length
                FROM articles 
                WHERE published_date >= ?
                AND published_date <= ?
                ORDER BY published_date DESC
                LIMIT 10
            """
            
            result = conn.execute(query, [start_date, end_date]).fetchall()
            
            print(f"\n📅 Articles from {start_date.date()} to {end_date.date()}:")
            print(f"   Found {len(result)} articles (showing first 10)")
            
            for row in result:
                article_id, title, domain, pub_date, content_len = row
                print(f"\n   ID: {article_id}")
                print(f"   Title: {title[:80]}...")
                print(f"   Domain: {domain}")
                print(f"   Date: {pub_date}")
                print(f"   Content Length: {content_len} chars")
            
            # Get date range of all articles
            date_range = conn.execute("""
                SELECT 
                    MIN(published_date) as earliest,
                    MAX(published_date) as latest
                FROM articles
            """).fetchone()
            
            print(f"\n📆 Date range of all articles:")
            print(f"   Earliest: {date_range[0]}")
            print(f"   Latest: {date_range[1]}")
            
        except Exception as e:
            print(f"❌ Error querying articles: {e}")
            
            # Try to see table schema
            try:
                schema = conn.execute("DESCRIBE articles").fetchall()
                print("\n📋 Articles table schema:")
                for col in schema:
                    print(f"   {col[0]}: {col[1]}")
            except:
                pass
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Failed to connect to MotherDuck: {e}")
        return False


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🦆 MOTHERDUCK CONNECTION TEST")
    print("="*60 + "\n")
    
    success = test_motherduck_connection()
    
    if success:
        print("\n✅ MotherDuck connection test successful!")
        print("\n📝 Next step: Run the article selector")
        print("   python run_article_selector.py --db motherduck --start-date 2025-08-13 --end-date 2025-08-20")
    else:
        print("\n❌ MotherDuck connection test failed!")
        print("   Please check your MOTHERDUCK_TOKEN in .env")