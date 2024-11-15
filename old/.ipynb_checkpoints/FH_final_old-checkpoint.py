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


def main():
    # define important parameters - on the config.ini file and parse it
    config = configparser.ConfigParser()
    config.read('config.ini')

    # usually these 3 are static

    #chromedriver = config['Optional Config Parameters']['chromedriver']
    gui_display = eval(config['Optional Config Parameters']['gui_display']) # to show or not the GUI - True is only useful when testing and to deploy outside my PC, it had to be False
    website = config['Optional Config Parameters']['website']

    user = config['Fitness Hut Credentials']['username']
    pwd = config['Fitness Hut Credentials']['password']

    
    # run the function on main_init.py and assign 2 variables to continue
    driver, wait = initial_exec(user, pwd, website, gui_display)

    # retrieve dictionary of days to schedule - we can change this always

    classes_dict = eval(config['Classes to Schedule by Day']['classes_dict'])

    # now we want to know today's date so that we can book tomorrow's class - 36 + 1 hours ahead 
    # This because here in config.ini we define Lisbon Time which is UTC + 1, vs UTC scheduler in the app where we will deploy

    #current_time = datetime(2024, 8, 19, 1, 30, 46, 553971)
    current_time = datetime.now()
    print(current_time)

    today = current_time.strftime("%Y-%m-%d")
    day_of_week_today = current_time.strftime('%A')

    tomorrow = (current_time + timedelta(hours=37)).strftime("%Y-%m-%d")
    day_of_week_tomorrow = (current_time + timedelta(hours=37)).strftime('%A')


    #tomorrow = '2024-08-16'
    #day_of_week_tomorrow = 'Friday'
    #classes_of_day = ['19:30', '21:30']

    # click on tomorrow's day first

    day_select = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-cy="booking-swiper-date-{}"]'.format(tomorrow))))
    day_select.click()

    def schedule_slots(driver, wait, class_of_day, max_retries=5, retry_delay=2):
        
        for attempt in range(max_retries):
            try:
                # Locate all schedules
                elements = wait.until(EC.visibility_of_all_elements_located((By.CSS_SELECTOR, '[data-cy="start-time"]')))
                
                # Attempt to find and click the desired class slot
                for element in elements:
                    if element.text == class_of_day:
                        # Click the element
                        #driver.execute_script("arguments[0].click();", element)
                        element.click()
                        
                        # Book the class by clicking the appropriate buttons
                        class_book = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-cy="book-button"]')))
                        class_book.click()
                        
                        confirm_book = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-cy="book-class-confirm-button"]')))
                        confirm_book.click()
                        
                        print("Class {} booked successfully.".format(class_of_day))
                        return class_of_day # Exit the function after successful booking
                
                # If the loop completes without finding the class, refresh and retry
                print("Class not found, refreshing the page.")
                driver.refresh()
                time.sleep(retry_delay)
            
            except (WebDriverException, StaleElementReferenceException) as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                time.sleep(retry_delay)  # Wait before retrying
        
        print("Failed to book the class after maximum retries.")

    # change 18-08-24 - to run only this script once per schedule, so in fact, the list will be only 1 schedule - 36 + 1 hours after

    # Calculate the time 37 hours from now
    target_time = current_time + timedelta(hours=37)

    # Function to check if a class is within the target time range (±30 minutes)
    def is_class_within_target_range(class_time_str):
        # Combine the next day and class time into a datetime object
        class_time = datetime.strptime(class_time_str, '%H:%M')
        class_datetime = target_time.replace(hour=class_time.hour, minute=class_time.minute)

        # Check if the class time falls within the ±30 minutes (1800 seconds) range
        return abs((class_datetime - target_time).total_seconds()) <= 1800

    # Find and print the classes that match the criteria for the next day
    scheduled_classes = []
    if day_of_week_tomorrow in classes_dict:
        for time_str, class_name in classes_dict[day_of_week_tomorrow].items():
            if is_class_within_target_range(time_str):
                scheduled_classes.append(f"{day_of_week_tomorrow} {time_str} - {class_name}")

    classes_of_day = []
    # Output the scheduled classes
    if scheduled_classes:
        print("Scheduled classes:")
        for scheduled_class in scheduled_classes:
            print(scheduled_class)
            classes_of_day.append(scheduled_class.split()[1])
    else:
        print("No classes available within the target time range.")

    successful_classes = []

    # run all and see which ones were successfully reserved ("successful_classes" variable)
    for class_of_day in classes_of_day:
        print(class_of_day)
        successful_class = schedule_slots(driver, wait, class_of_day)
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
        msg['Subject'] = f'Fitness Hut Class Booking Notification for {tomorrow}'

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


    # send email notification

    receive_notification_email = config['Email Notification']['receiver_email']

    send_notification(filtered_class_dict, receive_notification_email, thread_message_id='<d457b64436c0154acaf5d6778875a5e6ebba97c8be1cfb30@gmail.com>')

    print('current time is: {}'.format(datetime.now()))

# run it
if __name__ == "__main__":
    main()