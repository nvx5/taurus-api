from flask import Flask, request, jsonify
import datetime
import os
import json
import logging
from flask_cors import CORS
from astro_transits import get_transits
from astroseek_transits import fetch_transits_from_astroseek

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Enable CORS for all routes
CORS(app)

# Error handling middleware
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Resource not found"}), 404

@app.errorhandler(500)
def server_error(error):
    logger.error(f"Server error: {error}")
    return jsonify({"error": "Internal server error"}), 500

@app.errorhandler(400)
def bad_request(error):
    return jsonify({"error": "Bad request"}), 400

# Health check endpoint for Azure monitoring
@app.route('/health')
def health_check():
    return jsonify({"status": "healthy", "version": "1.0.0"})

@app.route('/')
def index():
    """API documentation homepage"""
    return """
    <html>
    <head>
        <title>Taurus Transit API</title>
        <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; }
            h1 { color: #4a4a4a; }
            h2 { color: #5a5a5a; margin-top: 30px; }
            ul { padding-left: 20px; }
            li { margin-bottom: 10px; }
            code { background-color: #f4f4f4; padding: 2px 5px; border-radius: 3px; font-family: monospace; }
        </style>
    </head>
    <body>
        <h1>Taurus Astrological Transit API</h1>
        <p>Welcome to the Taurus API for calculating astrological transits.</p>
        <h2>Available Endpoints:</h2>
        <ul>
            <li>
                <b>GET /transits</b> - Calculate transits based on query parameters
                <br>Required parameters:
                <ul>
                    <li>birth_date - Birth date in YYYY-MM-DD format</li>
                    <li>birth_time - Birth time in HH:MM format</li>
                    <li>birth_coordinates - Birth coordinates in "51n39 0w24" format</li>
                    <li>month - Target month in YYYY-MM format</li>
                </ul>
                <br>Optional parameters:
                <ul>
                    <li>current_coordinates - Current coordinates in "51n39 0w24" format (defaults to birth coordinates)</li>
                    <li>house_system - House system to use (W for Whole Sign, P for Placidus, defaults to W)</li>
                    <li>astroseek - Set to "1" to use AstroSeek calculation (defaults to Swiss Ephemeris)</li>
                    <li>aspect_set - Set of aspects to use (major, minor, all; defaults to major)</li>
                </ul>
            </li>
            <li>
                <b>POST /transits</b> - Calculate transits with JSON payload
                <br>See documentation for request format
            </li>
            <li>
                <b>GET /health</b> - Health check endpoint for monitoring
            </li>
        </ul>
        <h2>Example Request:</h2>
        <code>GET /transits?birth_date=1990-01-01&birth_time=12:00&birth_coordinates=51n30%200w10&month=2024-09</code>
    </body>
    </html>
    """

@app.route('/transits', methods=['GET', 'POST'])
def calculate_transits():
    """Calculate transits based on input parameters"""
    try:
        logger.info(f"Received transit calculation request via {request.method}")
        
        # Process request parameters
        if request.method == 'POST':
            # Handle JSON payload
            params = request.json
            logger.info("Processing JSON payload")
        else:
            # Handle query parameters
            params = request.args.to_dict()
            logger.info("Processing query parameters")
        
        # Required parameters
        birth_date = params.get('birth_date')
        birth_time = params.get('birth_time')
        birth_coordinates = params.get('birth_coordinates')
        month = params.get('month')
        
        # Validate required parameters
        if not all([birth_date, birth_time, birth_coordinates, month]):
            missing = [p for p in ['birth_date', 'birth_time', 'birth_coordinates', 'month'] 
                      if params.get(p) is None]
            logger.warning(f"Missing required parameters: {missing}")
            return jsonify({
                "error": "Missing required parameters",
                "required": ["birth_date", "birth_time", "birth_coordinates", "month"],
                "missing": missing
            }), 400
        
        # Optional parameters
        current_coordinates = params.get('current_coordinates', birth_coordinates)
        house_system = params.get('house_system', 'W')
        use_astroseek = params.get('astroseek', '0') == '1'
        aspect_set = params.get('aspect_set', 'major')
        
        logger.info(f"Processing request for birth date: {birth_date}, month: {month}, "
                   f"using {'AstroSeek' if use_astroseek else 'Swiss Ephemeris'}")
        
        # Construct birth data
        birth_data = {
            "date": birth_date,
            "time": birth_time,
            "coordinates": birth_coordinates,
            "house_system": house_system
        }
        
        # Configure calculation options
        config = {
            "current_coordinates": current_coordinates,
            "aspect_set": aspect_set,
            "house_system": house_system
        }
        
        # Calculate transits
        if use_astroseek:
            # Use AstroSeek calculation
            logger.info("Using AstroSeek for transit calculation")
            transits = fetch_transits_from_astroseek(birth_data, month)
        else:
            # Use Swiss Ephemeris calculation
            logger.info("Using Swiss Ephemeris for transit calculation")
            transits = get_transits(birth_data, month, config)
        
        logger.info(f"Found {len(transits)} transits")
        
        # Clean up the transits for output
        clean_transits = []
        for transit in transits:
            # Format date display
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
            except Exception as e:
                # Fallback if parsing fails
                logger.warning(f"Date parsing error: {e}")
                date_display = date_str
                
            # Format time
            if isinstance(transit['time'], str):
                time_str = transit['time']
            else:
                time_str = transit['time'].strftime("%H:%M")
            
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
            
            # Create a clean transit object with only necessary fields
            clean_transit = {
                "date_display": f"{date_display}, {time_str}",
                "date": date_str,
                "time": time_str,
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
        
        # Add report parameters
        result = {
            "parameters": {
                "birth_date": birth_date,
                "birth_time": birth_time,
                "birth_coordinates": birth_coordinates,
                "house_system": house_system,
                "period": month,
                "current_coordinates": current_coordinates,
                "aspect_set": aspect_set,
                "calculation_method": "AstroSeek" if use_astroseek else "Swiss Ephemeris"
            },
            "total_transits": len(clean_transits),
            "transits": clean_transits
        }
        
        logger.info("Returning transit calculation result")
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error calculating transits: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Get port from environment variable for Azure deployment
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting Taurus Transit API server on port {port}, debug mode: {debug_mode}")
    app.run(host='0.0.0.0', port=port, debug=debug_mode) 