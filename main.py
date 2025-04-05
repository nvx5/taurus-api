#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import argparse
import datetime
import json
import os
from typing import Dict, List, Union, Optional, Any

# Import necessary functions from our modules
try:
    from astro_transits import get_transits, format_transit_output, simplified_transit_output, fetch_transit_interpretation
    from utils import parse_coordinates, get_timezone_from_coordinates, get_planet_symbol, get_aspect_symbol
    
    # Import AstroSeek functionality
    try:
        from astroseek_transits import get_astroseek_transits
        ASTROSEEK_AVAILABLE = True
    except ImportError:
        ASTROSEEK_AVAILABLE = False
    
    # Try to import TimezoneFinder
    try:
        from timezonefinder import TimezoneFinder
    except ImportError:
        # Mock TimezoneFinder for testing without the dependency
        class TimezoneFinder:
            def timezone_at(self, **kwargs):
                return "UTC"
except ImportError:
    # Mock implementations for testing without dependencies
    def get_transits(*args, **kwargs):
        return []
    
    def format_transit_output(*args, **kwargs):
        return []
    
    def simplified_transit_output(*args, **kwargs):
        return []
    
    def parse_coordinates(*args, **kwargs):
        return (0, 0)
    
    def get_timezone_from_coordinates(*args, **kwargs):
        return "UTC"
    
    def get_planet_symbol(*args, **kwargs):
        return "*"
    
    def get_aspect_symbol(*args, **kwargs):
        return "*"
    
    def get_astroseek_transits(*args, **kwargs):
        return []

    ASTROSEEK_AVAILABLE = False
    
    class TimezoneFinder:
        def timezone_at(self, **kwargs):
            return "UTC"

def handle_transit_request(request_data=None):
    """Handle transit calculation request"""
    if not request_data:
        raise ValueError("No request data provided")
        
    # Validate request data
    required_fields = ["birth", "period"]
    for field in required_fields:
        if field not in request_data:
            raise ValueError(f"Missing required field: {field}")
    
    # Validate birth data
    birth_data = request_data["birth"]
    required_birth_fields = ["date", "time", "coordinates"]
    for field in required_birth_fields:
        if field not in birth_data:
            raise ValueError(f"Missing required birth field: {field}")
    
    # Set configuration options
    current_coordinates = request_data.get("current_coordinates")
    house_system = request_data.get("house_system", "W")
    aspect_set = request_data.get("aspect_set", "major")
    time_step = request_data.get("time_step", 10)
    use_astroseek = request_data.get("use_astroseek", False)
    
    # Define the planet groups
    luminaries = ["Sun", "Moon"]
    
    # Generate transit report using the appropriate calculation function
    try:
        if use_astroseek and ASTROSEEK_AVAILABLE:
            print("Using AstroSeek for transit calculations...")
            report = get_astroseek_transits(
                birth_data, 
                request_data['period'],
                {
                    "house_system": house_system,
                    "aspect_set": aspect_set
                }
            )
        else:
            if use_astroseek and not ASTROSEEK_AVAILABLE:
                print("AstroSeek functionality not available, falling back to Swiss Ephemeris calculations...")
                
            report = get_transits(
                birth_data, 
                request_data['period'],
                {
                    "current_coordinates": current_coordinates,
                    "house_system": house_system,
                    "aspect_set": "major",  # Always use major aspects only
                    "time_step": time_step,
                    "luminaries": luminaries
                }
            )
        
        print(f"Successfully calculated {len(report)} transits")
    except Exception as e:
        raise RuntimeError(f"Error calculating transits: {e}")
    
    # Only include major aspects in the filtered transits
    major_aspects = ["conjunction", "opposition", "square", "trine", "sextile"]
    filtered_transits = [t for t in report if t.get('aspect', '').lower() in major_aspects]
    
    # Sort by date and time
    filtered_transits = sorted(filtered_transits, key=lambda t: (
        t['date'] if isinstance(t['date'], str) else t['date'].strftime("%Y-%m-%d"),
        t['time'] if isinstance(t['time'], str) else t['time']
    ))

    # Fetch interpretations for each transit
    try:
        print(f"Fetching interpretations for {len(filtered_transits)} transits...")
        for transit in filtered_transits:
            # Only fetch if interpretation is not already included
            if "interpretation" not in transit:
                interpretation_data = fetch_transit_interpretation(
                    transit['transit_planet'], 
                    transit['aspect'], 
                    transit['natal_planet']
                )
                transit["interpretation"] = interpretation_data.get("interpretation")
                transit["interpretation_url"] = interpretation_data.get("source_url")
        
        print("Interpretations fetched successfully")
    except Exception as e:
        print(f"Warning: Could not fetch interpretations: {e}")
    
    return filtered_transits

def print_transit_report(transits, show_parameters=False, request_data=None):
    """
    Print a formatted transit report.
    
    Args:
        transits: List of transit dictionaries to display
        show_parameters: Whether to show the parameters used
        request_data: The original request data
    """
    try:
        if not transits:
            print("No transits found for the specified period.")
            return
            
        if show_parameters and request_data:
            print("\n=== TRANSIT REPORT ===\n")
            print("PARAMETERS USED:")
            print(f"Birth Date: {request_data['birth']['date']}")
            print(f"Birth Time: {request_data['birth']['time']}")
            print(f"Birth Coordinates: {request_data['birth']['coordinates']}")
            print(f"House System: {request_data['birth'].get('house_system', 'W')}")
            
            # Period information
            if isinstance(request_data['period'], str):
                print(f"Period: {request_data['period']}")
            elif isinstance(request_data['period'], dict):
                if 'start' in request_data['period'] and 'end' in request_data['period']:
                    print(f"Period: {request_data['period']['start']} to {request_data['period']['end']}")
                elif 'year' in request_data['period'] and 'month' in request_data['period']:
                    print(f"Period: {request_data['period']['year']}-{request_data['period']['month']:02d}")
            
            if 'current_coordinates' in request_data:
                print(f"Current Coordinates: {request_data.get('current_coordinates')}")
            else:
                print("Current Coordinates: Same as birth")
                
            print(f"Aspect Set: {request_data.get('aspect_set', 'major')}")
            print(f"Calculation Method: {'AstroSeek' if request_data.get('use_astroseek', False) else 'Swiss Ephemeris'}")
            print(f"Total Transits Found: {len(transits)}")
            print("\n" + "-" * 70 + "\n")
        
        # Sort all transits by date
        sorted_transits = sorted(transits, key=lambda t: (
            t['date'] if isinstance(t['date'], str) else t['date'].strftime("%Y-%m-%d"),
            t['time'] if isinstance(t['time'], str) else t['time']
        ))
        
        for t in sorted_transits:
            # Format date
            if isinstance(t['date'], str):
                date_str = t['date']
                if len(date_str) > 10:  # If it includes time
                    date_str = date_str[:10]
            else:
                date_str = t['date'].strftime("%Y-%m-%d")
                
            # Extract month and day
            try:
                # Parse the date to get month name
                parsed_date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
                month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
                date_display = f"{month_names[parsed_date.month-1]} {parsed_date.day}"
            except Exception:
                # Fallback if parsing fails
                date_display = date_str
                
            # Format time
            if isinstance(t['time'], str):
                time_str = t['time']
            else:
                time_str = t['time'].strftime("%H:%M")
                
            # Get transit and natal planet symbols
            transit_planet = t.get('transit_planet', '')
            natal_planet = t.get('natal_planet', '')
            aspect = t.get('aspect', '')
            
            # Get symbols if available, otherwise use names
            transit_symbol = t.get('transit_planet_symbol', get_planet_symbol(transit_planet))
            natal_symbol = t.get('natal_planet_symbol', get_planet_symbol(natal_planet))
            aspect_symbol = t.get('aspect_symbol', get_aspect_symbol(aspect))
            
            # Format retrograde status
            is_retrograde = t.get('is_retrograde', False)
            retrograde_indicator = " R" if is_retrograde else ""
            
            # Format transit description with symbols
            transit_desc = f"{transit_symbol}{retrograde_indicator} {aspect_symbol} {natal_symbol}"
            
            # Get position information
            position = t.get('position', '')
            
            # Format house information
            house = t.get('house', '')
            if not house and 'house_number' in t:
                house = f"H{t['house_number']}"
                
            # Print the transit row in the exact requested format
            print(f"{date_display}, {time_str} | {transit_desc} | {position} | {house}")
            
            # If interpretation is available, print it without any prefix
            if t.get("interpretation"):
                # Clean up interpretation - remove house-specific sections
                interpretation = t["interpretation"]
                
                # Find the first paragraph
                first_para_end = interpretation.find("\n\n")
                if first_para_end > 0:
                    # Only keep the first paragraph (general interpretation)
                    interpretation = interpretation[:first_para_end].strip()
                
                # Print the interpretation without any prefix
                print(f"{interpretation}\n")
            else:
                # Print a placeholder message for missing interpretations
                print(f"No detailed interpretation available for this transit.\n")
                
    except Exception as e:
        # If an error occurs while printing report, show a simplified error message
        print(f"Error displaying transit report: {str(e)}")
        print("Simplified transit list:")
        for t in transits:
            try:
                transit_planet = t.get('transit_planet', 'Unknown')
                aspect = t.get('aspect', 'Unknown')
                natal_planet = t.get('natal_planet', 'Unknown')
                date = t.get('date', 'Unknown')
                time = t.get('time', 'Unknown')
                print(f"{date} {time}: {transit_planet} {aspect} {natal_planet}")
                if t.get("interpretation"):
                    # Just show the first sentence of interpretation
                    first_sentence = t['interpretation'].split('.')[0] + '.'
                    print(f"{first_sentence}")
            except Exception:
                # If we can't even print a simplified transit, skip it
                continue

def parse_command_line():
    """Parse command line arguments with full astrological parameters"""
    parser = argparse.ArgumentParser(description="Calculate astrological transits")
    
    # Birth information
    parser.add_argument("--birth-date", help="Birth date (YYYY-MM-DD)")
    parser.add_argument("--birth-time", help="Birth time (HH:MM)")
    parser.add_argument("--birth-coordinates", help="Birth coordinates in format '51n39 0w24'")
    
    # Period (target month or date range)
    parser.add_argument("--month", help="Target month (YYYY-MM)")
    parser.add_argument("--start-date", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="End date (YYYY-MM-DD)")
    
    # Optional parameters
    parser.add_argument("--current-coordinates", help="Current coordinates in format '51n39 0w24' (default: birth coordinates)")
    parser.add_argument("--house-system", choices=["W", "P", "K", "R", "C", "E", "T", "B", "O", "M"], default="W",
                       help="House system (W=Whole Sign, P=Placidus, K=Koch, R=Regiomontanus, C=Campanus, etc.)")
    parser.add_argument("--aspect-set", choices=["major", "all"], default="major",
                       help="Which aspects to include (default: major)")
    parser.add_argument("--time-step", type=int, default=10,
                       help="Time step in minutes for transit calculation (default: 10)")
    parser.add_argument("--input-file", help="JSON input file with transit request parameters")
    parser.add_argument("--output-file", help="Output file for transit results (JSON format)")
    
    # AstroSeek option
    parser.add_argument("--astroseek", action="store_true", 
                        help="Use AstroSeek web scraping for transit calculation instead of Swiss Ephemeris")
    
    return parser.parse_args()

def main():
    """Main entry point for the application"""
    try:
        # Parse command line arguments
        args = parse_command_line()
        
        # Check if we have any arguments at all
        if len(sys.argv) <= 1:
            print("""
Taurus Astrology Transit Calculator
            
Usage examples:
  python main.py --birth-date 1990-01-15 --birth-time 14:30 --birth-coordinates "51n39 0w24" --month 2023-11
  python main.py --birth-date 1988-06-20 --birth-time 08:15 --birth-coordinates "51n30 0w10" --start-date 2024-01-01 --end-date 2024-12-31
  python main.py --birth-date 1990-01-01 --birth-time 12:00 --birth-coordinates "51n30 0w10" --month 2024-08 --astroseek
  
For all available options:
  python main.py --help
            """)
            return
        
        print("Command line arguments parsed successfully")
        
        # Check if input file is provided
        if args.input_file:
            try:
                with open(args.input_file, 'r') as f:
                    request_data = json.load(f)
                print(f"Loaded request data from {args.input_file}")
            except FileNotFoundError:
                print(f"Error: Input file '{args.input_file}' not found")
                return
            except json.JSONDecodeError:
                print(f"Error: Input file '{args.input_file}' contains invalid JSON")
                return
            except Exception as e:
                print(f"Error loading input file: {e}")
                return
        else:
            # Construct request data from command line arguments
            request_data = {}
            
            # Birth data
            if args.birth_date and args.birth_time and args.birth_coordinates:
                birth_data = {
                    "date": args.birth_date,
                    "time": args.birth_time,
                    "coordinates": args.birth_coordinates
                }
                
                # Set house system
                birth_data["house_system"] = args.house_system
                
                request_data["birth"] = birth_data
                print("Birth data processed")
            else:
                print("Error: Birth date, time, and coordinates are required")
                return
            
            # Period data
            if args.month:
                try:
                    # Validate month format
                    datetime.datetime.strptime(args.month, "%Y-%m")
                    request_data["period"] = args.month
                    print(f"Using month: {args.month}")
                except ValueError:
                    print("Error: Month must be in YYYY-MM format (e.g., 2023-11)")
                    return
            elif args.start_date and args.end_date:
                try:
                    # Validate date formats
                    datetime.datetime.strptime(args.start_date, "%Y-%m-%d")
                    datetime.datetime.strptime(args.end_date, "%Y-%m-%d")
                    
                    request_data["period"] = {
                        "start": args.start_date,
                        "end": args.end_date
                    }
                    print(f"Using date range: {args.start_date} to {args.end_date}")
                except ValueError:
                    print("Error: Dates must be in YYYY-MM-DD format (e.g., 2023-11-01)")
                    return
            else:
                print("Error: Either month or start/end date must be provided")
                return
            
            # Other parameters
            if args.current_coordinates:
                request_data["current_coordinates"] = args.current_coordinates
                print(f"Using current coordinates: {args.current_coordinates}")
            
            # Add AstroSeek option
            if args.astroseek:
                request_data["use_astroseek"] = True
                print("Using AstroSeek for transit calculations")
                if not ASTROSEEK_AVAILABLE:
                    print("Warning: AstroSeek module not available, will fall back to Swiss Ephemeris")
            
            # Add additional configuration
            request_data["aspect_set"] = args.aspect_set
            request_data["time_step"] = args.time_step
            
            print("Request data constructed from command line arguments")
        
        # Calculate transits
        print("Calculating transits...")
        transits = handle_transit_request(request_data)
        
        # Output results
        if args.output_file:
            # Write to output file in JSON format
            try:
                # Create a cleaned version of the transits for output
                clean_transits = []
                for transit in transits:
                    # Clean up interpretation if present
                    interpretation = None
                    if "interpretation" in transit and transit["interpretation"]:
                        # Only keep the first paragraph
                        interpretation_text = transit["interpretation"]
                        first_para_end = interpretation_text.find("\n\n")
                        if first_para_end > 0:
                            interpretation = interpretation_text[:first_para_end].strip()
                        else:
                            interpretation = interpretation_text
                    
                    # Format date string
                    if isinstance(transit['date'], str):
                        date_str = transit['date']
                    else:
                        date_str = transit['date'].strftime("%Y-%m-%d")
                        
                    # Extract month and day
                    try:
                        # Parse the date to get month name
                        parsed_date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
                        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
                        date_display = f"{month_names[parsed_date.month-1]} {parsed_date.day}"
                    except Exception:
                        # Fallback if parsing fails
                        date_display = date_str
                        
                    # Format time
                    if isinstance(transit['time'], str):
                        time_str = transit['time']
                    else:
                        time_str = transit['time'].strftime("%H:%M")
                    
                    # Create a clean transit object with only necessary fields
                    clean_transit = {
                        "date_display": f"{date_display}, {time_str}",
                        "transit_planet": transit.get('transit_planet', ''),
                        "transit_planet_symbol": transit.get('transit_planet_symbol', ''),
                        "is_retrograde": transit.get('is_retrograde', False),
                        "aspect": transit.get('aspect', ''),
                        "aspect_symbol": transit.get('aspect_symbol', ''),
                        "natal_planet": transit.get('natal_planet', ''),
                        "natal_planet_symbol": transit.get('natal_planet_symbol', ''),
                        "position": transit.get('position', ''),
                        "house": transit.get('house', ''),
                        "interpretation": interpretation if interpretation else "No detailed interpretation available for this transit."
                    }
                    clean_transits.append(clean_transit)
                
                # Write the clean transits to the output file
                with open(args.output_file, 'w') as f:
                    json.dump(clean_transits, f, indent=2, default=str)
                print(f"Transit data written to {args.output_file}")
            except Exception as e:
                print(f"Error writing to output file: {e}")
        else:
            # Show an example of the JSON output format
            print("\nJSON OUTPUT EXAMPLE:")
            if transits:
                # Show just the first transit as an example
                example_transit = transits[0]
                
                # Clean up interpretation if present
                interpretation = None
                if "interpretation" in example_transit and example_transit["interpretation"]:
                    # Only keep the first paragraph
                    interpretation_text = example_transit["interpretation"]
                    first_para_end = interpretation_text.find("\n\n")
                    if first_para_end > 0:
                        interpretation = interpretation_text[:first_para_end].strip()
                    else:
                        interpretation = interpretation_text
                
                # Format date string
                if isinstance(example_transit['date'], str):
                    date_str = example_transit['date']
                else:
                    date_str = example_transit['date'].strftime("%Y-%m-%d")
                    
                # Extract month and day
                try:
                    # Parse the date to get month name
                    parsed_date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
                    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
                    date_display = f"{month_names[parsed_date.month-1]} {parsed_date.day}"
                except Exception:
                    # Fallback if parsing fails
                    date_display = date_str
                    
                # Format time
                if isinstance(example_transit['time'], str):
                    time_str = example_transit['time']
                else:
                    time_str = example_transit['time'].strftime("%H:%M")
                
                # Create a clean transit object with only necessary fields
                clean_transit = {
                    "date_display": f"{date_display}, {time_str}",
                    "transit_planet": example_transit.get('transit_planet', ''),
                    "transit_planet_symbol": example_transit.get('transit_planet_symbol', ''),
                    "is_retrograde": example_transit.get('is_retrograde', False),
                    "aspect": example_transit.get('aspect', ''),
                    "aspect_symbol": example_transit.get('aspect_symbol', ''),
                    "natal_planet": example_transit.get('natal_planet', ''),
                    "natal_planet_symbol": example_transit.get('natal_planet_symbol', ''),
                    "position": example_transit.get('position', ''),
                    "house": example_transit.get('house', ''),
                    "interpretation": interpretation if interpretation else "No detailed interpretation available for this transit."
                }
                
                # Print the example
                print(json.dumps(clean_transit, indent=2, default=str))
            else:
                print("No transits found to display JSON example.")
        
        # Print transit report
        print_transit_report(transits, True, request_data)
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()  # Print the full stack trace for debugging

if __name__ == "__main__":
    main() 