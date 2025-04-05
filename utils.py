import math
import datetime
import pytz
from timezonefinder import TimezoneFinder
from geopy.geocoders import Nominatim
import swisseph as swe

# Initialize Swiss Ephemeris
swe.set_ephe_path()

def normalize_angle(angle):
    """Normalize angle to [0, 360) degrees"""
    try:
        # Handle tuple or list inputs
        if isinstance(angle, (tuple, list)):
            angle = angle[0]  # Extract the longitude value from the tuple/list
        
        # Handle string inputs
        if isinstance(angle, str):
            angle = float(angle)
            
        # Ensure angle is a numeric value
        return float(angle) % 360
    except (TypeError, ValueError, IndexError) as e:
        # If we can't process the input, return 0 as a fallback
        print(f"Warning: Could not normalize angle {angle}: {e}")
        return 0.0

def angle_to_dms(angle):
    """Convert decimal angle to degrees, minutes, seconds format string"""
    angle = normalize_angle(angle)
    degrees = int(angle)
    minutes = int((angle - degrees) * 60)
    seconds = int(((angle - degrees) * 60 - minutes) * 60)
    return f"{degrees}°{minutes}'{seconds}\""

def angle_to_dm(angle):
    """Convert decimal angle to degrees and minutes
    
    Args:
        angle: Angle in decimal degrees
        
    Returns:
        Tuple of (degrees, minutes) as integers
    """
    try:
        angle = normalize_angle(angle)
        degrees = int(angle)
        minutes = int((angle - degrees) * 60)
        return degrees, minutes
    except (TypeError, ValueError) as e:
        print(f"Warning: Could not convert angle {angle} to DM: {e}")
        return 0, 0

def dms_to_decimal(degrees, minutes=0, seconds=0, direction=None):
    """Convert degrees, minutes, seconds to decimal degrees
    
    Args:
        degrees: Degrees as integer
        minutes: Minutes as integer (default 0)
        seconds: Seconds as integer (default 0)
        direction: Direction as string ('N', 'S', 'E', 'W') or integer (0=N/E, 1=S/W)
        
    Returns:
        Decimal degrees as float
    """
    decimal = float(degrees) + float(minutes)/60 + float(seconds)/3600
    
    # Handle direction
    if direction in ['S', 'W', 1]:
        decimal = -decimal
    
    return decimal

def parse_coordinates_format(coord_str):
    """Parse coordinates in the format "51n39 0w24" to decimal degrees
    
    Args:
        coord_str: Coordinate string in format "51n39 0w24" (lat deg, lat direction, lat min, long deg, long direction, long min)
        
    Returns:
        Tuple (latitude, longitude) in decimal degrees
    """
    # Remove any spaces that might be present
    coord_str = coord_str.replace(" ", "")
    
    # Try to parse the coordinate string
    try:
        # Find the positions of 'n', 's', 'e', 'w' (case insensitive)
        lat_dir_pos = -1
        for i, char in enumerate(coord_str):
            if char.lower() in ['n', 's']:
                lat_dir_pos = i
                break
        
        if lat_dir_pos == -1:
            raise ValueError("Latitude direction (n/s) not found")
        
        lng_dir_pos = -1
        for i, char in enumerate(coord_str):
            if char.lower() in ['e', 'w']:
                lng_dir_pos = i
                break
        
        if lng_dir_pos == -1:
            raise ValueError("Longitude direction (e/w) not found")
        
        # Extract latitude components
        lat_deg = int(coord_str[:lat_dir_pos])
        lat_dir = coord_str[lat_dir_pos].lower()
        
        # Find where latitude minutes end and longitude degrees start
        # We need to find the first non-digit character after the latitude direction
        # or the first digit of the longitude degrees
        lng_start = lat_dir_pos + 1
        while lng_start < len(coord_str) and coord_str[lng_start].isdigit():
            lng_start += 1
        
        lat_min = int(coord_str[lat_dir_pos+1:lng_start])
        
        # Now find where longitude degrees start - the first digit after the latitude minutes
        lng_deg_start = lng_start
        while lng_deg_start < len(coord_str) and not coord_str[lng_deg_start].isdigit():
            lng_deg_start += 1
        
        if lng_deg_start >= lng_dir_pos:
            # No longitude degrees specified
            lng_deg = 0
        else:
            lng_deg = int(coord_str[lng_deg_start:lng_dir_pos])
        
        # Get longitude direction
        lng_dir = coord_str[lng_dir_pos].lower()
        
        # Extract longitude minutes
        lng_min_start = lng_dir_pos + 1
        if lng_min_start < len(coord_str):
            lng_min = int(coord_str[lng_min_start:])
        else:
            lng_min = 0
        
        # Convert to decimal degrees
        lat_decimal = lat_deg + (lat_min / 60.0)
        if lat_dir == 's':
            lat_decimal = -lat_decimal
            
        lng_decimal = lng_deg + (lng_min / 60.0)
        if lng_dir == 'w':
            lng_decimal = -lng_decimal
            
        return lat_decimal, lng_decimal
    
    except (ValueError, IndexError) as e:
        raise ValueError(f"Could not parse coordinates: {coord_str}. Error: {e}")

def parse_coordinates(coordinates):
    """Parse coordinates in specified format to decimal degrees
    
    Supported formats:
    - Standard "51n39 0w24" format (lat deg, lat direction, lat min, long deg, long direction, long min)
    - Decimal degrees (e.g., "52.6369, -1.1398")
    - AstroSeek format dict with keys for degrees, minutes, direction
    - Tuple of decimal coordinates (lat, lng)
    
    Args:
        coordinates: Coordinates in any supported format
        
    Returns:
        Tuple (latitude, longitude) in decimal degrees
    """
    if isinstance(coordinates, str):
        # Check if it's using the standard format pattern (51n39 0w24)
        has_dir_letters = any(c in coordinates.lower() for c in ['n', 's', 'e', 'w'])
        if has_dir_letters:
            return parse_coordinates_format(coordinates)
            
        # Check if it's already in decimal format (e.g. "52.6369, -1.1398")
        elif ',' in coordinates:
            parts = coordinates.replace(' ', '').split(',')
            if len(parts) == 2:
                try:
                    lat, lng = float(parts[0]), float(parts[1])
                    return lat, lng
                except ValueError:
                    pass
    
    elif isinstance(coordinates, dict):
        # Handle AstroSeek format
        lat_dict = coordinates.get('latitude', {})
        lng_dict = coordinates.get('longitude', {})
        
        if lat_dict and lng_dict:
            lat_deg = lat_dict.get('degrees', 0)
            lat_min = lat_dict.get('minutes', 0)
            lat_dir = lat_dict.get('direction', 0)  # 0=N, 1=S
            
            lng_deg = lng_dict.get('degrees', 0)
            lng_min = lng_dict.get('minutes', 0)
            lng_dir = lng_dict.get('direction', 0)  # 0=E, 1=W
            
            lat = dms_to_decimal(lat_deg, lat_min, 0, 'S' if lat_dir == 1 else 'N')
            lng = dms_to_decimal(lng_deg, lng_min, 0, 'W' if lng_dir == 1 else 'E')
            
            return lat, lng
            
    elif isinstance(coordinates, tuple) and len(coordinates) == 2:
        # Already in (lat, lng) format
        return coordinates
        
    raise ValueError(f"Could not parse coordinates: {coordinates}")

def zodiac_sign(angle):
    """Get zodiac sign from angle"""
    signs = ["Aries", "Taurus", "Gemini", "Cancer", 
             "Leo", "Virgo", "Libra", "Scorpio", 
             "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
    sign_index = int(normalize_angle(angle) / 30)
    return signs[sign_index]

def zodiac_sign_symbol(angle):
    """Get zodiac sign symbol from angle"""
    signs = ["♈", "♉", "♊", "♋", "♌", "♍", "♎", "♏", "♐", "♑", "♒", "♓"]
    sign_index = int(normalize_angle(angle) / 30)
    return signs[sign_index]

def get_aspect_symbol(aspect_name):
    """Get symbol for aspect type"""
    symbols = {
        "conjunction": "☌",
        "opposition": "☍",
        "square": "□",
        "trine": "△",
        "sextile": "⚹",
        "quincunx": "⚻",
        "semisextile": "⚺",
        "semisquare": "∠",
        "sesquisquare": "⚼",
        "Conjunction": "☌",
        "Opposition": "☍",
        "Trine": "△",
        "Square": "□",
        "Sextile": "⚹",
        "Quincunx": "⚻",
        "Semi-sextile": "⚺",
        "Quintile": "Q",
        "Bi-quintile": "bQ",
        "Semi-square": "⚼",
        "Sesquiquadrate": "⚿",
        "Parallel": "⦵",
        "Contra-parallel": "⦶"
    }
    return symbols.get(aspect_name, aspect_name)

def get_planet_symbol(planet_name):
    """Get the symbol for a planet"""
    symbols = {
        'Sun': '☉',
        'Moon': '☽',
        'Mercury': '☿',
        'Venus': '♀',
        'Mars': '♂',
        'Jupiter': '♃',
        'Saturn': '♄',
        'Uranus': '♅',
        'Neptune': '♆',
        'Pluto': '♇',
        'North Node': '☊',
        'South Node': '☋',
        'Chiron': '⚷',
        'Ceres': '⚳',
        'Pallas': '⚴',
        'Juno': '⚵',
        'Vesta': '⚶',
        'Ascendant': 'Asc',
        'Midheaven': 'MC',
        'Descendant': 'Desc',
        'IC': 'IC'
    }
    return symbols.get(planet_name, planet_name)

def are_in_aspect(angle1, angle2, aspect_type, orb=1.0):
    """Check if two angles form a specified aspect within the given orb
    
    Args:
        angle1: First angle in degrees
        angle2: Second angle in degrees
        aspect_type: One of "conjunction", "opposition", "square", "trine", "sextile"
        orb: Maximum allowed deviation from exact aspect in degrees
        
    Returns:
        Boolean indicating if the angles form the specified aspect
    """
    aspects = {
        "conjunction": 0,
        "opposition": 180,
        "square": 90,
        "trine": 120,
        "sextile": 60,
        "quincunx": 150,
        "semisextile": 30,
        "semisquare": 45,
        "sesquisquare": 135
    }
    
    if aspect_type not in aspects:
        raise ValueError(f"Unknown aspect type: {aspect_type}")
    
    aspect_angle = aspects[aspect_type]
    
    # Calculate the absolute angular difference
    diff = abs(normalize_angle(angle1 - angle2))
    diff = min(diff, 360 - diff)
    
    # Check if the difference is within the specified aspect angle ± orb
    return abs(diff - aspect_angle) <= orb

def aspect_exact_angle(angle1, angle2, aspect_type):
    """Calculate how exact an aspect is in degrees and minutes
    
    Args:
        angle1: First angle in degrees
        angle2: Second angle in degrees
        aspect_type: One of the supported aspect types
        
    Returns:
        Tuple (is_applying, angular_difference, exactness)
        - is_applying: True if planets are moving toward exact aspect, False if separating
        - angular_difference: Absolute difference from exact aspect in degrees
        - exactness: String representation of the exactness
    """
    aspects = {
        "conjunction": 0,
        "opposition": 180,
        "square": 90,
        "trine": 120,
        "sextile": 60,
        "quincunx": 150,
        "semisextile": 30,
        "semisquare": 45,
        "sesquisquare": 135
    }
    
    if aspect_type not in aspects:
        raise ValueError(f"Unknown aspect type: {aspect_type}")
    
    aspect_angle = aspects[aspect_type]
    
    # Calculate the absolute angular difference
    diff = abs(normalize_angle(angle1 - angle2))
    diff = min(diff, 360 - diff)
    
    # Calculate the difference from exact aspect
    angular_difference = abs(diff - aspect_angle)
    
    # Determine if applying or separating (simplified assumption)
    # This will be calculated more accurately in astro_transits.py
    is_applying = True
    
    # Format the exactness
    exactness = angle_to_dm(angular_difference)
    
    return (is_applying, angular_difference, exactness)

def calculate_whole_sign_houses(asc_degree):
    """Calculate Whole Sign house cusps based on Ascendant degree
    
    Args:
        asc_degree: Ascendant degree
        
    Returns:
        List of house cusps in degrees
    """
    # In Whole Sign houses, each house cusp is at 0° of each sign
    # Starting from the sign that contains the Ascendant
    asc_sign = int(normalize_angle(asc_degree) / 30)
    
    # Create house cusps array (12 houses)
    house_cusps = []
    for i in range(12):
        # Each cusp is at 0° of the sign, so we take the start of each sign
        house_sign = (asc_sign + i) % 12
        house_cusps.append(house_sign * 30)
    
    return house_cusps

def calculate_houses(jd, lat, lng, house_system='P'):
    """Calculate house cusps using Swiss Ephemeris with specified house system
    
    Args:
        jd: Julian day
        lat: Latitude in degrees
        lng: Longitude in degrees
        house_system: House system identifier ('P' for Placidus, 'W' for Whole Sign)
        
    Returns:
        List of house cusps in degrees
    """
    try:
        if house_system == 'W':
            # For Whole Sign, we need to get the Ascendant first
            houses, ascmc = swe.houses(jd, lat, lng, b'P')  # Get Placidus to find Ascendant
            asc_degree = ascmc[0]
            # Then calculate Whole Sign houses
            return calculate_whole_sign_houses(asc_degree)
        else:
            # Using the specified house system
            houses, ascmc = swe.houses(jd, lat, lng, house_system.encode())
            return list(houses)
    except Exception as e:
        # Fallback to simple houses if there's an error
        print(f"Warning: Could not calculate houses: {e}")
        return [i * 30 for i in range(12)]

def get_house_number(house_cusps, angle):
    """Get the house number for a given angle
    
    Args:
        house_cusps: List of house cusps
        angle: Angle in degrees
        
    Returns:
        House number (1-12)
    """
    angle = normalize_angle(angle)
    
    # For Whole Sign houses, this is simpler
    if all(h % 30 == 0 for h in house_cusps):
        # This is likely a Whole Sign house system
        return ((int(angle) // 30) + 1 - (int(house_cusps[0]) // 30)) % 12 or 12
    
    # Regular house system with potentially irregular cusps
    for i in range(11):
        if house_cusps[i] <= angle < house_cusps[i+1]:
            return i + 1
    
    # Last house (between last cusp and first cusp)
    return 12

def get_timezone_from_coordinates(lat, lng):
    """Get timezone string from coordinates using timezonefinder
    
    Args:
        lat: Latitude in decimal degrees
        lng: Longitude in decimal degrees
        
    Returns:
        Timezone string (e.g., 'Europe/London')
    """
    try:
        tf = TimezoneFinder()
        tz_str = tf.timezone_at(lat=lat, lng=lng)
        if not tz_str:
            # Fallback to UTC if timezone cannot be determined
            return "UTC"
        return tz_str
    except Exception as e:
        print(f"Warning: Error determining timezone: {e}")
        return "UTC"

def datetime_to_julian_day(dt, timezone_str=None):
    """Convert datetime to Julian day
    
    Args:
        dt: Datetime object
        timezone_str: Timezone string (if None, dt is assumed to be in UTC)
        
    Returns:
        Julian day as float
    """
    if timezone_str:
        tz = pytz.timezone(timezone_str)
        if dt.tzinfo is None:
            dt = tz.localize(dt)
        dt = dt.astimezone(pytz.UTC)
    
    # Convert to Julian day
    jd = (dt.timestamp() / 86400.0) + 2440587.5
    
    return jd

def get_current_location():
    """Get current location based on IP address (approximate)
    
    Returns:
        Tuple (location_name, (lat, lng))
    """
    try:
        # Try to get location from IP
        import requests
        response = requests.get('https://ipinfo.io/json')
        data = response.json()
        
        if 'loc' in data:
            # Split the location string "lat,lng"
            lat, lng = map(float, data['loc'].split(','))
            location_name = f"{data.get('city', '')}, {data.get('country', '')}"
            return location_name, (lat, lng)
    except Exception as e:
        print(f"Warning: Could not determine current location: {e}")
    
    # Default to Leicester, UK as specified by the user
    return "Leicester, UK", (52.6369, -1.1398) 