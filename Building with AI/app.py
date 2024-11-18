from flask import Flask, render_template, jsonify, request
import google.generativeai as genai
import os
import json
from werkzeug.utils import secure_filename
from colorthief import ColorThief 
import webcolors

# Initialize Flask app
app = Flask(__name__, static_folder='static')

# Configure Gemini API key
API_KEY = os.environ.get("GENAI_API_KEY")
if not API_KEY:
    raise EnvironmentError("GENAI_API_KEY environment variable is not set.")
genai.configure(api_key=API_KEY)

# Configure upload folder and allowed extensions
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Mock knowledge base for building accessibility data
knowledge_base = {
    "McClain Hall": {
        "elevators": "Yes, located near the west entrance.",
        "ramps": "Yes, at the north entrance.",
        "automatic_doors": "Yes, at the main entrance.",
        "restrooms": "Accessible restrooms are available on each floor."
    },
    "Other Hall": {
        "elevators": "No",
        "ramps": "Yes, located at the east entrance.",
        "automatic_doors": "No",
        "restrooms": "Accessible restrooms are available on the ground floor."
    }
    
}

# Helper function to get data from knowledge base
def get_accessibility_data(building_name):
    return knowledge_base.get(building_name)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Route for the root URL
@app.route('/')
def home():
    return render_template('index.html')  # Assuming index.html is your main template

@app.route('/check-accessibility', methods=['POST'])
def check_accessibility():
    try:
        data = request.get_json()
        building_name = data.get('buildingName')

        if not building_name:
            return jsonify({"error": "Building name is required"}), 400

        print(f"Received data for building: {building_name}")

        building_data = get_accessibility_data(building_name)
        if building_data:
            return jsonify({"accessibilityInfo": building_data}), 200

        prompt = (
            f"Use this information to answer about the specific {building_name} building your asked only.McClain Hall at Truman State University has accessibility features including ramps at multiple entrances, elevators to access different floors, and automatic doors at many entrances, including the main entrances."
            f"Barnett Hall at Truman State University has similar accessibility features, such as ramps, elevators, and automatic doors at multiple entrances. The main entrance to Barnett Hall is located on Normal Street."
            f"Magruder Hall at Truman State University is accessible to people with disabilities. It has ramps, elevators, and automatic doors to help people get around easily. The best street to access Magruder Hall is Pershing Street."
            
    
        )

        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)

        print(f"Model response: {response.text}")
        return jsonify({"accessibilityInfo": response.text}), 200

    except Exception as e:
        print(f"Error occurred: {e}")
        return jsonify({"error": "An error occurred while processing your request"}), 500
def get_color_name(rgb_color):
    """Convert RGB to the closest color name."""
    try:
        # Try to get the exact color name
        return webcolors.rgb_to_name(rgb_color)
    except ValueError:
        # Find the closest color name if exact match isn't available
        closest_color = webcolors.rgb_to_name(webcolors.css3_hex_to_names, webcolors.hex_to_rgb(webcolors.rgb_to_hex(rgb_color)))
        return closest_color

    #color API
@app.route('/upload-image', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        image_url = f"/{file_path}"

        # Use ColorThief to extract the dominant color from the image
        color_thief = ColorThief(file_path)
        dominant_color = color_thief.get_color(quality=1)  # Extract dominant color
        palette = color_thief.get_palette(color_count=6)  # Get a palette of 6 colors
        
        print(f"Image saved at {file_path}")
        print(f"Dominant color: {dominant_color}")
    


        return jsonify({
            "imageUrl": image_url,
            "dominantColor": f"rgb{dominant_color}",  # Returning dominant color as an RGB value
            "colorPalette": [f"rgb{color}" for color in palette]  # Return color palette as RGB values
        }), 200

    return jsonify({"error": "File type not allowed"}), 400
#Best Building
knowledge_base = {
    "Truman State University": {
        "best_building": "Pickler Memorial",
        "details": "McClain Hall has elevators, ramps, automatic doors, and accessible restrooms on all floors."
    },
    "University of Iowa": {
        "best_building": "Iowa Memorial Union",
        "details": "The Iowa Memorial Union is equipped with wheelchair ramps, elevators, and accessible restrooms."
    },
    "Harvard University": {
        "best_building": "Science Center",
        "details": "The Sciene Center is equipped with wheelchair ramps, elevators, and accessible restrooms."
}
}

def get_accessibility_info_from_knowledge_base(university_name):
    """Fetches building accessibility information from the knowledge base."""
    return knowledge_base.get(university_name)

def generate_accessibility_info(university_name):
    """Generates building accessibility information using the Gemini API."""
    prompt = (
        f"Provide the name of the most accessible building for people with disabilities at {university_name}, "
        "including information on ramps, elevators, automatic doors, and accessible restrooms."
    )
    try:
        # Query the Gemini model
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Error generating response from Gemini: {e}")
        return None

@app.route('/accessible-building', methods=['POST'])
def accessible_building():
    try:
        data = request.get_json()
        university_name = data.get('universityName')

        if not university_name:
            return jsonify({"error": "University name is required."}), 400

        # Check knowledge base first
        building_info = get_accessibility_info_from_knowledge_base(university_name)
        if building_info:
            return jsonify({
                "university": university_name,
                "bestBuilding": building_info["best_building"],
                "details": building_info["details"]
            }), 200

        # Use Gemini API if knowledge base lacks data
        generated_info = generate_accessibility_info(university_name)
        if generated_info:
            return jsonify({
                "university": university_name,
                "bestBuilding": generated_info
            }), 200
        else:
            return jsonify({"error": "Could not retrieve accessibility information for the university."}), 500

    except Exception as e:
        print(f"Error occurred: {e}")
        return jsonify({"error": "An error occurred while processing your request."}), 500




if __name__ == '__main__':
    app.run(port=5001,debug=True)
