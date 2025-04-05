"""
Astrological Transit Calculator - AstroSeek Integration Module

This module provides functionality to calculate transits using the AstroSeek website.
It uses web scraping to fetch transit data from AstroSeek and formats it to match
the structure of transits calculated with the Swiss Ephemeris.
"""

import re
import time
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional, Union

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

from astro_transits import fetch_transit_interpretation
from utils import parse_coordinates, get_planet_symbol, get_aspect_symbol, zodiac_sign_symbol

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
ZODIAC_ORDER = [
    "Aries", "Taurus", "Gemini", "Cancer", 
    "Leo", "Virgo", "Libra", "Scorpio", 
    "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

PLANET_INDEX_MAPPING = {
    "Sun": 0,
    "Moon": 1,
    "Mercury": 2,
    "Venus": 3,
    "Mars": 4,
    "Jupiter": 5,
    "Saturn": 6,
    "Uranus": 7,
    "Neptune": 8,
    "Pluto": 9
}

RULERSHIP = {
    "Sun": ["Leo"],
    "Moon": ["Cancer"],
    "Mercury": ["Gemini", "Virgo"],
    "Venus": ["Taurus", "Libra"],
    "Mars": ["Aries"],
    "Jupiter": ["Sagittarius"],
    "Saturn": ["Capricorn"],
    "Uranus": ["Aquarius"],
    "Neptune": ["Pisces"],
    "Pluto": ["Scorpio"]
}

ASPECT_MAPPING = {
    "conjunction": "cj",
    "trine": "tr",
    "sextile": "sx",
    "square": "sq",
    "opposition": "op"
}

def generate_astroseek_url(birth_data, period_data):
    """
    Generate an AstroSeek URL based on birth data and period.
    
    Args:
        birth_data: Dictionary containing birth information
        period_data: Dictionary or string containing period information
    
    Returns:
        URL string for AstroSeek transit calculation
    """
    # Extract birth data
    birth_day = datetime.strptime(birth_data["date"], "%Y-%m-%d").day
    birth_month = datetime.strptime(birth_data["date"], "%Y-%m-%d").month
    birth_year = datetime.strptime(birth_data["date"], "%Y-%m-%d").year
    birth_hour = datetime.strptime(birth_data["time"], "%H:%M").hour
    birth_minute = datetime.strptime(birth_data["time"], "%H:%M").minute
    
    # Parse coordinates in format "51n39 0w24"
    lat_deg = 0
    lat_min = 0
    lat_dir = 0  # 0 = North, 1 = South
    lng_deg = 0
    lng_min = 0
    lng_dir = 0  # 0 = East, 1 = West
    
    if "coordinates" in birth_data:
        coord_str = birth_data["coordinates"]
        try:
            # Parse the coordinates using the utility function
            lat, lng = parse_coordinates(coord_str)
            
            # Convert decimal degrees to DMS for AstroSeek
            # Latitude
            lat_abs = abs(lat)
            lat_deg = int(lat_abs)
            lat_min = int((lat_abs - lat_deg) * 60)
            lat_dir = 1 if lat < 0 else 0  # 0 = North, 1 = South
            
            # Longitude
            lng_abs = abs(lng)
            lng_deg = int(lng_abs)
            lng_min = int((lng_abs - lng_deg) * 60)
            lng_dir = 1 if lng < 0 else 0  # 0 = East, 1 = West, opposite of standard
        except Exception as e:
            logger.error(f"Error parsing coordinates: {e}")
            # Use default coordinates (0,0) if parsing fails
    
    # Determine the transit period (year and month)
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    transit_year = current_year
    transit_month = current_month
    
    if isinstance(period_data, str):
        # Format YYYY-MM
        period_parts = period_data.split("-")
        if len(period_parts) == 2:
            transit_year = int(period_parts[0])
            transit_month = int(period_parts[1])
            
            # If month is in the past, use next year
            if transit_month < current_month and transit_year == current_year:
                transit_year += 1
    elif isinstance(period_data, dict):
        if "year" in period_data and "month" in period_data:
            transit_year = period_data["year"]
            transit_month = period_data["month"]
        elif "start" in period_data:
            # Use the start date of the range
            start_date = period_data["start"]
            if isinstance(start_date, str):
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                transit_year = start_dt.year
                transit_month = start_dt.month
    
    # Construct the URL
    url = (
        f"https://horoscopes.astro-seek.com/calculate-personal-transit-calendar/"
        f"?edit_input_data=1&send_calculation=1"
        f"&muz_narozeni_den={birth_day}"
        f"&muz_narozeni_mesic={birth_month}"
        f"&muz_narozeni_rok={birth_year}"
        f"&muz_narozeni_hodina={birth_hour}"
        f"&muz_narozeni_minuta={birth_minute}"
    )
    
    # Add coordinates
    url += f"&muz_narozeni_sirka_stupne={lat_deg}"
    url += f"&muz_narozeni_sirka_minuty={lat_min}"
    url += f"&muz_narozeni_sirka_smer={lat_dir}"
    url += f"&muz_narozeni_delka_stupne={lng_deg}"
    url += f"&muz_narozeni_delka_minuty={lng_min}"
    url += f"&muz_narozeni_delka_smer={lng_dir}"
    
    # Add other parameters
    url += (
        f"&muz_narozeni_timezone_form=auto"
        f"&muz_narozeni_timezone_dst_form=auto"
        f"&zena_planeta_navrat=planety_rocni_all"
        f"&kalendar_aspekt=aspekty_all"
        f"&muz_planeta_navrat=planety_all"
        f"&revoluce_narozeni_rok={transit_year}"
        f"&revoluce_narozeni_rok_do={transit_year}"
        f"&revoluce_narozeni_mesic={transit_month:02d}"
        f"&progrese="
        f"&house_system=whole_horizon"
    )
    
    return url

def determine_ascendant_and_houses(birth_data):
    """
    Determine the Ascendant and house positions for planets based on birth data.
    This function uses a simplified approach since we don't have access to the complete 
    chart calculation functionality.
    
    Args:
        birth_data: Dictionary containing birth information
        
    Returns:
        Tuple of (ascendant_sign, house_positions)
    """
    # Using Nil's default values as in TransitReport.py
    ascendant = "Cancer"
    house_positions = [11, 4, 11, 10, 6, 12, 12, 8, 8, 6]
    
    return ascendant, house_positions

def parse_astroseek_transits(html_content, ascendant, house_positions):
    """
    Parse the HTML content from AstroSeek to extract transit information.
    
    Args:
        html_content: HTML content from AstroSeek
        ascendant: Ascendant sign
        house_positions: Array of house positions for each planet
        
    Returns:
        List of transit dictionaries
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    transit_rows = soup.select('.detail-rozbor-items table tbody tr')
    
    transits = []
    
    # Calculate house cusps based on ascendant
    house_index = []
    for x in range(0, 12):
        house_index.append(ZODIAC_ORDER[x])
    ascendant_index = ZODIAC_ORDER.index(ascendant.capitalize())
    house_index = ZODIAC_ORDER[ascendant_index:] + ZODIAC_ORDER[:ascendant_index]
    
    # Skip header rows
    for row in transit_rows[2:]:
        columns = row.find_all('td')
        
        # Ensure we have enough columns
        if len(columns) < 4:
            continue
            
        try:
            # Extract date
            date_element = columns[0].find('strong')
            if not date_element:
                continue
                
            date_str = date_element.text.strip()
            
            # Extract time
            time_element = columns[0].find('span', class_='form-info')
            if not time_element:
                continue
                
            time_str = time_element.text.strip()[-5:]
            
            # Convert to datetime
            date_obj = datetime.strptime(f"{date_str} {datetime.now().year} {time_str}", "%b %d %Y %H:%M")
            formatted_date = date_obj.strftime("%Y-%m-%d")
            
            # Extract transiting planet 
            transit_planet_img = columns[1].find('img', class_='astro_symbol')
            if not transit_planet_img:
                continue
                
            transit_planet = transit_planet_img['alt'].split()[1].strip()
            
            # Extract aspect and natal planet following the approach from TransitReport.py
            # Extract natal planet text
            natal_planet = re.sub(r'[^a-zA-Z]', '', str(columns[1])[-14:-5])
            if natal_planet == "Merc":
                natal_planet = "Mercury"
            
            # Extract aspect
            aspect_elements = columns[1].find_all('img')
            if len(aspect_elements) < 2:
                continue
                
            aspect = aspect_elements[1]['alt'].split()[1].strip()
            
            # Calculate transit planet house
            transit_house_text = str(columns[3])[-8:-5]
            transit_planet_house = int(re.sub(r'[^0-9]', '', transit_house_text))
            
            # Get natal planet house
            i = PLANET_INDEX_MAPPING.get(natal_planet, 0)
            natal_planet_house = house_positions[i] if i < len(house_positions) else 0
            
            # Extract position (sign and degree)
            position_text = columns[2].text.strip()
            sign_match = re.search(r'([A-Za-z]+)', position_text)
            degree_match = re.search(r'(\d+)°(\d+)', position_text)
            
            sign = sign_match.group(1) if sign_match else ""
            degrees = int(degree_match.group(1)) if degree_match else 0
            minutes = int(degree_match.group(2)) if degree_match else 0
            
            # Map sign name to symbol
            sign_symbols = {
                "Aries": "♈",
                "Taurus": "♉",
                "Gemini": "♊",
                "Cancer": "♋",
                "Leo": "♌",
                "Virgo": "♍",
                "Libra": "♎",
                "Scorpio": "♏",
                "Sagittarius": "♐",
                "Capricorn": "♑",
                "Aquarius": "♒",
                "Pisces": "♓"
            }
            sign_symbol = sign_symbols.get(sign, "")
            
            # Check if retrograde
            is_retrograde = "R" in position_text
            
            # Create position string
            position = f"{sign_symbol} {degrees}°{minutes}'"
            
            # Create transit object in same format as astro_transits.py output
            transit = {
                "date": formatted_date,
                "time": time_str,
                "transit_planet": transit_planet,
                "natal_planet": natal_planet,
                "aspect": aspect.lower(),
                "orb": 0.0,  # AstroSeek doesn't provide exact orb values
                "is_retrograde": is_retrograde,
                "is_applying": True,  # Default to applying as AstroSeek doesn't specify
                "transit_planet_symbol": get_planet_symbol(transit_planet),
                "natal_planet_symbol": get_planet_symbol(natal_planet),
                "aspect_symbol": get_aspect_symbol(aspect.lower()),
                "planet_abbr": natal_planet,
                "house": f"H{natal_planet_house}",
                "house_number": natal_planet_house,
                "position": position,
                "longitude": (ZODIAC_ORDER.index(sign) * 30) + degrees + (minutes / 60.0) if sign in ZODIAC_ORDER else 0
            }
            
            # Add to transits list
            transits.append(transit)
            
        except Exception as e:
            logger.error(f"Error parsing transit row: {e}")
            continue
    
    return transits

def fetch_transits_from_astroseek(birth_data, period_data):
    """
    Fetch transits from AstroSeek based on birth data and period.
    
    Args:
        birth_data: Dictionary containing birth information
        period_data: Dictionary or string containing period information
        
    Returns:
        List of transit dictionaries
    """
    logger.info("Starting AstroSeek transit calculation...")
    
    logger.info("Fetching transits from AstroSeek...")
    
    # Generate the AstroSeek URL
    url = generate_astroseek_url(birth_data, period_data)
    logger.info(f"Generated AstroSeek URL: {url}")
    
    # Determine ascendant and house positions
    ascendant, house_positions = determine_ascendant_and_houses(birth_data)
    logger.info(f"Using Ascendant: {ascendant}")
    
    try:
        # Initialize the Selenium WebDriver with headless mode for Azure
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        
        # Create a service with webdriver_manager to handle chromedriver installation
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
        except Exception as e:
            logger.warning(f"Error using ChromeDriverManager: {e}. Trying default ChromeDriver...")
            # Fall back to using the built-in ChromeDriver in Azure
            driver = webdriver.Chrome(options=chrome_options)
        
        # Load the AstroSeek URL
        logger.info("Loading AstroSeek page...")
        driver.get(url)
        driver.implicitly_wait(10)  # Wait up to 10 seconds for elements to load
        
        # Get the page source
        html_content = driver.page_source
        
        # Close the browser
        driver.quit()
        
        # Parse the transits
        logger.info("Parsing transits from AstroSeek response...")
        transits = parse_astroseek_transits(html_content, ascendant, house_positions)
        
        # Add interpretations
        logger.info("Adding interpretations to transits...")
        for transit in transits:
            interpretation_data = fetch_transit_interpretation(
                transit['transit_planet'], 
                transit['aspect'], 
                transit['natal_planet']
            )
            transit["interpretation"] = interpretation_data.get("interpretation")
            transit["interpretation_url"] = interpretation_data.get("source_url")
        
        logger.info(f"Successfully fetched {len(transits)} transits from AstroSeek")
        return transits
        
    except Exception as e:
        logger.error(f"Error fetching transits from AstroSeek: {e}")
        return []

def get_astroseek_transits(birth_data, period_data, config=None):
    """
    Get transits from AstroSeek with the same interface as get_transits in astro_transits.py.
    
    Args:
        birth_data: Dictionary containing birth information
        period_data: Dictionary or string containing period information
        config: Configuration options (optional)
        
    Returns:
        List of transit dictionaries
    """
    logger.info("Starting AstroSeek transit calculation...")
    
    # Validate birth data
    if not birth_data:
        logger.error("No birth data provided")
        return []
        
    required_fields = ["date", "time"]
    for field in required_fields:
        if field not in birth_data:
            logger.error(f"Birth data missing required field: {field}")
            return []
    
    # Either coordinates must be provided
    if "coordinates" not in birth_data:
        logger.error("Birth data must include coordinates")
        return []
    
    # Validate period data
    if not period_data:
        logger.error("No period data provided")
        return []
    
    # Fetch transits from AstroSeek
    transits = fetch_transits_from_astroseek(birth_data, period_data)
    
    # Filter by aspect set if specified
    if config and "aspect_set" in config and config["aspect_set"] != "all":
        if config["aspect_set"] == "major":
            major_aspects = ["conjunction", "opposition", "square", "trine", "sextile"]
            transits = [t for t in transits if t["aspect"].lower() in major_aspects]
        else:
            # Custom aspect set
            aspect_set = config["aspect_set"]
            if isinstance(aspect_set, list):
                transits = [t for t in transits if t["aspect"].lower() in aspect_set]
    
    # Sort by date and time
    transits = sorted(transits, key=lambda t: (t["date"], t["time"]))
    
    return transits 