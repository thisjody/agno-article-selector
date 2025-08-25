#!/usr/bin/env python3
"""Find the articles source table in MotherDuck."""

import os
from dotenv import load_dotenv
import duckdb

load_dotenv()

def find_articles_table():
    """Find where articles are stored."""
    
    token = os.getenv("MOTHERDUCK_TOKEN")
    database = "newsletter-data"
    
    print(f"🔄 Connecting to MotherDuck database: {database}")
    
    try:
        # Connect directly to the database
        conn = duckdb.connect(f"md:{database}?motherduck_token={token}")
        print("✅ Connected!")
        
        # List all tables
        tables = conn.execute("SHOW TABLES").fetchall()
        print(f"\n📊 Tables in {database}:")
        for table in tables:
            table_name = table[0]
            print(f"\n  📁 {table_name}")
            
            # Get table info
            try:
                # Row count
                count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                print(f"     Rows: {count}")
                
                # Schema (first 8 columns)
                schema = conn.execute(f"DESCRIBE {table_name}").fetchall()
                cols = [col[0] for col in schema[:8]]
                print(f"     Columns: {', '.join(cols)}")
                
                # Check if it looks like an articles table
                col_names = [col[0].lower() for col in schema]
                if any(word in ' '.join(col_names) for word in ['article', 'title', 'content', 'url', 'domain']):
                    print(f"     ⭐ This looks like an articles table!")
                    
                    # Show a sample
                    sample = conn.execute(f"SELECT * FROM {table_name} LIMIT 1").fetchone()
                    if sample:
                        print(f"     Sample record:")
                        for i, col in enumerate(schema[:5]):
                            if i < len(sample):
                                print(f"       {col[0]}: {str(sample[i])[:80]}")
                
            except Exception as e:
                print(f"     Error: {e}")
        
        # Try common table names
        print("\n🔍 Checking for common article table names...")
        common_names = ['articles', 'article', 'news', 'feed', 'items', 'posts', 
                       'raw_articles', 'source_articles', 'newsletter_articles',
                       'scraped_articles', 'article_feed', 'news_articles']
        
        for name in common_names:
            try:
                count = conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
                print(f"   ✅ Found table '{name}' with {count} rows!")
                
                # Show schema
                schema = conn.execute(f"DESCRIBE {name}").fetchall()
                print(f"      Columns: {', '.join([col[0] for col in schema[:8]])}")
                
            except:
                # Table doesn't exist
                pass
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        
        # Try to parse the error for hints
        if "does not exist" in str(e):
            print("\n💡 Hint: The articles might be in a different database or need to be imported")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🦆 MOTHERDUCK ARTICLES TABLE SEARCH")
    print("="*60 + "\n")
    
    find_articles_table()
    
    print("\n📝 Note: The ADK version might be using a different database")
    print("   or creating/importing articles on the fly.")
    print("\n   The newsletter_selections table contains already processed articles.")
    print("   We may need to:")
    print("   1. Import raw articles from a CSV/source")
    print("   2. Use the newsletter_selections as input")
    print("   3. Connect to a different MotherDuck database")