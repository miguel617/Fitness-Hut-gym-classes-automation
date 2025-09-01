#!/usr/bin/env python
# coding: utf-8

import time
import pandas as pd
from datetime import datetime, timedelta
import os
import configparser
import chromedriver_autoinstaller
import unicodedata

from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, StaleElementReferenceException

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from main_init import initial_exec


# ------------------------------------------------------------------------
# Utility: normalize class names (handles dashes, case, accents, spaces)
# ------------------------------------------------------------------------
def normalize_text(s: str) -> str:
    return (
        unicodedata.normalize("NFKD", s)
        .strip()
        .lower()
        .replace("–", "-")  # replace en-dash with ASCII dash
    )


# ------------------------------------------------------------------------
# Load config and init driver
# ------------------------------------------------------------------------
config = configparser.ConfigParser()
config.read('config.ini')

gui_display = eval(config['Optional Config Parameters']['gui_display'])
website = config['Optional Config Parameters']['website']
delay_hours = int(config['Optional Config Parameters']['delay_hours'])

user = os.getenv('FH_USERNAME')
pwd = os.getenv('FH_PWD')

driver, wait = initial_exec(user, pwd, website, gui_display)

classes_dict = eval(config['Classes to Schedule by Day']['classes_dict'])


# ------------------------------------------------------------------------
# Date setup
# ------------------------------------------------------------------------
current_time = datetime.now()
print("Current time:", current_time)

target_date = current_time + timedelta(hours=delay_hours)
tomorrow = target_date.strftime("%Y-%m-%d")
day_of_week_tomorrow = target_date.strftime('%A')

# Click the correct day
day_select = wait.until(
    EC.element_to_be_clickable((By.CSS_SELECTOR, f'[data-cy="booking-swiper-date-{tomorrow}"]'))
)
day_select.click()


# ------------------------------------------------------------------------
# Find classes in the next delay_hours
# ------------------------------------------------------------------------
def find_classes_in_next_delay_hours(classes_dict, delay_hours):
    now = datetime.now()
    time_delay_hours_later = now + timedelta(hours=delay_hours)

    days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    days_lag = delay_hours // 24
    tomorrow = days_of_week[(now.weekday() + days_lag) % 7]

    upcoming_classes = []
    if tomorrow in classes_dict:
        for time_str, class_name in classes_dict[tomorrow].items():
            base_date = now + timedelta(days=days_lag)
            time_of_class = datetime.combine(
                base_date.date(),
                datetime.strptime(time_str, "%H:%M").time()
            )
            if now <= time_of_class <= time_delay_hours_later:
                print('Found upcoming class:', time_of_class, class_name)
                upcoming_classes.append((time_of_class, class_name))

    return upcoming_classes


# ------------------------------------------------------------------------
# Try to schedule slots
# ------------------------------------------------------------------------
def schedule_slots(driver, wait, class_time, class_name, max_retries=5, retry_delay=2):
    for attempt in range(max_retries):
        try:
            time_elements = wait.until(
                EC.visibility_of_all_elements_located((By.CSS_SELECTOR, '[data-cy="start-time"]'))
            )

            for time_element in time_elements:
                extracted_time = time_element.text.strip()
                if extracted_time == class_time:
                    booking_name_element = time_element.find_element(By.XPATH, '../../..//*[@data-cy="booking-name"]')
                    extracted_class_name = booking_name_element.text.strip()

                    print(f"🔎 Comparing extracted='{extracted_class_name}' vs config='{class_name}'")

                    if normalize_text(extracted_class_name) == normalize_text(class_name):
                        time_element.click()

                        class_book = wait.until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-cy="book-button"]'))
                        )
                        class_book.click()

                        confirm_book = wait.until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-cy="book-class-confirm-button"]'))
                        )
                        confirm_book.click()

                        print(f"✅ Class '{class_name}' at {class_time} booked successfully.")
                        return class_time  # return only time string

            print(f"🔄 No match for {class_time} ({class_name}), refreshing (attempt {attempt+1}/{max_retries}).")
            driver.refresh()
            time.sleep(retry_delay)

        except (WebDriverException, StaleElementReferenceException) as e:
            print(f"⚠️ Attempt {attempt + 1} failed: {e}")
            time.sleep(retry_delay)

    print(f"❌ Failed to book class '{class_name}' at {class_time}.")
    return None


# ------------------------------------------------------------------------
# Run booking process
# ------------------------------------------------------------------------
upcoming_classes = find_classes_in_next_delay_hours(classes_dict, delay_hours)
classes_of_day_dict = {dt.strftime("%H:%M"): name for dt, name in upcoming_classes}

successful_classes = []
for class_time, class_name in classes_of_day_dict.items():
    successful_class = schedule_slots(driver, wait, class_time, class_name)
    if successful_class:
        successful_classes.append(successful_class)

filtered_class_dict = {
    time: classes_dict[day_of_week_tomorrow][time]
    for time in successful_classes
    if time in classes_dict[day_of_week_tomorrow]
}

print("Final booked classes:", filtered_class_dict)

driver.quit()


# ------------------------------------------------------------------------
# Email notification
# ------------------------------------------------------------------------
def send_notification(filtered_class_dict, user_email, thread_message_id=None):
    smtp_server = 'smtp.gmail.com'
    smtp_port = 587
    smtp_user = os.getenv('SMTP_USER')
    smtp_password = os.getenv('SMTP_PASSWORD')

    msg = MIMEMultipart()
    msg['From'] = smtp_user
    msg['To'] = user_email
    msg['Subject'] = 'Fitness Hut Bot Booking Notification'

    if thread_message_id:
        msg['In-Reply-To'] = thread_message_id
        msg['References'] = thread_message_id
    else:
        msg_id_domain = smtp_user.split('@')[-1]
        msg_id = f"<{os.urandom(24).hex()}@{msg_id_domain}>"
        msg['Message-ID'] = msg_id
        print(f'Generated msg_id: {msg_id}')

    if filtered_class_dict:
        concatenated_items = [f"{key} - {value}" for key, value in filtered_class_dict.items()]
        body = f"The following classes were successfully booked for {day_of_week_tomorrow}, {tomorrow}:\n\n" + "\n".join(concatenated_items)
    else:
        body = f"No classes were successfully booked for {day_of_week_tomorrow}, {tomorrow} :("

    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        text = msg.as_string()
        server.sendmail(smtp_user, user_email, text)
        server.quit()
        print(f"Notification email sent to {user_email}")
        return msg['Message-ID']
    except Exception as e:
        print(f"Failed to send email: {e}")
        return None


# Send notification
receive_notification_email = config['Email Notification']['receiver_email']
send_notification(
    filtered_class_dict,
    receive_notification_email,
    thread_message_id='<d457b64436c0154acaf5d6778875a5e6ebba97c8be1cfb30@gmail.com>'
)

print('Script finished at:', datetime.now())
