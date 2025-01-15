import os
import re
import requests
import xml.etree.ElementTree as ET
from typing import List, Dict
from meteofrance_api import MeteoFranceClient

METEOFRANCE_API_URL = 'https://public-api.meteofrance.fr/public/DPBRA/v1/'
METEO_FRANCE_TOKEN = os.getenv('METEO_FRANCE_API_TOKEN')

def get_massifs_meteo_france() -> List[Dict]:
    """
    Fetch the list of massifs from Meteo France API.

    Returns:
        List[Dict]: List of massifs with their details.
    """
    url = METEOFRANCE_API_URL + 'liste-massifs'
    headers = {'apikey': METEO_FRANCE_TOKEN, 'accept': '*/*'}
    response = requests.get(url, headers=headers)
    response = response.json()
    liste_massifs = []
    for massif in response['features']:
        liste_massifs.append({
            "id": massif['properties']['code'],
            "nom": massif['properties']['title'],
            "groupe": massif['properties']['Departemen'],
        })
    return liste_massifs

def extraire_texte(element: ET.Element) -> str:
    """
    Extract all text from an XML element recursively.

    Args:
        element (ET.Element): XML element.

    Returns:
        str: Extracted text.
    """
    texte = element.text or ""
    for enfant in element:
        texte += extraire_texte(enfant)
    texte += element.tail or ""
    return texte

def get_massif_conditions(massif_id: str) -> str:
    """
    Fetch the weather conditions for a given massif.

    Args:
        massif_id (str): ID of the massif.

    Returns:
        str: Weather conditions in plain text.
    """
    url = METEOFRANCE_API_URL + 'massif/BRA'
    headers = {'apikey': METEO_FRANCE_TOKEN, 'accept': '*/*'}
    params = {'id-massif': massif_id, "format": "xml"}
    response = requests.get(url, headers=headers, params=params)
    xml_text = response.text
    root = ET.fromstring(xml_text)
    text = extraire_texte(root)
    #remove file names
    text = re.sub(r'\b[\w\-]+\.[a-zA-Z0-9]+\b', '', text).strip()
    return text

def get_forecast(latitude, longitude): 
    
    client = MeteoFranceClient(METEO_FRANCE_TOKEN)
    forecast = client.get_forecast(latitude, longitude)
    