#!/usr/bin/env python
# coding: utf-8

import os
import subprocess
import configparser
from datetime import datetime, timedelta
import pytz
import time as time_py

def main():
    time_py.sleep(1)

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    CONFIG_FILE = os.path.join(BASE_DIR, 'config.ini')

    # Define important parameters - on the config.ini file and parse it
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)

    classes_dict = eval(config['Classes to Schedule by Day']['classes_dict'])
    classes_dict = {key: value for key, value in classes_dict.items() if value}  # Remove empty days

    delay_hours = int(config['Optional Config Parameters']['delay_hours'])

    def calculate_cron_expression(target_time_str, target_day, target_class, offset_hours, timezone_str):
        # Define weekdays mapping
        days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

        # Check if target_day is valid
        if target_day not in days_of_week:
            raise ValueError(f"Invalid day of the week: {target_day}. Must be one of {days_of_week}")

        # Parse the target time
        target_time = datetime.strptime(target_time_str, '%H:%M').time()

        # Load the timezone
        local_tz = pytz.timezone(timezone_str)

        # Get the current date and time in the local timezone
        now = datetime.now(local_tz)

        # Determine the weekday number for the target day (0=Monday, 6=Sunday)
        target_day_index = days_of_week.index(target_day)

        # Find the next occurrence of the target day
        days_until_target = (target_day_index - now.weekday()) % 7
        if days_until_target == 0 and now.time() > target_time:
            days_until_target += 7

        target_datetime_local = now + timedelta(days=days_until_target)
        target_datetime_local = target_datetime_local.replace(hour=target_time.hour, minute=target_time.minute, second=0, microsecond=0)

        # Subtract the offset
        target_datetime_local -= timedelta(hours=offset_hours)

        # Convert to UTC
        target_datetime_utc = target_datetime_local.astimezone(local_tz)

        # Format the cron expression
        cron_minute = target_datetime_utc.minute
        cron_hour = target_datetime_utc.hour
        cron_day_of_month = '*'
        cron_month = '*'
        cron_day_of_week = (target_datetime_utc.weekday() + 1) % 7  # 1=Monday, 0=Sunday - cron expression is different from the python function weekday()

        # Return the cron expression
        return f'- cron: "{cron_minute} {cron_hour} {cron_day_of_month} {cron_month} {cron_day_of_week}"    # Runs {delay_hours} hours less (UTC time) to schedule {target_day} : {target_time_str} - {target_class}'

    cron_expressions = []

    offset_hours = delay_hours  # Offset in hours
    timezone_str = 'Portugal'  # Local timezone

    # Get all iterations and apply the function
    for day, activities in classes_dict.items():
        for time, activity in activities.items():
            cron_expression = calculate_cron_expression(time, day, activity, offset_hours, timezone_str)
            cron_expressions.append(cron_expression)

    ############### GitHub cloning and push commits ####################

    def clone_repo(repo_url, clone_dir):
        if not os.path.exists(clone_dir):
            print(f"Cloning repository into: {clone_dir}")
            subprocess.run(['git', 'clone', repo_url, clone_dir])
        else:
            print(f"Repository already exists at: {clone_dir}")

    def commit_push(commit_message, repo_dir):
        # Add and commit the changes
        subprocess.run(['git', 'add', '.'], cwd=repo_dir)
        subprocess.run(['git', 'commit', '-m', commit_message], cwd=repo_dir)

        # Push the changes back to GitHub
        subprocess.run(['git', 'push'], cwd=repo_dir)

    github_token = os.getenv('GH_TOKEN')
    print(github_token)
    print("github token =", github_token)
    repo_url = config['GitHub Config']['github_repo']

    # Use PAT for authentication
    if github_token:
        repo_url_with_pat = repo_url.replace("https://", f"https://{github_token}@")
    else:
        print("Error: GitHub token not provided.")
        return

    clone_dir = os.path.join(BASE_DIR, 'repo')  # Clone into a specific directory
    file_path = os.path.join(clone_dir, '.github/workflows/schedule.yml')  # Use absolute path

    # Clone the repository
    clone_repo(repo_url_with_pat, clone_dir)

    # Debug: Check if the file exists
    print(f"Looking for file at: {file_path}")
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return
    else:
        print("File found!")

    # Retrieve and modify the file
    def read_file(file_path):
        with open(file_path, 'r') as file:
            content = file.read()
            return content

    def modify_file(file_path, new_content):
        with open(file_path, 'w') as file:  # 'w' mode to overwrite
            file.write(new_content)

    # Read the YML file
    content = read_file(file_path)

    def change_cron_lines(multiline_string, cron_lines_to_add):
        lines = multiline_string.splitlines()  # Split the input string into individual lines
        output_lines = []

        for line in lines:
            if not line.strip().startswith('- cron:'):
                output_lines.append(line)  # Add each line to the output list except the previous cron lines
            if line.strip() == 'schedule:':  # After finding the 'schedule:' line, add the cron lines
                for cron_line in cron_lines_to_add:
                    output_lines.append("    " + cron_line)

        updated_multi_line_string = '\n'.join(output_lines)
        return updated_multi_line_string

    # Replace the cron expression in the file content
    new_content = change_cron_lines(content, cron_expressions)

    # Update the file on GitHub and commit and push all changed files
    commit_message = 'Updated schedule.yml, scheduler_update.py, and config.ini files'
    print(commit_message)

    # Modify the schedule.yml file
    modify_file(file_path, new_content)

    # Copy scheduler_update.py and config.ini to the repository directory
    scheduler_update_src = os.path.join(BASE_DIR, 'scheduler_update.py')
    config_ini_src = os.path.join(BASE_DIR, 'config.ini')

    scheduler_update_dst = os.path.join(clone_dir, 'scheduler_update.py')
    config_ini_dst = os.path.join(clone_dir, 'config.ini')

    # Copy files
    subprocess.run(['cp', scheduler_update_src, scheduler_update_dst])
    subprocess.run(['cp', config_ini_src, config_ini_dst])

    # Commit and push changes
    commit_push(commit_message, repo_dir=clone_dir)

if __name__ == "__main__":
    main()