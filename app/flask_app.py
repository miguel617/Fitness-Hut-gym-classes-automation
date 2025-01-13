from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import configparser
import ast

app = Flask(__name__)
CORS(app)

CONFIG_FILE = 'config.ini'

def read_config():
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    classes_dict = ast.literal_eval(config['Classes to Schedule by Day']['classes_dict'])
    return classes_dict

def write_config(classes_dict):
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    config['Classes to Schedule by Day']['classes_dict'] = str(classes_dict)
    with open(CONFIG_FILE, 'w') as f:
        config.write(f)

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

# Remove the if __name__ == '__main__' block