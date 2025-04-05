#!/usr/bin/env python
"""
Taurus Transit API Test Script

This script tests the Taurus Transit API by sending requests for both
Swiss Ephemeris and AstroSeek calculation methods.
"""

import argparse
import json
import requests
from datetime import datetime

def test_api(base_url, birth_date, birth_time, birth_coordinates, month):
    """
    Test the Taurus Transit API with both calculation methods
    """
    print("\n====== Testing Taurus Transit API ======\n")
    print(f"Base URL: {base_url}")
    print(f"Birth Date: {birth_date}")
    print(f"Birth Time: {birth_time}")
    print(f"Birth Coordinates: {birth_coordinates}")
    print(f"Target Month: {month}")
    print("\n--------------------------------------\n")
    
    # Test Swiss Ephemeris calculation
    print("Testing Swiss Ephemeris calculation...")
    swiss_url = f"{base_url}/transits"
    params = {
        "birth_date": birth_date,
        "birth_time": birth_time,
        "birth_coordinates": birth_coordinates,
        "month": month
    }
    
    try:
        response = requests.get(swiss_url, params=params)
        response.raise_for_status()
        data = response.json()
        
        print(f"Success! Found {data.get('total_transits', 0)} transits.")
        print(f"Status code: {response.status_code}")
        print(f"Response time: {response.elapsed.total_seconds():.2f} seconds")
        
        # Save response to file
        filename = f"swiss_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Response saved to {filename}")
        
    except requests.exceptions.RequestException as e:
        print(f"Error with Swiss Ephemeris test: {e}")
    
    print("\n--------------------------------------\n")
    
    # Test AstroSeek calculation
    print("Testing AstroSeek calculation...")
    astroseek_url = f"{base_url}/transits"
    params = {
        "birth_date": birth_date,
        "birth_time": birth_time,
        "birth_coordinates": birth_coordinates,
        "month": month,
        "astroseek": "1"
    }
    
    try:
        print("This request may take longer due to web scraping...")
        response = requests.get(astroseek_url, params=params)
        response.raise_for_status()
        data = response.json()
        
        print(f"Success! Found {data.get('total_transits', 0)} transits.")
        print(f"Status code: {response.status_code}")
        print(f"Response time: {response.elapsed.total_seconds():.2f} seconds")
        
        # Save response to file
        filename = f"astroseek_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Response saved to {filename}")
        
    except requests.exceptions.RequestException as e:
        print(f"Error with AstroSeek test: {e}")
    
    print("\n====== Test Complete ======\n")

def main():
    parser = argparse.ArgumentParser(description='Test the Taurus Transit API')
    parser.add_argument('--url', default='http://localhost:5000', help='Base URL of the API')
    parser.add_argument('--birth-date', default='1990-01-01', help='Birth date (YYYY-MM-DD)')
    parser.add_argument('--birth-time', default='12:00', help='Birth time (HH:MM)')
    parser.add_argument('--birth-coordinates', default='51n30 0w10', help='Birth coordinates (51n30 0w10)')
    
    # Get current month in YYYY-MM format
    current_month = datetime.now().strftime('%Y-%m')
    parser.add_argument('--month', default=current_month, help='Target month (YYYY-MM)')
    
    args = parser.parse_args()
    
    test_api(
        args.url, 
        args.birth_date, 
        args.birth_time, 
        args.birth_coordinates, 
        args.month
    )

if __name__ == "__main__":
    main() 