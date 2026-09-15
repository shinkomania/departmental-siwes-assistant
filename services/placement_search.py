"""
Placement Search Service
------------------------
Handles placement searches across:
1. Internal Verified Database (organizations stored and verified in SQLite)
2. Live Web Research / Search API (extensible adapter for live online organization search)

This service ensures transparency: it never invents organizations and clearly
differentiates between Verified DB records, Online Sources, and Student Submissions.
"""
import os
import logging
from sqlalchemy import or_, and_
from models.organization import Organization

logger = logging.getLogger(__name__)

class PlacementSearchService:
    """Service to search and match SIWES placement organizations."""

    def __init__(self, api_key=None, provider=None):
        self.api_key = api_key or os.environ.get('SEARCH_API_KEY')
        self.provider = provider or os.environ.get('SEARCH_PROVIDER', 'none')

    def search(self, state=None, city=None, interest=None, org_type=None, keywords=None):
        """
        Executes a complete placement search combining verified database results
        and external web research (if configured).
        
        Returns a dict:
        {
            'database_results': list of Organization dicts,
            'web_results': list of Organization dicts,
            'live_search_status': {
                'configured': bool,
                'message': str,
                'provider': str
            },
            'total_count': int
        }
        """
        # 1. Search Internal Database
        db_results = self._search_database(
            state=state,
            city=city,
            interest=interest,
            org_type=org_type,
            keywords=keywords
        )

        # 2. Search Live Web Research (if configured)
        web_search_status = self._search_live_web(
            state=state,
            city=city,
            interest=interest,
            org_type=org_type,
            keywords=keywords
        )

        # Format database results with calculated relevance notes
        formatted_db_results = []
        for org in db_results:
            org_data = org.to_dict()
            # Calculate dynamic relevance explanation if not present
            if not org_data.get('why_relevant') or interest:
                org_data['why_relevant'] = self._generate_relevance_note(org, interest, state, city)
            formatted_db_results.append(org_data)

        total_count = len(formatted_db_results) + len(web_search_status.get('results', []))

        return {
            'database_results': formatted_db_results,
            'web_results': web_search_status.get('results', []),
            'live_search_status': {
                'configured': web_search_status.get('configured', False),
                'message': web_search_status.get('message', ''),
                'provider': web_search_status.get('provider', 'None')
            },
            'total_count': total_count,
            'query_params': {
                'state': state or '',
                'city': city or '',
                'interest': interest or '',
                'org_type': org_type or '',
                'keywords': keywords or ''
            }
        }

    def _search_database(self, state=None, city=None, interest=None, org_type=None, keywords=None):
        """Query active organizations from SQLite with flexible filters."""
        query = Organization.query.filter(Organization.is_active == True)

        # Filter by State (Case-insensitive match)
        if state and state.strip() and state.lower() != 'all':
            query = query.filter(Organization.state.ilike(f"%{state.strip()}%"))

        # Filter by City
        if city and city.strip():
            query = query.filter(Organization.city.ilike(f"%{city.strip()}%"))

        # Filter by Organization Type / Industry
        if org_type and org_type.strip() and org_type.lower() != 'all':
            query = query.filter(
                or_(
                    Organization.industry.ilike(f"%{org_type.strip()}%"),
                    Organization.relevance_areas.ilike(f"%{org_type.strip()}%")
                )
            )

        # Filter by Area of Interest
        if interest and interest.strip() and interest.lower() != 'all':
            query = query.filter(
                or_(
                    Organization.relevance_areas.ilike(f"%{interest.strip()}%"),
                    Organization.description.ilike(f"%{interest.strip()}%")
                )
            )

        # Additional Keyword Filter
        if keywords and keywords.strip():
            kw = f"%{keywords.strip()}%"
            query = query.filter(
                or_(
                    Organization.name.ilike(kw),
                    Organization.description.ilike(kw),
                    Organization.relevance_areas.ilike(kw),
                    Organization.industry.ilike(kw)
                )
            )

        # Order by verification priority (Verified first, then Student Submitted, etc.)
        return query.order_by(
            Organization.verification_status.asc(),
            Organization.name.asc()
        ).all()

    def _search_live_web(self, state=None, city=None, interest=None, org_type=None, keywords=None):
        """
        Extensible adapter for live web research.
        If SEARCH_API_KEY is not set or provider is 'none', returns explicit unconfigured notice.
        """
        if not self.api_key or self.provider == 'none':
            return {
                'configured': False,
                'provider': 'None',
                'message': (
                    "Live web research is not currently configured. "
                    "You can browse organization records in the DSA directory or configure a search API."
                ),
                'results': []
            }

        # Extensible plug-in point for live API search (e.g. SerpAPI, Tavily, Google Search)
        try:
            results = self._execute_provider_search(
                provider=self.provider,
                api_key=self.api_key,
                state=state,
                city=city,
                interest=interest,
                org_type=org_type,
                keywords=keywords
            )
            return {
                'configured': True,
                'provider': self.provider,
                'message': f"Live web research retrieved {len(results)} candidate results from {self.provider.capitalize()}.",
                'results': results
            }
        except Exception as e:
            logger.error(f"Live web search provider error: {e}")
            return {
                'configured': True,
                'provider': self.provider,
                'message': f"Live web research encountered a temporary provider issue: {str(e)}",
                'results': []
            }

    def _execute_provider_search(self, provider, api_key, state, city, interest, org_type, keywords):
        """
        Provider integration placeholder.
        Real HTTP queries can be executed here when an API key is provided.
        """
        # Example structured query formulation for future integration:
        # search_query = f"tech companies SIWES industrial training in {city or ''} {state or 'Nigeria'} {interest or ''}"
        return []

    def _generate_relevance_note(self, org, interest=None, state=None, city=None):
        """Generates clear, factual context for why this organization is relevant to the student."""
        relevance_parts = []
        if interest and interest.lower() in org.relevance_areas.lower():
            relevance_parts.append(f"Actively works in your field of interest ({interest})")
        
        if state and state.lower() in org.state.lower():
            relevance_parts.append(f"Located in your preferred state ({org.state})")
            
        if relevance_parts:
            return " â€¢ ".join(relevance_parts) + f". Specializes in {org.industry}."
        
        return f"Engages in {org.relevance_areas} in {org.city}, {org.state}."
