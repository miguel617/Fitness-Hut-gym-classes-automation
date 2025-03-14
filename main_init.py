import time
import pandas as pd
from bs4 import BeautifulSoup
import chromedriver_autoinstaller
import os
import subprocess

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select


def insert_text(id, text, wait):
    #email_textbox = driver.find_element(By.ID, id) 
    textbox = wait.until(EC.presence_of_element_located((By.ID, id)))
    textbox.send_keys(text)
    
    textbox.click()

    #textbox.send_keys(text)

    return textbox


def initial_exec(user, pwd, website, gui_option=False):
    
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--search-engine-choice-country')

    if not gui_option:
        chrome_options.add_argument('--headless')
    #chrome_options.add_argument("--headless")    
    
    #webdriver_service = Service(chromedriver) 
    #webdriver_service = Service()
    
    # Create a WebDriver instance
    driver = webdriver.Chrome(options=chrome_options)

    driver.get(website)

    wait = WebDriverWait(driver, 10)

    # accept cookies
    try:
        cookie_button = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "cky-btn-accept")))
        cookie_button.click()
        print("Cookies accepted")
    except Exception as e:
        print("No cookie banner found or already accepted")

    # input email
    insert_text('email', user, wait)

    # input pwd
    insert_text('password', pwd, wait)


    validate_login = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-cy="login-button"]')))
    validate_login.click()


    new_reservation = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-cy="booknew-button"]')))
    new_reservation.click()


    # First, check if we have the correct gym selected, otherwise we have to remove it and add the correct one
    
    gym_name = 'Arco do Cego'
    
    #element = wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), '{}')]".format(gym_name))))
    #print(element.text)
    
    # when Miguel is the user then deselect picoas gym and select only arco do cego
    if 'miguel' in user:
       option_to_select = wait.until(EC.presence_of_element_located((By.XPATH, '//li[@role="option"]//span[text()="{}"]'.format(gym_name))))
       driver.execute_script("arguments[0].click();", option_to_select)
    
       # deselect the wrong one
       bad_gym_name = 'Picoas'
    
       option_to_deselect = wait.until(EC.presence_of_element_located((By.XPATH, '//li[@role="option"]//span[text()="{}"]'.format(bad_gym_name))))
       driver.execute_script("arguments[0].click();", option_to_deselect)
    
    else:    
       pass

    return driver, wait



# github cloning and push commits

def clone_repo(repo_url, clone_dir=''):
    if not os.path.exists(clone_dir):
        subprocess.run(['git', 'clone', repo_url, clone_dir])


def commit_push(commit_message, repo_dir=None):
    # Add and commit the changes
    subprocess.run(['git', 'add', '.'], cwd=repo_dir)
    subprocess.run(['git', 'commit', '-m', commit_message], cwd=repo_dir)

    # Push the changes back to GitHub
    subprocess.run(['git', 'push'], cwd=repo_dir)
