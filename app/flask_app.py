from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import configparser
import ast
import json
import os
import subprocess

app = Flask(__name__)
CORS(app)

# Get the absolute path to the directory where the script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, 'config.ini')
DAYS_ORDER = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

def read_config():
    config = configparser.ConfigParser()

    # Check if the config file exists, create it with default data if it doesn't
    if not os.path.exists(CONFIG_FILE):
        default_schedule = {
            'Monday': {'13:15': 'Body Pump', '18:15': 'Body Attack'},
            'Tuesday': {'13:15': 'Body Attack'},
            'Wednesday': {'18:30': 'Body Pump'},
            'Thursday': {'13:15': 'Body Pump'},
            'Friday': {'18:15': 'Body Pump', '19:15': 'Body Attack'},
            'Saturday': {},
            'Sunday': {}
        }
        config['Classes to Schedule by Day'] = {'classes_dict': str(default_schedule)}
        with open(CONFIG_FILE, 'w') as f:
            config.write(f)

    try:
        config.read(CONFIG_FILE)
        classes_dict = ast.literal_eval(config['Classes to Schedule by Day']['classes_dict'])
        # Order the dictionary according to DAYS_ORDER
        ordered_classes_dict = {day: classes_dict.get(day, {}) for day in DAYS_ORDER}
        return ordered_classes_dict
    except Exception as e:
        print(f"Error reading config file: {e}")
        return {day: {} for day in DAYS_ORDER}

def write_config(classes_dict):
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)

    # Order the dictionary before writing
    ordered_classes_dict = {day: classes_dict.get(day, {}) for day in DAYS_ORDER}

    config['Classes to Schedule by Day'] = {'classes_dict': str(ordered_classes_dict)}
    with open(CONFIG_FILE, 'w') as f:
        config.write(f)

    # Run scheduler_update.py after saving config.ini
    try:
        subprocess.run(['python', os.path.join(BASE_DIR, 'scheduler_update.py')], check=True)
        print("scheduler_update.py executed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error running scheduler_update.py: {e}")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/schedule', methods=['GET'])
def get_schedule():
    return jsonify(read_config())

@app.route('/api/schedule', methods=['POST'])
def update_schedule():
    new_schedule = request.json
    write_config(new_schedule)
    return jsonify({"status": "success"})

# In a production environment, you would not use `app.run()` but instead
# configure a WSGI server (like Gunicorn or uWSGI) to run your app.
# if __name__ == '__main__':
#     app.run(debug=True)  # Do NOT use debug=True in production
