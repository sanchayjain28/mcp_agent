import aiosqlite
import os
import asyncio
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any
from datetime import datetime
from logger import logger


class DatabaseHelper:
    """SQLite database helper for managing file-based database operations."""
    
    def __init__(self, db_path: str = "agent.db"):
        """
        Initialize the database helper.
        
        Args:
            db_path: Path to the SQLite database file (default: "agent.db")
        """
        self.db_path = db_path
        self._ensure_db_directory()
        self._initialized = False
        self._init_lock = asyncio.Lock()
    
    def _ensure_db_directory(self):
        """Ensure the directory for the database file exists."""
        db_dir = os.path.dirname(os.path.abspath(self.db_path))
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
    
    @asynccontextmanager
    async def get_connection(self):
        """
        Async context manager for database connections.
        
        Usage:
            async with db.get_connection() as conn:
                cursor = await conn.cursor()
                await cursor.execute(...)
        """
        # Ensure database is initialized
        if not self._initialized:
            async with self._init_lock:
                if not self._initialized:
                    await self._initialize_database()
                    self._initialized = True
        
        conn = await aiosqlite.connect(self.db_path)
        conn.row_factory = aiosqlite.Row  # Enable column access by name
        try:
            yield conn
            await conn.commit()
        except Exception as e:
            await conn.rollback()
            logger.error(f"Database error: {str(e)}")
            raise
        finally:
            await conn.close()
    
    async def _initialize_database(self):
        """Initialize database tables if they don't exist."""
        # Create connection directly to avoid circular dependency
        conn = await aiosqlite.connect(self.db_path)
        conn.row_factory = aiosqlite.Row
        try:
            cursor = await conn.cursor()
            
            # Create conversations table
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    query TEXT NOT NULL,
                    response TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create compensation_data table (for salary/compensation data from CSV)
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS compensation_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    combined_field TEXT,
                    serial_no INTEGER,
                    adjustment TEXT,
                    num_rows INTEGER,
                    category_counter INTEGER,
                    category TEXT,
                    area TEXT,
                    tower TEXT,
                    tower_short_code TEXT,
                    sub_tower TEXT,
                    sub_tower_short_code TEXT,
                    location TEXT,
                    role TEXT,
                    role_short_code TEXT,
                    experience TEXT,
                    ipp_25th TEXT,
                    ipp_median TEXT,
                    ipp_75th TEXT,
                    global_si_25th TEXT,
                    global_si_median TEXT,
                    global_si_75th TEXT,
                    min_exp INTEGER,
                    max_exp INTEGER,
                    median_exp INTEGER,
                    level TEXT,
                    role_description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create logs table for storing application logs
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    module TEXT,
                    function TEXT,
                    line INTEGER,
                    exception TEXT,
                    extra_data TEXT
                )
            """)
            
            # Create query_cache table
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS query_cache (
                    query_hash TEXT PRIMARY KEY,
                    query_text TEXT NOT NULL,
                    result TEXT NOT NULL,
                    expires_at TIMESTAMP
                )
            """)
            
            # Create index on timestamp and level for faster queries
            await cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp)
            """)
            await cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_logs_level ON logs(level)
            """)
            
            await conn.commit()
            logger.info(f"Database initialized at {self.db_path}")
        finally:
            await conn.close()
    
    async def insert_conversation(self, user_id: str, query: str, response: Optional[str] = None) -> int:
        """
        Insert a new conversation record.
        
        Args:
            user_id: User identifier
            query: User query text
            response: Response text (optional)
            
        Returns:
            ID of the inserted record
        """
        async with self.get_connection() as conn:
            cursor = await conn.cursor()
            await cursor.execute("""
                INSERT INTO conversations (user_id, query, response)
                VALUES (?, ?, ?)
            """, (user_id, query, response))
            return cursor.lastrowid
    
    async def get_conversations(self, user_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get conversation records.
        
        Args:
            user_id: Filter by user_id (optional)
            limit: Maximum number of records to return
            
        Returns:
            List of conversation dictionaries
        """
        async with self.get_connection() as conn:
            cursor = await conn.cursor()
            if user_id:
                await cursor.execute("""
                    SELECT * FROM conversations 
                    WHERE user_id = ? 
                    ORDER BY created_at DESC 
                    LIMIT ?
                """, (user_id, limit))
            else:
                await cursor.execute("""
                    SELECT * FROM conversations 
                    ORDER BY created_at DESC 
                    LIMIT ?
                """, (limit,))
            
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
            
    async def cache_query_result(self, query_hash: str, query_text: str, result: str, 
                          expires_in_hours: int = 24) -> None:
        """
        Cache a query result.
        
        Args:
            query_hash: Hash of the query
            query_text: Original query text
            result: Cached result (JSON string)
            expires_in_hours: Hours until expiration
        """
        from datetime import timedelta
        expires_at = datetime.now() + timedelta(hours=expires_in_hours)
        
        async with self.get_connection() as conn:
            cursor = await conn.cursor()
            await cursor.execute("""
                INSERT OR REPLACE INTO query_cache (query_hash, query_text, result, expires_at)
                VALUES (?, ?, ?, ?)
            """, (query_hash, query_text, result, expires_at))
    
    async def get_cached_result(self, query_hash: str) -> Optional[str]:
        """
        Get a cached query result if it exists and hasn't expired.
        
        Args:
            query_hash: Hash of the query
            
        Returns:
            Cached result or None if not found/expired
        """
        async with self.get_connection() as conn:
            cursor = await conn.cursor()
            await cursor.execute("""
                SELECT result FROM query_cache 
                WHERE query_hash = ? AND (expires_at IS NULL OR expires_at > ?)
            """, (query_hash, datetime.now()))
            
            row = await cursor.fetchone()
            return row['result'] if row else None
    
    async def clear_expired_cache(self) -> int:
        """
        Clear expired cache entries.
        
        Returns:
            Number of deleted entries
        """
        async with self.get_connection() as conn:
            cursor = await conn.cursor()
            await cursor.execute("""
                DELETE FROM query_cache 
                WHERE expires_at IS NOT NULL AND expires_at < ?
            """, (datetime.now(),))
            return cursor.rowcount
    
    async def execute_raw_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """
        Execute a raw SQL query (use with caution).
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            List of result dictionaries
        """
        async with self.get_connection() as conn:
            cursor = await conn.cursor()
            await cursor.execute(query, params)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def insert_compensation_record(self, record: Dict[str, Any]) -> int:
        """
        Insert a compensation/salary record.
        
        Args:
            record: Dictionary containing compensation data fields
            
        Returns:
            ID of the inserted record
        """
        async with self.get_connection() as conn:
            cursor = await conn.cursor()
            await cursor.execute("""
                INSERT INTO compensation_data (
                    combined_field, serial_no, adjustment, num_rows, category_counter,
                    category, area, tower, tower_short_code, sub_tower,
                    sub_tower_short_code, location, role, role_short_code, experience,
                    ipp_25th, ipp_median, ipp_75th, global_si_25th, global_si_median,
                    global_si_75th, min_exp, max_exp, median_exp, level, role_description
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get('combined_field'),
                record.get('serial_no'),
                record.get('adjustment'),
                record.get('num_rows'),
                record.get('category_counter'),
                record.get('category'),
                record.get('area'),
                record.get('tower'),
                record.get('tower_short_code'),
                record.get('sub_tower'),
                record.get('sub_tower_short_code'),
                record.get('location'),
                record.get('role'),
                record.get('role_short_code'),
                record.get('experience'),
                record.get('ipp_25th'),
                record.get('ipp_median'),
                record.get('ipp_75th'),
                record.get('global_si_25th'),
                record.get('global_si_median'),
                record.get('global_si_75th'),
                record.get('min_exp'),
                record.get('max_exp'),
                record.get('median_exp'),
                record.get('level'),
                record.get('role_description')
            ))
            return cursor.lastrowid
    
    async def query_compensation_data(
        self,
        filters: Dict[str, Any],
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Query compensation data with filters.
        
        Args:
            filters: Dictionary of filters
            limit: Maximum number of records to return
            
        Returns:
            List of matching compensation records
        """
        async with self.get_connection() as conn:
            cursor = await conn.cursor()
            
            where_clauses = []
            params = []
            
            if filters.get('role') is not None:
                where_clauses.append("role = ?")
                params.append(filters.get('role'))
            
            if filters.get('tower') is not None:
                where_clauses.append("tower = ?")
                params.append(filters.get('tower'))
            
            if filters.get('sub_tower') is not None:
                where_clauses.append("sub_tower = ?")
                params.append(filters.get('sub_tower'))
            
            if filters.get('location') is not None:
                where_clauses.append("location = ?")
                params.append(filters.get('location'))
            
            if filters.get('category') is not None:
                where_clauses.append("category = ?")
                params.append(filters.get('category'))
            
            if filters.get('level') is not None:
                where_clauses.append("level = ?")
                params.append(filters.get('level'))
            
            if filters.get('area') is not None:
                where_clauses.append("area = ?")
                params.append(filters.get('area'))
            
            if filters.get('role_short_code') is not None:
                where_clauses.append("role_short_code = ?")
                params.append(filters.get('role_short_code'))
            
            if filters.get('min_exp') is not None:
                where_clauses.append("min_exp >= ?")
                params.append(filters.get('min_exp'))
            
            if filters.get('max_exp') is not None:
                where_clauses.append("max_exp <= ?")
                params.append(filters.get('max_exp'))
            
            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
            params.append(limit)
            
            query = f"""
                SELECT * FROM compensation_data 
                WHERE {where_sql}
                ORDER BY serial_no
                LIMIT ?
            """
            logger.debug(f"Executing query: {query} with params: {params}")
            await cursor.execute(query, params)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Get information about a table's schema.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of column information dictionaries
        """
        async with self.get_connection() as conn:
            cursor = await conn.cursor()
            await cursor.execute(f"PRAGMA table_info({table_name})")
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

# Create a default database instance
db = DatabaseHelper()

