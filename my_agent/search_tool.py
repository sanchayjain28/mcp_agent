from typing import List, Dict, Any, Optional
from data_loader import DataLoader
from role_mapper import RoleMapper
from thefuzz import fuzz, process
from logger import logger

class SearchTool:
    def __init__(self, data_loader: DataLoader):
        self.data_loader = data_loader
        self.role_mapper = RoleMapper()
        self.db = data_loader.db
        self._roles_cache = None
        self._locations_cache = None
    
    async def _get_all_roles(self) -> List[str]:
        """Get all unique roles from database"""
        if self._roles_cache is not None:
            logger.debug("Using cached roles list")
            return self._roles_cache
        
        logger.info("Loading roles from database")
        async with self.db.get_connection() as conn:
            cursor = await conn.cursor()
            await cursor.execute("SELECT DISTINCT role FROM compensation_data WHERE role IS NOT NULL AND role != ''")
            rows = await cursor.fetchall()
            self._roles_cache = [row[0] for row in rows]
        logger.info(f"Loaded {len(self._roles_cache)} unique roles")
        return self._roles_cache
    
    async def _get_all_locations(self) -> List[str]:
        """Get all unique locations from database"""
        if self._locations_cache is not None:
            logger.debug("Using cached locations list")
            return self._locations_cache
        
        logger.info("Loading locations from database")
        async with self.db.get_connection() as conn:
            cursor = await conn.cursor()
            await cursor.execute("SELECT DISTINCT location FROM compensation_data WHERE location IS NOT NULL AND location != ''")
            rows = await cursor.fetchall()
            self._locations_cache = [row[0] for row in rows]
        logger.info(f"Loaded {len(self._locations_cache)} unique locations")
        return self._locations_cache
    
    async def search(
        self,
        role: Optional[str] = None,
        tower: Optional[str] = None,
        sub_tower: Optional[str] = None,
        location: Optional[str] = None,
        level: Optional[str] = None,
        min_experience: Optional[int] = None,
        max_experience: Optional[int] = None,
        fuzzy_threshold: int = 80,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Search records with multiple filters and fuzzy matching using database."""
        logger.info(f"Starting search: role={role}, tower={tower}, sub_tower={sub_tower}, location={location}, level={level}, min_exp={min_experience}, max_exp={max_experience}, limit={limit}")
        
        # Build filters for database query (exact matches)
        db_filters = {}
        
        # Role search with mapping and fuzzy matching
        role_to_search = None
        if role:
            logger.debug(f"Searching for role: {role}")
            expanded_roles = self.role_mapper.expand_query(role)
            
            # Try exact match first
            all_roles = await self._get_all_roles()
            exact_matches = [r for r in expanded_roles if r in all_roles]
            
            if exact_matches:
                # Use first exact match (or could use all matches)
                role_to_search = exact_matches[0]
                logger.debug(f"Found exact role match: {role_to_search}")
            else:
                # Try fuzzy matching
                matches = process.extract(role, all_roles, limit=10, scorer=fuzz.token_sort_ratio)
                matched_roles = [match[0] for match in matches if match[1] >= fuzzy_threshold]
                if matched_roles:
                    role_to_search = matched_roles[0]
                    logger.info(f"Found fuzzy role match: '{role}' -> '{role_to_search}' (score: {matches[0][1]})")
                else:
                    logger.warning(f"No role match found for: {role}")
        
        if role_to_search:
            db_filters['role'] = role_to_search.lower()
        
        # Location search with fuzzy matching (similar to role matching)
        location_to_search = None
        if location:
            logger.debug(f"Searching for location: {location}")
            location_lower = location.lower().strip()
            all_locations = await self._get_all_locations()
            
            # Try exact match first (case-insensitive)
            exact_matches = [loc for loc in all_locations if loc.lower() == location_lower]
            
            if exact_matches:
                title_case_matches = [loc for loc in exact_matches if loc[0].isupper() and not loc.isupper()]
                location_to_search = title_case_matches[0] if title_case_matches else exact_matches[0]
                logger.debug(f"Found exact location match: {location_to_search}")
            else:
                # Try partial match (contains) - e.g., "mexico" matches "Mexico" or "MEXICO"
                partial_matches = [loc for loc in all_locations if location_lower in loc.lower() or loc.lower() in location_lower]
                
                if partial_matches:
                    # Prefer title case over all caps
                    title_case_matches = [loc for loc in partial_matches if loc[0].isupper() and not loc.isupper()]
                    location_to_search = title_case_matches[0] if title_case_matches else partial_matches[0]
                    logger.info(f"Found partial location match: '{location}' -> '{location_to_search}'")
                else:
                    # Try fuzzy matching
                    matches = process.extract(location, all_locations, limit=10, scorer=fuzz.token_sort_ratio)
                    matched_locations = [match[0] for match in matches if match[1] >= fuzzy_threshold]
                    if matched_locations:
                        # Prefer title case over all caps
                        title_case_matches = [loc for loc in matched_locations if loc[0].isupper() and not loc.isupper()]
                        location_to_search = title_case_matches[0] if title_case_matches else matched_locations[0]
                        logger.info(f"Found fuzzy location match: '{location}' -> '{location_to_search}' (score: {matches[0][1]})")
                    else:
                        logger.warning(f"No location match found for: {location}")
        
        if location_to_search:
            db_filters['location'] = location_to_search.lower()
        
        # For text fields that need partial matching, we'll filter after querying
        # But we can still use exact matches if they work
        if tower:
            # Try exact match first, but we'll also do partial matching later
            db_filters['tower'] = tower.lower()
        
        if sub_tower:
            db_filters['sub_tower'] = sub_tower.lower()
        
        if level:
            db_filters['level'] = level
        
        if min_experience is not None:
            db_filters['min_exp'] = min_experience
        
        if max_experience is not None:
            db_filters['max_exp'] = max_experience
        
        # Query database with a higher limit to allow for post-filtering
        query_limit = limit * 10 if (tower or sub_tower) else limit
        logger.debug(f"Querying database with filters: {db_filters}, limit: {query_limit}")
        results = await self.db.query_compensation_data(db_filters, limit=query_limit)
        logger.info(f"Database query returned {len(results)} records")
        
        # Post-filter for partial text matching on tower, sub_tower
        # Note: location is already handled with fuzzy matching above
        filtered_results = []
        for record in results:
            # Check tower partial match
            if tower and record.get('tower'):
                if tower.lower() not in record.get('tower', '').lower():
                    continue
            
            # Check sub_tower partial match
            if sub_tower and record.get('sub_tower'):
                if sub_tower.lower() not in record.get('sub_tower', '').lower():
                    continue
            
            filtered_results.append(record)
            if len(filtered_results) >= limit:
                break
        
        logger.info(f"Post-filtering returned {len(filtered_results)} records (limit: {limit})")
        
        # Convert to expected format (matching CSV column names)
        formatted_results = []
        for record in filtered_results:
            formatted_results.append({
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
        
        logger.info(f"Search completed, returning {len(formatted_results)} results")
        return formatted_results
    
    async def get_role_suggestions(self, partial_role: str, limit: int = 10) -> List[str]:
        """Get role name suggestions based on partial input"""
        logger.debug(f"Getting role suggestions for: {partial_role}")
        all_roles = await self._get_all_roles()
        if not all_roles:
            logger.warning("No roles found in database")
            return []
        
        matches = process.extract(partial_role, all_roles, limit=limit, scorer=fuzz.token_sort_ratio)
        suggestions = [match[0] for match in matches]
        logger.info(f"Found {len(suggestions)} role suggestions for '{partial_role}'")
        return suggestions
    
    async def get_location_suggestions(self, partial_location: str, limit: int = 10) -> List[str]:
        """Get location name suggestions based on partial input"""
        logger.debug(f"Getting location suggestions for: {partial_location}")
        all_locations = await self._get_all_locations()
        if not all_locations:
            logger.warning("No locations found in database")
            return []
        
        matches = process.extract(partial_location, all_locations, limit=limit, scorer=fuzz.token_sort_ratio)
        # Prefer title case over all caps
        suggestions = []
        for match in matches:
            loc = match[0]
            # If there's a title case version, prefer it
            title_case = loc.title() if loc.isupper() else loc
            if title_case not in suggestions:
                suggestions.append(title_case)
            elif loc not in suggestions:
                suggestions.append(loc)
        
        result = suggestions[:limit]
        logger.info(f"Found {len(result)} location suggestions for '{partial_location}'")
        return result

