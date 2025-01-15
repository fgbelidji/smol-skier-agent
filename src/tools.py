import os
import pandas as pd
from smolagents import Tool
from typing import List, Dict, Any, Union, Tuple
from meteofrance_api import MeteoFranceClient
from src.skitour_api import get_topos, get_refuges, get_details_topo, get_massifs, get_recent_outings
from src.meteo_france_api import get_massif_conditions
from src.utils import geocode_location, assign_location_to_clusters, haversine, llm_summarizer



class RefugeTool(Tool):
    name = "refuge_recherche"
    description = "Recherche d'un refuge dans un massif donné"

    inputs = {
        "massif_id": {
            "description": "[Optional, default: None] Id du massif souhaité ",
            "type": "string",
        }
    }
    output_type = "string"

    def forward(self, massif_id) -> List[Dict]:
        return get_refuges(massif_id)
    
    
class GetRoutesTool(Tool):
    name = "list_routes"
    description = """
    Looking for a list of ski touring routes in a given list of mountain ranges.
    Returns a list containing the information of the topos found.
    Use `topo_details` immediately after this tool to get the details of a specific topo. 
    """

    inputs = {
        "mountain_range_ids": {
            "description": "List of mountain range ids",
            "type": "string",
        }
    }
    output_type = "any"

    def forward(self, mountain_range_ids: str) -> List[Dict]:

        topos = get_topos(mountain_range_ids)
        
        return topos
        
class DescribeRouteTool(Tool):
    name = "describe_route"
    description = """ 
    Searches for key information about a specific ski touring route, including weather forecasts and associated avalanche risks. 
    Always use this tool after using the `list_routes` tool.
    This tool returns a dictionary containing the route's information, the avalanche risk estimation bulletin, and the weather forecast for the coming days of the route.
    """
    inputs = {
        "id_route": {
            "description": "id of the route",
            "type": "string",
        },
        "id_range": {
            "description": "mountain range id of the route",
            "type": "string"}
    }
    output_type = "any"
    
    def __init__(self, skitour2meteofrance: dict, llm_engine: Any):
        super().__init__()
        self.massifs_infos = skitour2meteofrance
        self.weather_client =  MeteoFranceClient(access_token=os.getenv("METEO_FRANCE_API_KEY"))   
        self.llm_engine = llm_engine

    def forward(self, id_route: str, id_range: str) -> dict:

        topo_info = get_details_topo(str(id_route))
        avalanche_conditions = get_massif_conditions(
            self.massifs_infos[str(id_range)]['meteofrance_id']
            )
        lat, lon = topo_info["depart"]["latlon"]
        weather_forecast = self.weather_client.get_forecast(float(lat), float(lon))
        daily_forecast = weather_forecast.forecast[:24]

        for day_forecast in daily_forecast:
            day_forecast["dt"] = weather_forecast.timestamp_to_locale_time(day_forecast["dt"]).isoformat()
        forecast_summary = llm_summarizer(str(daily_forecast), self.llm_engine)
        avalanche_summary = llm_summarizer(str(avalanche_conditions), self.llm_engine)
        return {
            "route_info": topo_info, 
            "avalanche_conditions": avalanche_summary,
            "daily_weather_forecast": forecast_summary,
            "route_link": f"https://skitour.fr/topos/{id_route}"
            }   
    
class RecentOutingsTool(Tool):
    name = "recent_outings"
    description = """ 
    Searches for recent outings in a given mountain range.
    Returns a list of the most recent outings in the given range.
    """
    inputs = {
        "id_range": {
            "description": "id of the mountain range",
            "type": "string",
        }
    }
    output_type = "any"
    
    def forward(self, id_range: str) -> List[Dict]:
        return get_recent_outings(id_range)
    
class MountainRangesTool(Tool):
    name = "list_mountain_ranges"
    description = """ Searches for the ID(s) of the mountain ranges closest to a given location.
    If the location is too far from known ranges, the search returns None.
    Should return a string with the massif IDs separated by commas.
    """

    inputs = {
        "location": {
            "description": "Location to search for",
            "type": "string",
        },
        
        "num_ranges": {
            "description": "[Optional, default: 3] Number of closest mountain ranges to return",
            "type": "number",   
        }
    }
    output_type = "string"
    
    def __init__(self, clusters: Dict[str, List[Tuple[float, float]]]):
        super().__init__()
        self.clusters = clusters

    def forward(self, location: str, num_ranges: int) -> Union[str, None]:

        coord_location = geocode_location(location)
        if not location:
            return None
        
        matched_ranges = assign_location_to_clusters(coord_location, self.clusters, k=num_ranges)

        
        list_ranges = [range[0] for range in matched_ranges if range[1] < 100]
        if not list_ranges:
            return ''
      
        massifs= get_massifs()
       
        massif_ids = [_massif['id'] for _massif in massifs if _massif['nom'] in list_ranges]
        return ", ".join(massif_ids)
    
class ForecastTool(Tool):
    name = "forecast"
    description = """Searches for the weather forecast for a given location as well as the current avalanche risk estimation bulletin.  
    Unnecessary if the user is inquiring about a route, as `describe_route` already provides this information."""
    
    inputs = {
        "location": {
            "description": "Location to search for",
            "type": "string",
        },
    }
    
    output_type = "any"

    def __init__(self, llm_engine, clusters: Dict[str, List[Tuple[float, float]]], skitour2meteofrance: dict):
        super().__init__()
        self.clusters = clusters
        self.massifs_infos = skitour2meteofrance
        self.llm_engine = llm_engine
        
    def forward(self, location: str) -> Union[Dict[str, Any], None]:

        coord_location = geocode_location(location)
        if not location:
            return None
        
        # Get the closest mountain range to the location to get the avalanche conditions
        matched_ranges = assign_location_to_clusters(coord_location, self.clusters, k=1)
        
        list_ranges = [range[0] for range in matched_ranges if range[1] < 100]
        if not list_ranges:
            return None
      
        massifs= get_massifs()
       
        massif_id = [_massif['id'] for _massif in massifs if _massif['nom'] in list_ranges]
        
        avalanche_conditions = get_massif_conditions(
            self.massifs_infos[str(massif_id[0])]['meteofrance_id']
            )
        
        weather_client =  MeteoFranceClient(access_token=os.getenv("METEO_FRANCE_API_KEY"))
        forecast = weather_client.get_forecast(*coord_location)
        daily_forecast = forecast.forecast[:24]
        
        for day_forecast in daily_forecast:
            day_forecast["dt"] = forecast.timestamp_to_locale_time(day_forecast["dt"]).isoformat()
        
        forecast_summary = llm_summarizer(str(daily_forecast), self.llm_engine)
        avalanche_summary = llm_summarizer(str(avalanche_conditions), self.llm_engine)
            
    
        return {"forecast": forecast_summary, "avalanche_conditions": avalanche_summary}