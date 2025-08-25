"""Database connection and management for DuckDB/MotherDuck."""

import os
import duckdb
from typing import Optional, List, Dict, Any
from pathlib import Path
import pandas as pd
from datetime import datetime


class ArticleDatabase:
    """Manages article storage in DuckDB/MotherDuck."""
    
    def __init__(
        self,
        local_db_path: Optional[str] = None,
        motherduck_token: Optional[str] = None,
        motherduck_database: Optional[str] = None,
        use_motherduck: bool = False,
    ):
        """Initialize database connection.
        
        Args:
            local_db_path: Path to local DuckDB file
            motherduck_token: MotherDuck authentication token
            motherduck_database: MotherDuck database name
            use_motherduck: Whether to use MotherDuck (cloud) or local DuckDB
        """
        self.use_motherduck = use_motherduck
        
        if use_motherduck and motherduck_token:
            # Connect to MotherDuck
            self.conn = duckdb.connect(f"md:{motherduck_database}?motherduck_token={motherduck_token}")
            print(f"Connected to MotherDuck database: {motherduck_database}")
        else:
            # Use local DuckDB
            db_path = local_db_path or os.getenv("CANDIDATE_EMBED_DB_PATH", "data/test_articles.duckdb")
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            self.conn = duckdb.connect(db_path)
            print(f"Connected to local DuckDB: {db_path}")
        
        # Initialize tables
        self._init_tables()
    
    def _init_tables(self):
        """Initialize database tables if they don't exist."""
        
        # Articles table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY,
                title VARCHAR,
                url VARCHAR,
                domain VARCHAR,
                content TEXT,
                published_date TIMESTAMP,
                author VARCHAR,
                tags VARCHAR[],
                metadata JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # First pass results table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS first_pass_results (
                id INTEGER PRIMARY KEY,
                article_id INTEGER,
                status VARCHAR,
                reasoning TEXT,
                confidence DOUBLE,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (article_id) REFERENCES articles(id)
            )
        """)
        
        # Scoring results table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS scoring_results (
                id INTEGER PRIMARY KEY,
                article_id INTEGER,
                relevance_score DOUBLE,
                quality_score DOUBLE,
                impact_score DOUBLE,
                overall_score DOUBLE,
                reasoning TEXT,
                recommendation VARCHAR,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (article_id) REFERENCES articles(id)
            )
        """)
        
        # Selected articles table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS selected_articles (
                id INTEGER PRIMARY KEY,
                article_id INTEGER,
                rank INTEGER,
                selection_reasoning TEXT,
                batch_id VARCHAR,
                selected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (article_id) REFERENCES articles(id)
            )
        """)
    
    def load_articles_from_csv(self, csv_path: str) -> int:
        """Load articles from CSV file.
        
        Args:
            csv_path: Path to CSV file
            
        Returns:
            Number of articles loaded
        """
        df = pd.read_csv(csv_path)
        
        # Map CSV columns to database columns
        column_mapping = {
            'ID': 'id',
            'Title': 'title',
            'URL': 'url',
            'Domain': 'domain',
            'Content': 'content',
        }
        
        df = df.rename(columns=column_mapping)
        
        # Add missing columns with default values
        if 'published_date' not in df.columns:
            df['published_date'] = datetime.now()
        if 'author' not in df.columns:
            df['author'] = None
        if 'tags' not in df.columns:
            df['tags'] = None
        if 'metadata' not in df.columns:
            df['metadata'] = None
        if 'created_at' not in df.columns:
            df['created_at'] = datetime.now()
        
        # Select only the columns we need in the correct order
        columns_order = ['id', 'title', 'url', 'domain', 'content', 
                        'published_date', 'author', 'tags', 'metadata', 'created_at']
        df = df[columns_order]
        
        # Insert into database
        self.conn.execute("INSERT OR REPLACE INTO articles SELECT * FROM df")
        
        count = len(df)
        print(f"Loaded {count} articles from {csv_path}")
        return count
    
    def get_unprocessed_articles(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get articles that haven't been processed yet.
        
        Args:
            limit: Maximum number of articles to return
            
        Returns:
            List of article dictionaries
        """
        result = self.conn.execute("""
            SELECT a.* 
            FROM articles a
            LEFT JOIN first_pass_results fp ON a.id = fp.article_id
            WHERE fp.id IS NULL
            LIMIT ?
        """, [limit]).fetchall()
        
        columns = ['id', 'title', 'url', 'domain', 'content', 'published_date', 
                   'author', 'tags', 'metadata', 'created_at']
        
        return [dict(zip(columns, row)) for row in result]
    
    def save_first_pass_result(
        self,
        article_id: int,
        status: str,
        reasoning: str,
        confidence: Optional[float] = None
    ):
        """Save first pass filtering result.
        
        Args:
            article_id: ID of the article
            status: Relevant or Irrelevant
            reasoning: Explanation for the decision
            confidence: Optional confidence score
        """
        self.conn.execute("""
            INSERT INTO first_pass_results (article_id, status, reasoning, confidence)
            VALUES (?, ?, ?, ?)
        """, [article_id, status, reasoning, confidence])
    
    def save_scoring_result(
        self,
        article_id: int,
        relevance_score: float,
        quality_score: float,
        impact_score: float,
        overall_score: float,
        reasoning: str,
        recommendation: str
    ):
        """Save scoring result.
        
        Args:
            article_id: ID of the article
            relevance_score: Relevance score (0-10)
            quality_score: Quality score (0-10)
            impact_score: Impact score (0-10)
            overall_score: Overall score (0-10)
            reasoning: Detailed explanation
            recommendation: Include/Exclude recommendation
        """
        self.conn.execute("""
            INSERT INTO scoring_results 
            (article_id, relevance_score, quality_score, impact_score, 
             overall_score, reasoning, recommendation)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [article_id, relevance_score, quality_score, impact_score,
              overall_score, reasoning, recommendation])
    
    def save_selected_articles(
        self,
        selections: List[Dict[str, Any]],
        batch_id: Optional[str] = None
    ):
        """Save selected articles.
        
        Args:
            selections: List of selected articles with rankings
            batch_id: Optional batch identifier
        """
        if not batch_id:
            batch_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for selection in selections:
            self.conn.execute("""
                INSERT INTO selected_articles (article_id, rank, selection_reasoning, batch_id)
                VALUES (?, ?, ?, ?)
            """, [selection['article_id'], selection['rank'], 
                  selection.get('reasoning', ''), batch_id])
    
    def get_relevant_articles(self) -> List[Dict[str, Any]]:
        """Get all articles marked as relevant in first pass.
        
        Returns:
            List of relevant articles with their scores
        """
        result = self.conn.execute("""
            SELECT a.*, fp.reasoning as first_pass_reasoning, sr.*
            FROM articles a
            JOIN first_pass_results fp ON a.id = fp.article_id
            LEFT JOIN scoring_results sr ON a.id = sr.article_id
            WHERE fp.status = 'Relevant'
            ORDER BY sr.overall_score DESC NULLS LAST
        """).fetchall()
        
        # Get column names
        columns = [desc[0] for desc in self.conn.description]
        
        return [dict(zip(columns, row)) for row in result]
    
    def export_results_to_json(self, output_path: str):
        """Export selected articles to JSON file.
        
        Args:
            output_path: Path for output JSON file
        """
        result = self.conn.execute("""
            SELECT a.*, sa.rank, sa.selection_reasoning, sa.batch_id,
                   sr.overall_score, sr.reasoning as score_reasoning
            FROM selected_articles sa
            JOIN articles a ON sa.article_id = a.id
            LEFT JOIN scoring_results sr ON a.id = sr.article_id
            ORDER BY sa.batch_id DESC, sa.rank
        """).df()
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        result.to_json(output_path, orient='records', indent=2)
        print(f"Exported results to {output_path}")
    
    def close(self):
        """Close database connection."""
        self.conn.close()


def get_database() -> ArticleDatabase:
    """Get database instance from environment configuration.
    
    Returns:
        ArticleDatabase instance
    """
    use_motherduck = os.getenv("MOTHERDUCK_TOKEN") is not None
    
    return ArticleDatabase(
        local_db_path=os.getenv("CANDIDATE_EMBED_DB_PATH"),
        motherduck_token=os.getenv("MOTHERDUCK_TOKEN"),
        motherduck_database=os.getenv("MOTHERDUCK_DATABASE"),
        use_motherduck=use_motherduck
    )