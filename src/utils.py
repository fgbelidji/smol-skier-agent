
import re
import json
import googlemaps
import os
from math import radians, sin, cos, sqrt, atan2
import numpy as np
from typing import Tuple, Dict, List
from openai import OpenAI

def geocode_location(query: str) -> Tuple[float, float]:
    """
    Geocode a location query into latitude and longitude.

    Args:
        query (str): Location query string.

    Returns:
        Tuple[float, float]: Latitude and longitude of the location.
    """
    gmaps = googlemaps.Client(key=os.getenv('GOOGLE_MAPS_API_KEY'))
    geocode_result = gmaps.places(query)
    try:
        location = geocode_result['results'][0]['geometry']['location']
        return location['lat'], location['lng']
    except:
        return None

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance in kilometers between two points on Earth.

    Args:
        lat1 (float): Latitude of the first point.
        lon1 (float): Longitude of the first point.
        lat2 (float): Latitude of the second point.
        lon2 (float): Longitude of the second point.

    Returns:
        float: Distance in kilometers.
    """
    R = 6371
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

def assign_location_to_clusters(location: Tuple[float, float], clusters: Dict[str, List[Tuple[float, float]]], k: int = 3) -> List[Tuple[str, float]]:
    """
    Assign a location to the closest clusters of mountain ranges based on proximity.

    Args:
        location (Tuple[float, float]): Latitude and longitude of the location.
        clusters (Dict[str, List[Tuple[float, float]]]): Clusters of mountain ranges.
        k (int): Number of closest clusters to return.

    Returns:
        List[Tuple[str, float]]: Closest clusters and their distances.
    """
    closest_summits = []
    for range_label, points in clusters.items():
        min_distance = float('inf')
        for lat, lon in points:
            dist = haversine(location[0], location[1], lat, lon)
            if dist < min_distance:
                min_distance = dist
        closest_summits.append((range_label, min_distance))
    closest_summits.sort(key=lambda x: x[1])
    return closest_summits[:k]

def build_clustered_mountain_ranges(peaks):
    """
    Group peaks into clusters based on their mountain range labels.
    :param peaks: list of dicts [{'name': str, 'lat': float, 'lon': float, 'range': str}]
    :return: dict of clusters {range_label: [(lat, lon)]}
    """
    clusters = {}
    for peak in peaks:
        range_label = peak['range']
        if range_label not in clusters:
            clusters[range_label] = []
        clusters[range_label].append((peak['lat'], peak['lon']))
    return clusters



def parse_topo_blob(output: str):
    """
    Checks if there is any dictionary-like structure in the output string.

    Args:
        output (str): The output string potentially containing a dictionary.

    Returns:
        dict or None: Parsed dictionary if found, otherwise None.
    """
    # Define a regex pattern to match any dictionary-like structure
    pattern = r"\{\s*(?:\"[^\"]+\":\s*(?:\".*?\"|\d+|true|false|null),?\s*)+\}"  # Matches any JSON-like dict

    # Search for the pattern in the output
    match = re.search(pattern, output, re.DOTALL)
    if match:
        blob = match.group()
        try:
            # Parse the JSON-like dict
            return json.loads(blob)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            return None

    return None

def llm_summarizer(text, llm_engine):
    
   
    messages=[
           {
            "role": "system",
            "content": "You're an expert at summarizing data on weather forecast and avalanche conditions. Summarize the data that's been provided to you below"
        }, 
        {
            "role": "user",
            "content": text,
        }
    ]
    
    summary = llm_engine(messages)
    return summary["content"]
    
    
    
    
    