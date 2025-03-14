#!/usr/bin/env python
# coding: utf-8

import time
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import os
import configparser
import chromedriver_autoinstaller

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import WebDriverException, StaleElementReferenceException

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from main_init import initial_exec


# define important parameters - on the config.ini file and parse it
config = configparser.ConfigParser()
config.read('config.ini')

# usually these 3 are static

#chromedriver = config['Optional Config Parameters']['chromedriver']
gui_display = eval(config['Optional Config Parameters']['gui_display']) # to show or not the GUI - True is only useful when testing and to deploy outside my PC, it had to be False
website = config['Optional Config Parameters']['website']
delay_hours = int(config['Optional Config Parameters']['delay_hours']) # 48 hours now but it might differ

user = os.getenv('FH_USERNAME')  # access the env variable
pwd = os.getenv('FH_PWD')  # access the env variable

# run the function on main_init.py and assign 2 variables to continue
driver, wait = initial_exec(user, pwd, website, gui_display)

# retrieve dictionary of days to schedule - we can change this always

classes_dict = eval(config['Classes to Schedule by Day']['classes_dict'])


# now we want to know today's date so that we can book tomorrow's class - 48 hours ahead 
# This because here in config.ini we define Lisbon Time which is UTC, vs UTC scheduler in the app where we will deploy

#current_time = datetime(2024, 9, 2, 2, 44, 46, 553971)
current_time = datetime.now()
print(current_time)

today = current_time.strftime("%Y-%m-%d")
day_of_week_today = current_time.strftime('%A')

tomorrow = (current_time + timedelta(hours=delay_hours)).strftime("%Y-%m-%d")
day_of_week_tomorrow = (current_time + timedelta(hours=delay_hours)).strftime('%A')

#tomorrow = '2024-08-16'
#day_of_week_tomorrow = 'Friday'
#classes_of_day = ['19:30', '21:30']

# click on tomorrow's day first

day_select = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-cy="booking-swiper-date-{}"]'.format(tomorrow))))
day_select.click()

############################################### [IMPORTANT] ####################################################
#### We will find how many classes there are to book within the 48 hour timeframe (only in one day) because github actions, often gets the job delayed so, probably, the booking will occur less than 48 before

# to run only this script once per schedule, so in fact, the list will be only 1 schedule - 48 hours after
def find_classes_in_next_delay_hours(classes_dict, delay_hours):
    # Get the current datetime
    now = datetime.now()
    
    # Calculate the datetime 48 hours from now
    time_delay_hours_later = now + timedelta(hours=delay_hours)
    
    # Days of the week to map string to weekday index
    days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    # Determine tomorrow's day name
    days_lag = delay_hours//24
    tomorrow = days_of_week[(now.weekday() + days_lag) % 7]
    
    # List to store results
    upcoming_classes = []

    # Iterate over the schedule of tomorrow
    if tomorrow in classes_dict:
        for time_str, class_name in classes_dict[tomorrow].items():
            # Convert time_str (e.g., '13:00') to a datetime object for tomorrow
            time_of_class = datetime.strptime(f"{time_str}", "%H:%M").replace(
                year=now.year,
                month=now.month,
                day=(now + timedelta(days=days_lag)).day
            )

            # Check if the class is within the next 48 hours
            if now <= time_of_class <= time_delay_hours_later:
                print('ola', time_of_class, class_name)
                upcoming_classes.append((time_of_class, class_name))
    
    return upcoming_classes
    

def schedule_slots(driver, wait, class_time, class_name, max_retries=5, retry_delay=2):
    """
    Attempts to book a class based on a given time and class name.
    """
    
    for attempt in range(max_retries):
        try:
            # Locate all class time elements
            time_elements = wait.until(EC.visibility_of_all_elements_located((By.CSS_SELECTOR, '[data-cy="start-time"]')))

            for time_element in time_elements:
                extracted_time = time_element.text.strip()  # Extract class time

                if extracted_time == class_time:  # Match time from dictionary
                    # Find the class name element
                    booking_name_element = time_element.find_element(By.XPATH, '../../..//*[@data-cy="booking-name"]')
                    extracted_class_name = booking_name_element.text.strip()

                    # Validate both class time AND class name
                    if extracted_class_name == class_name:  # ✅ Now checking correctly
                        # Click the time element to select the class
                        time_element.click()

                        # Click the book button
                        class_book = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-cy="book-button"]')))
                        class_book.click()

                        # Click the confirm button
                        confirm_book = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-cy="book-class-confirm-button"]')))
                        confirm_book.click()

                        print(f"✅ Class '{class_name}' at {class_time} booked successfully.")
                        return f"{class_name} at {class_time}"  # Exit after successful booking
            
            # If no matching class was found, refresh and retry
            print(f"🔄 Matching class not found for {class_time} ({class_name}), refreshing the page (attempt {attempt+1}/{max_retries}).")
            driver.refresh()
            time.sleep(retry_delay)
        
        except (WebDriverException, StaleElementReferenceException) as e:
            print(f"⚠️ Attempt {attempt + 1} failed: {e}")
            time.sleep(retry_delay)  # Wait before retrying
    
    print(f"❌ Failed to book class '{class_name}' at {class_time} after maximum retries.")
    return None  # Return None if booking was unsuccessful
    
# see the upcoming classes in this 48 hours timeframe (only including the classes for the day we want to schedule)
upcoming_classes = find_classes_in_next_delay_hours(classes_dict, delay_hours)

# Extract the hours and minutes as strings and convert the list of tuples into a dictionary of all to shedule
classes_of_day_dict = {dt.strftime("%H:%M"): name for dt, name in upcoming_classes}

# run all and see which ones were successfully reserved ("successful_classes" variable)

successful_classes = []
for class_time, class_name in classes_of_day_dict.items():
    successful_class = schedule_slots(driver, wait, class_time, class_name)
    successful_classes.append(successful_class)


# See the corresponding class names of each succeful time slot
filtered_class_dict = {time: classes_dict[day_of_week_tomorrow][time] for time in successful_classes if time in classes_dict[day_of_week_tomorrow]}

print(filtered_class_dict)


# now that all was done, close the session
driver.quit()



# define function to send email via TLS

def send_notification(filtered_class_dict, user_email, thread_message_id=None):
    # Set up the server and email details
    smtp_server = 'smtp.gmail.com'
    smtp_port = 587  # TLS port
    smtp_user = os.getenv('SMTP_USER')  # access the env variable
    smtp_password = os.getenv('SMTP_PASSWORD')  # access the env variable
    
    # Create the email
    msg = MIMEMultipart()
    msg['From'] = smtp_user
    msg['To'] = user_email
    msg['Subject'] = f'Fitness Hut Bot Booking Notification'

    # Include threading headers if replying to an existing thread
    if thread_message_id:
        msg['In-Reply-To'] = thread_message_id
        msg['References'] = thread_message_id
    else:
        # Generate a unique Message-ID for this email (this will be used as the thread ID)
        msg_id_domain = smtp_user.split('@')[-1]
        msg_id = f"<{os.urandom(24).hex()}@{msg_id_domain}>"
        msg['Message-ID'] = msg_id
        print(f'msg_id is {msg_id}')

    # Create the body of the email
    if filtered_class_dict:
        concatenated_items = [f"{key} - {value}" for key, value in filtered_class_dict.items()]
        
        body = f"The following classes were successfully booked for {day_of_week_tomorrow}, {tomorrow}:\n\n" + "\n".join(concatenated_items)
    else:
        body = f"No classes were successfully booked for {day_of_week_tomorrow}, {tomorrow} :("

    msg.attach(MIMEText(body, 'plain'))
    
    # Send the email
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        text = msg.as_string()
        server.sendmail(smtp_user, user_email, text)
        server.quit()
        print(f"Notification email sent to {user_email}")
        
        # Return the Message-ID to use it in the next reply
        return msg_id if not thread_message_id else thread_message_id
        
    except Exception as e:
        print(f"Failed to send email: {e}")
        return None


# send email notification and respond in the same mail thread

receive_notification_email = config['Email Notification']['receiver_email']

send_notification(filtered_class_dict, receive_notification_email, thread_message_id='<d457b64436c0154acaf5d6778875a5e6ebba97c8be1cfb30@gmail.com>')

print('current time is: {}'.format(datetime.now()))
