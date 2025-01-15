import requests
import json
import os
import datetime
from typing import List, Dict

SKITOUR_API_URL = 'https://skitour.fr/api/'

def get_massifs() -> List[Dict]:
    """
    Fetch the list of massifs from the Skitour API.

    Returns:
        List[Dict]: List of massifs with their details.
    """
    url = SKITOUR_API_URL + 'massifs'
    headers = {'cle': os.getenv('SKITOUR_API_TOKEN')}
    response = requests.get(url, headers=headers, timeout=10)
    return response.json()

def get_topos(ids_massif: str) -> List[Dict]:
    """
    Fetch ski touring itineraries for a given massif.

    Args:
        ids_massif (str): ID of the massif.

    Returns:
        List[Dict]: List of itineraries for the specified massif.
    """
    url = SKITOUR_API_URL + 'topos'
    headers = {'cle': os.getenv('SKITOUR_API_TOKEN')}
    params = {'m': ids_massif}
    response = requests.get(url, headers=headers, params=params, timeout=10) 
    return json.loads(response.text.replace('\\\\', '\\'))

def get_sommets(massif_id: str) -> List[Dict]:
    """
    Fetch the list of summits for a given massif.

    Args:
        massif_id (str): ID of the massif.

    Returns:
        List[Dict]: List of summits with their details.
    """
    url = SKITOUR_API_URL + 'sommets'
    headers = {'cle': os.getenv('SKITOUR_API_TOKEN')}
    params = {'m': massif_id}
    response = requests.get(url, headers=headers, params=params)
    response = response.json()
    sommets = []
    for _sommets in response:
        sommets.append({
            "name": _sommets['sommet'],
            "lat": float(_sommets['latlon'][0]),
            "lon": float(_sommets['latlon'][1]),
            "range": _sommets['massif']['nom']
        })
    return sommets

def get_refuges(massif_ids: str) -> List[Dict]:
    """
    Fetch the list of refuges for a given massif.

    Args:
        massif_ids (str): ID(s) of the massif(s).

    Returns:
        List[Dict]: List of refuges.
    """
    url = SKITOUR_API_URL + 'refuges'
    headers = {'cle': os.getenv('SKITOUR_API_TOKEN')}
    params = {'m': massif_ids}
    response = requests.get(url, headers=headers, params=params, timeout=10)
    return response.json()

def get_details_topo(id_topo):
    url = SKITOUR_API_URL + f'topo/{id_topo}'
    headers = {'cle': os.getenv('SKITOUR_API_TOKEN')}
    response = requests.get(url, headers=headers)
    return response.json()

def get_conditions(massif_ids: str) -> List[Dict]:
    """
    Fetch the list of refuges for a given massif.

    Args:
        massif_ids (str): ID(s) of the massif(s).

    Returns:
        List[Dict]: List of refuges.
    """
    url = SKITOUR_API_URL + 'refuges'
    headers = {'cle': os.getenv('SKITOUR_API_TOKEN')}
    params = {'m': massif_ids}
    response = requests.get(url, headers=headers, params=params, timeout=10)
    return response.json()

def get_outing(id_outing: str) -> Dict:
    """
    Fetch the details of a specific outing.

    Args:
        id_outing (str): ID of the outing.

    Returns:
        Dict: Details of the outing.
    """
    url = SKITOUR_API_URL + f'sortie/{id_outing}'
    headers = {'cle': os.getenv('SKITOUR_API_TOKEN')}
    response = requests.get(url, headers=headers, timeout=10)
    return response.json()

def get_recent_outings(massif_id: str) -> List[Dict]:
    """
    Fetch the list of recent outings for a given massif.

    Args:
        massif_id (str): ID of the massif.

    Returns:
        List[Dict]: List of recent outings.
    """
    url = SKITOUR_API_URL + 'sorties'
    headers = {'cle': os.getenv('SKITOUR_API_TOKEN')}
    params = {'m': massif_id, 'j':30}
    response = requests.get(url, headers=headers, params=params, timeout=10)
    response = response.json()
    if response:
    
        for _response in response:
            _response['date'] = datetime.datetime.fromtimestamp(float(_response['date'])).strftime('%Y-%m-%d')
            _response['description'] = get_outing(_response['id'])
        return response
    else: 
        return []
    

   