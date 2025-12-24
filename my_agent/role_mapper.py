from typing import Dict, List
from thefuzz import fuzz, process

class RoleMapper:
    def __init__(self):
        # Common role mappings (aliases to canonical names)
        self.role_mappings = {
            'sde2': ['Sr. Software Developer', 'Senior Software Developer', 'SSD'],
            'sde1': ['Software Developer', 'SD'],
            'sde3': ['Tech Lead', 'THL', 'Technical Lead'],
            'senior sd': ['Sr. Software Developer', 'Senior Software Developer'],
            'senior software developer': ['Sr. Software Developer'],
            'tech lead': ['Tech Lead', 'THL'],
            'project manager': ['Project Manager', 'ProjMan'],
            'business analyst': ['Business Analyst', 'BA'],
            'sr ba': ['Sr. Business Analyst', 'SBA', 'Senior Business Analyst'],
            'lead ba': ['Lead Business Analyst', 'LBA'],
            'dba': ['DBA'],
            'sr dba': ['Sr. DBA', 'SDBA', 'Senior DBA'],
            'devops': ['DevOps Consultant', 'DOC'],
            'sr devops': ['Sr DevOps Consultant', 'SDOC'],
            'scrum master': ['Scrum Master', 'ScM'],
            'architect': ['Application Architect', 'AA'],
            'sr architect': ['Sr. Application Architect', 'SAA'],
            'lead architect': ['Lead Architect', 'LA'],
        }
    
    def map_role(self, query: str) -> List[str]:
        """Map a role query to possible canonical role names."""
        query_lower = query.lower().strip()
        
        # Direct mapping lookup
        if query_lower in self.role_mappings:
            return self.role_mappings[query_lower]
        
        # Fuzzy match against known aliases
        aliases = list(self.role_mappings.keys())
        matches = process.extract(query_lower, aliases, limit=3, scorer=fuzz.token_sort_ratio)
        
        # If good match found, return mapped roles
        if matches and matches[0][1] >= 80:
            return self.role_mappings[matches[0][0]]
        
        # Return original query if no mapping found
        return [query]
    
    def expand_query(self, query: str) -> List[str]:
        """Expand a query to include all possible variations"""
        mapped = self.map_role(query)
        return list(set(mapped + [query]))

