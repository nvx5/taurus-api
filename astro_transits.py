import swisseph as swe
import datetime
import pytz
import requests
import re
from bs4 import BeautifulSoup
from timezonefinder import TimezoneFinder
from utils import (
    normalize_angle, are_in_aspect, get_timezone_from_coordinates, 
    datetime_to_julian_day, calculate_houses, get_house_number,
    zodiac_sign, zodiac_sign_symbol, angle_to_dm, get_aspect_symbol,
    parse_coordinates, get_planet_symbol
)

# Initialize Swiss Ephemeris
swe.set_ephe_path()

# Define constants
PLANETS = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mercury": swe.MERCURY,
    "Venus": swe.VENUS,
    "Mars": swe.MARS,
    "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN,
    "Uranus": swe.URANUS,
    "Neptune": swe.NEPTUNE,
    "Pluto": swe.PLUTO
}

# All possible aspects
ALL_ASPECTS = {
    "conjunction": 0,
    "sextile": 60,
    "square": 90, 
    "trine": 120,
    "opposition": 180,
    "quincunx": 150,
    "semisextile": 30,
    "semisquare": 45,
    "sesquisquare": 135
}

# Default aspect sets
ASPECT_SETS = {
    "major": ["conjunction", "opposition", "square", "trine", "sextile"],
    "minor": ["quincunx", "semisextile", "semisquare", "sesquisquare"],
    "all": list(ALL_ASPECTS.keys())
}

# AstroSeek's exact orb settings
DEFAULT_ORBS = {
    "conjunction": 7.0,    # Major aspect: 7° default
    "opposition": 7.0,     # Major aspect: 7° default
    "square": 7.0,         # Major aspect: 7° default
    "trine": 7.0,          # Major aspect: 7° default
    "sextile": 4.0,        # Sextile: 4° default
    "quincunx": 2.5,       # Minor aspect: 2.5° fixed
    "semisextile": 2.5,    # Minor aspect: 2.5° fixed
    "semisquare": 2.5,     # Minor aspect: 2.5° fixed
    "sesquisquare": 2.5    # Minor aspect: 2.5° fixed
}

# Luminary-specific orb adjustments
LUMINARY_ORB_ADJUSTMENTS = {
    "Sun": {
        "conjunction": 3.0,  # +3° for major aspects
        "opposition": 3.0,   # +3° for major aspects
        "square": 3.0,       # +3° for major aspects
        "trine": 3.0,        # +3° for major aspects
        "sextile": 1.5       # +1.5° for sextile
    },
    "Moon": {
        "conjunction": 3.0,  # +3° for major aspects
        "opposition": 3.0,   # +3° for major aspects
        "square": 3.0,       # +3° for major aspects
        "trine": 3.0,        # +3° for major aspects
        "sextile": 1.5       # +1.5° for sextile
    }
}

# Default planet-specific orbs
DEFAULT_PLANET_ORBS = {
    "Sun": 2.0,
    "Moon": 2.0,
    "Mercury": 1.5,
    "Venus": 1.5,
    "Mars": 1.8,
    "Jupiter": 1.5,
    "Saturn": 1.5,
    "Uranus": 1.3,
    "Neptune": 1.3,
    "Pluto": 1.3
}

# URL patterns for transit interpretations
ASTRO_X_FILES_BASE_URL = "https://www.astrology-x-files.com/transits/"

# Mapping for aspect abbreviations in URLs
ASPECT_URL_ABBR = {
    "conjunction": "cj",
    "opposition": "op",
    "square": "op",
    "trine": "tr",
    "sextile": "tr"
}

# Planet abbreviations for URL construction
PLANET_URL_ABBR = {
    "Sun": "sun",
    "Moon": "moon",
    "Mercury": "mercury",
    "Venus": "venus",
    "Mars": "mars",
    "Jupiter": "jupiter",
    "Saturn": "saturn",
    "Uranus": "uranus",
    "Neptune": "neptune",
    "Pluto": "pluto"
}

# Cache for transit interpretations to avoid multiple requests
TRANSIT_INTERPRETATION_CACHE = {}

class BirthChart:
    def __init__(self, birth_data):
        """Initialize birth chart with birth data
        
        Args:
            birth_data: Dictionary containing birth information
                Required keys:
                - date: Birth date in format "YYYY-MM-DD"
                - time: Birth time in format "HH:MM"
                - coordinates: Coordinates as string "51n39 0w24"
                Optional keys:
                - house_system: House system identifier ('P' for Placidus, 'W' for Whole Sign)
                - timezone_str: Explicit timezone string (if not provided, will be derived from coordinates)
        """
        # Get required fields
        date = birth_data["date"]
        time = birth_data["time"]
        coordinates = birth_data["coordinates"]
        
        # Parse birth datetime
        if isinstance(date, str) and isinstance(time, str):
            birth_dt = datetime.datetime.fromisoformat(f"{date}T{time}")
        elif isinstance(date, datetime.date) and isinstance(time, datetime.time):
            birth_dt = datetime.datetime.combine(date, time)
        else:
            raise ValueError(f"Invalid date/time format: {date} {time}")
            
        # Optional timezone handling
        timezone_str = birth_data.get("timezone_str", None)
        
        # Parse coordinates
        try:
            lat, lng = parse_coordinates(coordinates)
        except Exception as e:
            raise ValueError(f"Error parsing coordinates: {str(e)}")
            
        # Get timezone from coordinates if not provided
        if not timezone_str:
            timezone_str = get_timezone_from_coordinates(lat, lng)
            if not timezone_str:
                timezone_str = "UTC"  # Fallback to UTC
            
        # Calculate Julian day for birth time
        self.birth_jd = datetime_to_julian_day(birth_dt, timezone_str)
        
        # Set geographic coordinates
        self.lat = lat
        self.lng = lng
        
        # Store house system
        self.house_system = birth_data.get("house_system", 'W')  # Default to Whole Sign
        
        # Calculate house cusps
        self.house_cusps = self._calculate_houses()
        
        # Calculate planet positions at birth
        self.natal_positions = {}
        for planet_name, planet_id in PLANETS.items():
            result, status = swe.calc_ut(self.birth_jd, planet_id)
            self.natal_positions[planet_name] = normalize_angle(result[0])
            
    def _calculate_houses(self):
        """Calculate house cusps using Swiss Ephemeris with the specified house system"""
        return calculate_houses(self.birth_jd, self.lat, self.lng, self.house_system)

class TransitCalculator:
    def __init__(self, birth_chart, config=None):
        """Initialize transit calculator with birth chart and configuration
        
        Args:
            birth_chart: BirthChart instance
            config: Dictionary with configuration options
                - current_coordinates: Current coordinates for transit calculations (default: birth coordinates)
                - orb_tolerance: General orb tolerance in degrees (default: 1.0) 
                - aspect_orbs: Dictionary of aspect-specific orbs
                - planet_orbs: Dictionary of planet-specific orbs
                - aspect_set: Which aspects to include ("major", "all", or list of aspect names)
                - time_step: Time step in minutes for transit calculation (default: 10)
        """
        self.birth_chart = birth_chart
        
        # Set default config
        self.config = {
            "current_coordinates": None,
            "orb_tolerance": 1.0,
            "aspect_orbs": DEFAULT_ORBS.copy(),
            "aspect_set": "major",
            "time_step": 10,
            "luminaries": ["Sun", "Moon"]
        }
        
        # Update with provided config
        if config:
            self.config.update(config)
        
        # Apply general orb tolerance to all aspects if specified
        if "orb_tolerance" in self.config and self.config["orb_tolerance"] != 1.0:
            orb_factor = self.config["orb_tolerance"]
            # Scale all orbs by the tolerance factor
            for aspect in self.config["aspect_orbs"]:
                self.config["aspect_orbs"][aspect] *= orb_factor
        
        # Determine which aspects to use
        if isinstance(self.config["aspect_set"], str):
            if self.config["aspect_set"] in ASPECT_SETS:
                self.aspects_to_use = {aspect: ALL_ASPECTS[aspect] for aspect in ASPECT_SETS[self.config["aspect_set"]]}
            else:
                # Default to major aspects
                self.aspects_to_use = {aspect: ALL_ASPECTS[aspect] for aspect in ASPECT_SETS["major"]}
        elif isinstance(self.config["aspect_set"], list):
            # Use provided list of aspects
            self.aspects_to_use = {aspect: ALL_ASPECTS[aspect] for aspect in self.config["aspect_set"] if aspect in ALL_ASPECTS}
        else:
            # Default to major aspects
            self.aspects_to_use = {aspect: ALL_ASPECTS[aspect] for aspect in ASPECT_SETS["major"]}
        
        # Use current coordinates for transit calculations if provided
        current_coordinates = self.config["current_coordinates"]
        if current_coordinates:
            try:
                # Try to parse coordinates
                lat, lng = parse_coordinates(current_coordinates)
                self.current_lat = lat
                self.current_lng = lng
            except Exception:
                # Fall back to birth coordinates if coordinates can't be parsed
                self.current_lat = birth_chart.lat
                self.current_lng = birth_chart.lng
        else:
            # Default to birth coordinates
            self.current_lat = birth_chart.lat
            self.current_lng = birth_chart.lng
        
    def get_aspect_orb(self, aspect, transit_planet, natal_planet):
        """Get appropriate orb for aspect based on planets involved"""
        base_orb = self.config["aspect_orbs"].get(aspect, 0)
        luminaries = self.config.get("luminaries", ["Sun", "Moon"])
        
        # Check if either planet is a luminary
        if transit_planet in luminaries or natal_planet in luminaries:
            if aspect in ["conjunction", "opposition", "square", "trine"]:
                return base_orb + 3.0  # +3° for major aspects with luminaries
            elif aspect == "sextile":
                return base_orb + 1.5  # +1.5° for sextile with luminaries
        
        return base_orb
    
    def _calculate_transit_significance(self, transit):
        """Calculate significance score for a transit (higher is more significant)
        
        Args:
            transit: Transit dictionary
            
        Returns:
            Significance score (float)
        """
        # More significant if closer to exact
        exactness_factor = 1.0
        if "orb" in transit:
            # The closer to exact, the more significant (inverse relationship with orb)
            # AstroSeek seems to favor aspects with very small orbs
            orb = float(transit["orb"])
            max_orb = self.get_aspect_orb(transit["aspect"], transit["transit_planet"], transit["natal_planet"])
            
            # Normalize orb to range 0-1 (where 0 is exact, 1 is maximum allowed orb)
            normalized_orb = orb / max_orb if max_orb > 0 else 1.0
            
            # Exponential decay to prioritize exact aspects more significantly
            # This better matches AstroSeek's preference for very exact aspects
            exactness_factor = max(0.1, 1.0 - (normalized_orb * 0.9))
        
        # Calculate overall significance
        significance = exactness_factor * 10  # Scale factor to match previous range
        
        # Prioritize transits from slower-moving planets
        if transit["transit_planet"] in ["Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]:
            significance *= 1.2
        
        # Applying aspects are more significant than separating ones
        if transit.get("is_applying", False):
            significance *= 1.3  # Increase this factor to match AstroSeek's preference for applying aspects
        
        # Give extra significance to aspects involving Sun and Moon in the natal chart
        if transit["natal_planet"] in ["Sun", "Moon"]:
            significance *= 1.2
            
        return significance
    
    def _check_transit_aspects(self, transit_planet, jd, transit_positions=None):
        """Check for aspects between transit planet and natal planets at given Julian day
        
        Args:
            transit_planet: Name of transiting planet
            jd: Julian day to check
            transit_positions: Pre-calculated transit positions (optional)
            
        Returns:
            List of aspect dictionaries
        """
        aspects = []
        
        # Get transit planet ID
        transit_planet_id = PLANETS[transit_planet]
        
        # Calculate transit planet position if not provided
        if transit_positions and transit_planet in transit_positions:
            trans_pos = transit_positions[transit_planet]
            is_retrograde = False  # Can't determine from pre-calculated positions
        else:
            result, status = swe.calc_ut(jd, transit_planet_id)
            trans_pos = normalize_angle(result[0])
            is_retrograde = result[3] < 0  # Negative speed means retrograde
        
        # Convert JD to datetime
        dt = datetime.datetime.utcfromtimestamp((jd - 2440587.5) * 86400.0)
        
        # Check aspects to each natal planet
        for natal_planet, natal_pos in self.birth_chart.natal_positions.items():
            # Check each possible aspect
            for aspect_type, aspect_angle in self.aspects_to_use.items():
                # Get the appropriate orb for this aspect and planets
                orb_limit = self.get_aspect_orb(aspect_type, transit_planet, natal_planet)
                
                # Check if planets are in aspect
                is_in_aspect, orb = are_in_aspect(trans_pos, natal_pos, aspect_angle, orb_limit)
                
                if is_in_aspect:
                    # Determine if aspect is applying or separating
                    is_applying = self._is_applying(transit_planet, natal_planet, aspect_type, jd)
                    
                    # Calculate house position of transit planet
                    house_number = get_house_number(self.birth_chart.house_cusps, trans_pos)
                    
                    # Format position (sign and degrees)
                    sign = zodiac_sign(trans_pos)
                    sign_symbol = zodiac_sign_symbol(sign)
                    deg, min_sec = angle_to_dm(trans_pos % 30)
                    position = f"{sign_symbol} {deg}°{min_sec}'"
                    
                    # Add to aspects list
                    aspects.append({
                        "transit_planet": transit_planet,
                        "natal_planet": natal_planet,
                        "aspect": aspect_type,
                        "orb": orb,
                        "jd": jd,
                        "date": dt.strftime("%Y-%m-%d"),
                        "time": dt.strftime("%H:%M"),
                        "is_retrograde": is_retrograde,
                        "is_applying": is_applying,
                        "transit_planet_symbol": get_planet_symbol(transit_planet),
                        "natal_planet_symbol": get_planet_symbol(natal_planet),
                        "aspect_symbol": get_aspect_symbol(aspect_type),
                        "planet_abbr": natal_planet,
                        "house": f"H{house_number}",
                        "house_number": house_number,
                        "position": position,
                        "longitude": trans_pos
                    })
        
        return aspects
    
    def _find_exact_transit_time(self, aspect_type, trans_planet_id, natal_pos, 
                                start_jd, end_jd, precision=0.0001):
        """Find the exact time when an aspect becomes exact using binary search
        
        Args:
            aspect_type: The aspect type (conjunction, opposition, etc.)
            trans_planet_id: ID of the transiting planet
            natal_pos: Position of the natal planet
            start_jd: Start Julian day
            end_jd: End Julian day
            precision: Precision in Julian days (default ~8.6 seconds)
            
        Returns:
            Julian day when the aspect is exact, or None if not found
        """
        aspect_angle = self.aspects_to_use[aspect_type]
        
        # Calculate the angular difference at specific Julian day
        def get_angle_diff(jd):
            result, status = swe.calc_ut(jd, trans_planet_id)
            trans_pos = normalize_angle(result[0])
            
            # Calculate angular difference for the aspect
            diff = normalize_angle(trans_pos - natal_pos - aspect_angle)
            if diff > 180:
                diff = diff - 360
            return diff
        
        # Binary search for the exact time
        left_jd, right_jd = start_jd, end_jd
        left_diff, right_diff = get_angle_diff(left_jd), get_angle_diff(right_jd)
        
        # Check if there's a zero crossing between start and end
        if left_diff * right_diff > 0:
            return None  # No crossing
        
        # Binary search until desired precision
        while right_jd - left_jd > precision:
            mid_jd = (left_jd + right_jd) / 2
            mid_diff = get_angle_diff(mid_jd)
            
            if abs(mid_diff) < 0.001:  # Very close to exact aspect
                # Found an exact match
                return mid_jd
            
            if mid_diff * left_diff < 0:
                # Zero crossing between left and mid
                right_jd, right_diff = mid_jd, mid_diff
            else:
                # Zero crossing between mid and right
                left_jd, left_diff = mid_jd, mid_diff
                
        # Return the more accurate time
        return left_jd if abs(left_diff) < abs(right_diff) else right_jd
    
    def _is_applying(self, trans_planet, natal_planet, aspect_type, jd):
        """Check if an aspect is applying (planets moving closer) or separating
        
        Args:
            trans_planet: Name of transiting planet
            natal_planet: Name of natal planet
            aspect_type: Type of aspect
            jd: Julian day
            
        Returns:
            True if aspect is applying, False if separating
        """
        # Get planet ID and natal position
        trans_planet_id = PLANETS[trans_planet]
        natal_pos = self.birth_chart.natal_positions[natal_planet]
        aspect_angle = self.aspects_to_use[aspect_type]
        
        # Calculate positions now and a bit later
        result_now, status = swe.calc_ut(jd, trans_planet_id)
        trans_pos_now = normalize_angle(result_now[0])
        
        # Calculate position a few hours later (more precise than a full day)
        result_later, status = swe.calc_ut(jd + 0.125, trans_planet_id)  # 3 hours later
        trans_pos_later = normalize_angle(result_later[0])
        
        # Calculate current angular difference
        diff_now = abs(normalize_angle(trans_pos_now - natal_pos) - aspect_angle)
        diff_now = min(diff_now, 360 - diff_now)
        
        # Calculate future angular difference
        diff_later = abs(normalize_angle(trans_pos_later - natal_pos) - aspect_angle)
        diff_later = min(diff_later, 360 - diff_later)
        
        # Aspect is applying if planets are getting closer to exact aspect
        return diff_later < diff_now
    
    def _calculate_time_step_transits(self, start_time, transits_by_date):
        """Calculate transits with high time resolution
        
        Args:
            start_time: Start time (datetime object)
            transits_by_date: Dictionary to store found transits by date
            
        Returns:
            None (updates transits_by_date)
        """
        # Convert to Julian day
        start_jd = datetime_to_julian_day(start_time)
        
        # Calculate end time (24 hours later)
        end_time = start_time + datetime.timedelta(days=1)
        end_jd = datetime_to_julian_day(end_time)
        
        # Store date string for indexing
        date_str = start_time.strftime("%Y-%m-%d")
        
        # Calculate step size in Julian days
        time_step_minutes = self.config["time_step"]
        step_jd = time_step_minutes / (24 * 60)
        
        # Get planet positions at each time step
        current_jd = start_jd
        while current_jd < end_jd:
            # Get transiting planet positions at this time step
            planet_positions = {}
            planet_speeds = {}  # Store speeds for determining if retrograde
            
            for planet_name, planet_id in PLANETS.items():
                result, status = swe.calc_ut(current_jd, planet_id)
                planet_positions[planet_name] = normalize_angle(result[0])
                # Store speed for retrograde detection (negative longitude speed means retrograde)
                planet_speeds[planet_name] = result[3]
            
            # Check for aspects between transit and natal planets
            for trans_planet, trans_pos in planet_positions.items():
                trans_planet_id = PLANETS[trans_planet]
                
                # Is the planet retrograde?
                is_retrograde = planet_speeds[trans_planet] < 0
                
                for natal_planet, natal_pos in self.birth_chart.natal_positions.items():
                    for aspect_name, aspect_angle in self.aspects_to_use.items():
                        # Get appropriate orb for this aspect and planets
                        orb_limit = self.get_aspect_orb(aspect_name, trans_planet, natal_planet)
                        
                        # Calculate angular difference for this aspect
                        diff = abs(normalize_angle(trans_pos - natal_pos) - aspect_angle)
                        diff = min(diff, 360 - diff)
                        
                        # If within orb, find exact time
                        if diff <= orb_limit:
                            # Generate a key for this transit to avoid duplicates
                            transit_key = f"{trans_planet}_{aspect_name}_{natal_planet}"
                            
                            # Skip if we've already found this transit for this date
                            if transit_key in transits_by_date.get(date_str, {}):
                                continue
                            
                            # Find the exact time (if it occurs on this day)
                            exact_jd = self._find_exact_transit_time(
                                aspect_name, trans_planet_id, natal_pos, 
                                start_jd, end_jd
                            )
                            
                            if exact_jd:
                                # Get the exact position at the aspect time
                                exact_result, status = swe.calc_ut(exact_jd, trans_planet_id)
                                exact_pos = normalize_angle(exact_result[0])
                                
                                # Convert to datetime
                                exact_dt = datetime.datetime.utcfromtimestamp((exact_jd - 2440587.5) * 86400)
                                
                                # Calculate house position - correct parameter order
                                try:
                                    house_number = get_house_number(self.birth_chart.house_cusps, exact_pos)
                                except Exception:
                                    # Fallback if house calculation fails
                                    house_number = ((int(exact_pos) // 30) + 1)
                                
                                # Determine if applying or separating
                                try:
                                    is_applying = self._is_applying(trans_planet, natal_planet, aspect_name, exact_jd)
                                except Exception:
                                    # Default to applying if calculation fails
                                    is_applying = True
                                
                                # Format position (sign and degrees)
                                # Get zodiac sign name first, then get the symbol
                                sign_name = zodiac_sign(exact_pos)
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
                                sign_symbol = sign_symbols.get(sign_name, "")
                                
                                # Calculate degrees and minutes in sign
                                deg = int(exact_pos % 30)
                                min_sec = int(((exact_pos % 30) - deg) * 60)
                                position = f"{sign_symbol} {deg}°{min_sec}'"
                                
                                # Record the transit
                                transit = {
                                    "date": exact_dt.strftime("%Y-%m-%d"),
                                    "time": exact_dt.strftime("%H:%M"),
                                    "transit_planet": trans_planet,
                                    "aspect": aspect_name,
                                    "aspect_symbol": get_aspect_symbol(aspect_name),
                                    "natal_planet": natal_planet,
                                    "orb": diff,
                                    "jd": exact_jd,
                                    "is_retrograde": is_retrograde,
                                    "is_applying": is_applying,
                                    "transit_planet_symbol": get_planet_symbol(trans_planet),
                                    "natal_planet_symbol": get_planet_symbol(natal_planet),
                                    "planet_abbr": natal_planet,
                                    "house": f"H{house_number}",
                                    "house_number": house_number,
                                    "position": position,
                                    "longitude": exact_pos
                                }
                                
                                # Calculate significance for filtering
                                transit["significance"] = self._calculate_transit_significance(transit)
                                
                                # Add to transits by date dictionary
                                if date_str not in transits_by_date:
                                    transits_by_date[date_str] = {}
                                
                                transits_by_date[date_str][transit_key] = transit
            
            # Move to next time step
            current_jd += step_jd
    
    def calculate_transits(self, period, filter_significance=0.0):
        """Calculate transits for the specified period
        
        Args:
            period: Dictionary containing period information
                Required keys:
                - start: Start date in format "YYYY-MM-DD" or datetime object
                - end: End date in format "YYYY-MM-DD" or datetime object
                OR
                - year: Target year
                - month: Target month (1-12)
            filter_significance: Minimum significance threshold for including transits
            
        Returns:
            List of transit dictionaries
        """
        # Determine start and end dates based on input
        if "start" in period and "end" in period:
            # Use explicit start and end dates
            if isinstance(period["start"], str):
                start_date = datetime.datetime.fromisoformat(period["start"])
                if "T" not in period["start"]:  # Date only
                    start_date = datetime.datetime.combine(start_date.date(), datetime.time(0, 0))
            else:
                start_date = period["start"]
                
            if isinstance(period["end"], str):
                end_date = datetime.datetime.fromisoformat(period["end"])
                if "T" not in period["end"]:  # Date only
                    end_date = datetime.datetime.combine(end_date.date(), datetime.time(0, 0))
            else:
                end_date = period["end"]
        elif "year" in period and "month" in period:
            # Calculate start and end dates for a month
            year = period["year"]
            month = period["month"]
            
            start_date = datetime.datetime(year, month, 1)
            if month == 12:
                end_date = datetime.datetime(year + 1, 1, 1)
            else:
                end_date = datetime.datetime(year, month + 1, 1)
        else:
            raise ValueError("Invalid period specification. Provide either (start, end) or (year, month).")
        
        # Store transits by date to avoid duplicates
        transits_by_date = {}
        
        # Check each day with high time resolution
        current_date = start_date
        while current_date < end_date:
            self._calculate_time_step_transits(current_date, transits_by_date)
            current_date += datetime.timedelta(days=1)
        
        # Flatten the dictionary to a list
        all_transits = []
        for date_transits in transits_by_date.values():
            all_transits.extend(date_transits.values())
        
        # Filter by significance if requested
        if filter_significance > 0:
            all_transits = [t for t in all_transits if t.get("significance", 0) >= filter_significance]
        
        # Sort by date and time
        all_transits.sort(key=lambda x: x["jd"])
        
        return all_transits

def get_transits(birth_data, period_data, config=None):
    """Calculate transits based on birth data and period
    
    Args:
        birth_data: Dictionary containing birth information
            Required keys:
            - date: Birth date in format "YYYY-MM-DD"
            - time: Birth time in format "HH:MM"
            - coordinates: Coordinates as string "51n39 0w24"
            Optional keys:
            - house_system: House system identifier ('P' for Placidus, 'W' for Whole Sign)
        
        period_data: Dictionary containing period information or simple string "YYYY-MM"
            As a string: Target month (e.g., "2025-12")
            As a dictionary:
                Option 1 (month range):
                - year: Target year
                - month: Target month (1-12)
                Option 2 (date range):
                - start: Start date in format "YYYY-MM-DD"
                - end: End date in format "YYYY-MM-DD"
        
        config: Configuration options
            - current_coordinates: Current coordinates for transit calculations (default: birth coordinates)
            - orb_tolerance: General orb tolerance in degrees (default: 1.0)
            - aspect_orbs: Dictionary of aspect-specific orbs
            - planet_orbs: Dictionary of planet-specific orbs 
            - aspect_set: Which aspects to include ("major", "all", or list of aspect names)
            - time_step: Time step in minutes for transit calculation (default: 10)
            - filter_significance: Minimum significance threshold for including transits
        
    Returns:
        List of transit dictionaries with datetime and description
    """
    # Validate birth data
    required_birth_fields = ["date", "time", "coordinates"]
    for field in required_birth_fields:
        if field not in birth_data:
            raise ValueError(f"Missing required birth field: {field}")
    
    # Default configuration
    default_config = {
        "current_coordinates": None, 
        "orb_tolerance": 1.0,
        "aspect_set": "major",
        "time_step": 10,
        "house_system": 'W',
        "filter_significance": 6.0
    }
    
    # Update with provided config
    if config:
        default_config.update(config)
    
    # Ensure house_system is included in birth_data
    if "house_system" not in birth_data and "house_system" in default_config:
        birth_data["house_system"] = default_config["house_system"]
    
    # Parse period data
    if isinstance(period_data, str):
        # Format: "YYYY-MM" for a specific month
        year, month = map(int, period_data.split("-"))
        period = {"year": year, "month": month}
    else:
        # Already in dictionary format
        period = period_data
    
    # Extract filter significance
    filter_significance = default_config.pop("filter_significance", 6.0)
    
    # Create birth chart
    birth_chart = BirthChart(birth_data)
    
    # Create transit calculator
    calculator = TransitCalculator(birth_chart, default_config)
    
    # Calculate transits
    return calculator.calculate_transits(period, filter_significance)

def get_transit_interpretation_url(transit_planet, aspect, natal_planet):
    """
    Generate the URL for the interpretation of a specific transit.
    
    Args:
        transit_planet: Transiting planet name
        aspect: Aspect name
        natal_planet: Natal planet name
        
    Returns:
        URL for the interpretation or None if not available
    """
    # Get the abbreviations for URL construction
    transit_abbr = PLANET_URL_ABBR.get(transit_planet)
    aspect_abbr = ASPECT_URL_ABBR.get(aspect.lower())
    natal_abbr = PLANET_URL_ABBR.get(natal_planet)
    
    # Return None if any part is missing
    if not all([transit_abbr, aspect_abbr, natal_abbr]):
        return None
    
    # Construct URL pattern
    return f"{ASTRO_X_FILES_BASE_URL}{transit_abbr}-{aspect_abbr}-{natal_abbr}.html"

def fetch_transit_interpretation(transit_planet, aspect, natal_planet):
    """
    Fetch interpretation for a specific transit from astrology-x-files.com.
    
    Args:
        transit_planet: Transiting planet name
        aspect: Aspect name
        natal_planet: Natal planet name
        
    Returns:
        Dictionary with interpretation text and source URL
    """
    # Generate a cache key
    cache_key = f"{transit_planet}_{aspect}_{natal_planet}"
    
    # Return cached interpretation if available
    if cache_key in TRANSIT_INTERPRETATION_CACHE:
        return TRANSIT_INTERPRETATION_CACHE[cache_key]
    
    # Get URL for this transit
    url = get_transit_interpretation_url(transit_planet, aspect, natal_planet)
    if not url:
        return {"interpretation": None, "source_url": None}
    
    try:
        # Make request to fetch the content
        response = requests.get(url, timeout=10)
        
        # Check if request was successful
        if response.status_code == 200:
            # Parse HTML content
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Get the main content div
            main_content = soup.find('div', id='maincontent')
            
            if main_content:
                # Extract paragraphs after the horizontal rule
                hr_tag = main_content.find('hr')
                if hr_tag:
                    # Get the first paragraph after the hr tag
                    current = hr_tag.next_sibling
                    first_paragraph = None
                    
                    while current and not first_paragraph:
                        if current.name == 'p':
                            # Skip the "More on determining planetary condition..." paragraph
                            text = current.get_text().strip()
                            if not text.startswith("More on determining planetary condition"):
                                first_paragraph = text
                        current = current.next_sibling
                    
                    if first_paragraph:
                        # Cache the interpretation
                        result = {
                            "interpretation": first_paragraph,
                            "source_url": url
                        }
                        TRANSIT_INTERPRETATION_CACHE[cache_key] = result
                        return result
    
    except Exception as e:
        # Log error but don't fail the whole process
        print(f"Error fetching transit interpretation: {str(e)}")
    
    # Return empty result if interpretation couldn't be fetched
    result = {"interpretation": None, "source_url": None}
    TRANSIT_INTERPRETATION_CACHE[cache_key] = result
    return result

def format_transit_output(transit):
    """Format transit for display"""
    retrograde = " R" if transit.get("is_retrograde", False) else ""
    applying = " (applying)" if transit.get("is_applying", False) else " (separating)"
    
    # Get interpretation if not already included
    if "interpretation" not in transit:
        interpretation_data = fetch_transit_interpretation(
            transit['transit_planet'], 
            transit['aspect'], 
            transit['natal_planet']
        )
        transit["interpretation"] = interpretation_data.get("interpretation")
        transit["interpretation_url"] = interpretation_data.get("source_url")
    
    # Format basic transit information
    basic_info = (f"{transit['date']} {transit['time']} - "
                 f"{transit['transit_planet_symbol']}{retrograde} {transit['aspect_symbol']} "
                 f"{transit['natal_planet_symbol']} {transit['natal_planet']} - "
                 f"{transit['position']} in {transit['house']} {applying}")
    
    # Include interpretation if available
    if transit.get("interpretation"):
        interpretation = transit["interpretation"]
        return f"{basic_info}\n\nInterpretation:\n{interpretation}"
    
    return basic_info

def simplified_transit_output(transit):
    """Simplified transit output format for comparison with other calculators"""
    # Get interpretation if not already included
    if "interpretation" not in transit:
        interpretation_data = fetch_transit_interpretation(
            transit['transit_planet'], 
            transit['aspect'], 
            transit['natal_planet']
        )
        transit["interpretation"] = interpretation_data.get("interpretation")
        transit["interpretation_url"] = interpretation_data.get("source_url")
    
    result = {
        "datetime": f"{transit['date']}T{transit['time']}",
        "transit": f"{transit['transit_planet']} {transit['aspect']} {transit['natal_planet']}"
    }
    
    # Include interpretation if available
    if transit.get("interpretation"):
        result["interpretation"] = transit["interpretation"]
        
    if transit.get("interpretation_url"):
        result["interpretation_url"] = transit["interpretation_url"]
        
    return result 