from flask import render_template, request, redirect, url_for
from app import app
import configparser
import ast

config = configparser.ConfigParser()
config.read('config.ini')

@app.route('/', methods=['GET', 'POST'])
def index():
    # Parse the classes_dict from the config file
    classes_dict_str = config.get('Classes to Schedule by Day', 'classes_dict')
    classes_dict = ast.literal_eval(classes_dict_str)

    if request.method == 'POST':
        day = request.form['day']
        time = request.form['time']
        class_name = request.form['class_name']
        action = request.form['action']

        if action == 'add':
            if day not in classes_dict:
                classes_dict[day] = {}
            classes_dict[day][time] = class_name
        elif action == 'delete':
            if day in classes_dict and time in classes_dict[day]:
                del classes_dict[day][time]

        # Update the config file only for the relevant section
        config['Classes to Schedule by Day']['classes_dict'] = str(classes_dict)
        with open('config.ini', 'w') as configfile:
            config.write(configfile)

        return redirect(url_for('index'))

    return render_template('index.html', classes_dict=classes_dict)
