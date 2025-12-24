import pandas as pd
from typing import List, Dict, Any, Optional
from db_helper import DatabaseHelper

class DataLoader:
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize DataLoader with database connection.
        
        Args:
            db_path: Path to SQLite database (default: uses default from db_helper)
        """
        if db_path:
            self.db = DatabaseHelper(db_path)
        else:
            from db_helper import db
            self.db = db
        self._df_cache = None
    
    async def _load_from_db(self) -> pd.DataFrame:
        """Load all records from database into a DataFrame"""
        if self._df_cache is not None:
            return self._df_cache
        
        # Query all records from compensation_data table
        records = await self.db.query_compensation_data({}, limit=100000)
        
        if not records:
            # Return empty DataFrame with expected columns
            columns = [
                'S. No.', 'Adjustment', '# of RowS', 'Category Counter', 'Category',
                'Area', 'Tower', 'Tower (Short Codes)', 'Sub Tower', 'Sub Tower (Short Codes)',
                'Location', 'Roles', 'Roles (Short Codes)', 'Experience',
                'IPP - 25th', 'IPP - Median', 'IPP - 75th',
                'Global SI - 25th', 'Global SI - Median', 'Global SI - 75th',
                'Min Exp', 'Max Exp', 'Median Exp', 'Level', 'Role Descriptions'
            ]
            return pd.DataFrame(columns=columns)
        
        # Convert database records to DataFrame
        # Map database column names to CSV column names
        df_data = []
        for record in records:
            df_data.append({
                'S. No.': record.get('serial_no'),
                'Adjustment': record.get('adjustment'),
                '# of RowS': record.get('num_rows'),
                'Category Counter': record.get('category_counter'),
                'Category': record.get('category'),
                'Area': record.get('area'),
                'Tower': record.get('tower'),
                'Tower (Short Codes)': record.get('tower_short_code'),
                'Sub Tower': record.get('sub_tower'),
                'Sub Tower (Short Codes)': record.get('sub_tower_short_code'),
                'Location': record.get('location'),
                'Roles': record.get('role'),
                'Roles (Short Codes)': record.get('role_short_code'),
                'Experience': record.get('experience'),
                'IPP - 25th': record.get('ipp_25th'),
                'IPP - Median': record.get('ipp_median'),
                'IPP - 75th': record.get('ipp_75th'),
                'Global SI - 25th': record.get('global_si_25th'),
                'Global SI - Median': record.get('global_si_median'),
                'Global SI - 75th': record.get('global_si_75th'),
                'Min Exp': record.get('min_exp'),
                'Max Exp': record.get('max_exp'),
                'Median Exp': record.get('median_exp'),
                'Level': record.get('level'),
                'Role Descriptions': record.get('role_description'),
            })
        
        self._df_cache = pd.DataFrame(df_data)
        return self._df_cache
    
    async def get_all_records(self) -> List[Dict[str, Any]]:
        """Get all records as list of dictionaries from database"""
        return await self.db.query_compensation_data({}, limit=100000)
    
    async def get_dataframe(self) -> pd.DataFrame:
        """Get the dataframe (loaded from database)"""
        return await self._load_from_db()
    
    def refresh_cache(self):
        """Clear the cache to force reload from database"""
        self._df_cache = None

