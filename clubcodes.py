#! python3
"""
Twitter account CodesClub1909 posts codes, which are used to collect points at club1909.com
You may spend these points on rewards and to participate in auctions.
This script collects codes from CodesClub1909 tweets and submits them on your club1909 account page.
"""

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from twython import Twython
from twython.exceptions import TwythonError
import datetime
import configparser
import csv
import random
import re
import sys
import os
import time

# Path to phantomJS executable to use it with selenium webdriver.
PHANTOMJS_LOC = r'D:\Soft\phantomjs-2.1.1-windows\bin\phantomjs'
# List with exceptions (words that seem to qualify as code sometimes, but they are not).
EXCEPTIONS = ['SPORTSNET', 'CODE:', 'CODES', "TODAY'S", 'TODAYS', 'ARE:', 'RADIO', 'BELL', 'CENTER', '1909']


def clean_input(i):
    """ (str) -> str
    Clean up input string.
    """
    i = re.sub('#[a-zA-Z0-9-]+', '', i)     # remove twitter hashtags
    i = re.sub('\n+', ' ', i)               # replace newline characters with spaces
    i = re.sub(' +', ' ', i)                # replace multiple spaces with single space
    return i


def wait_for_element(driver, selector, timer=10, poll_frequency=0.5):
    """ (WebDriver, str[, int, float]) -> NoneType
    Wait for page to load content with CSS selector we've specified as function's argument.
    Stop script if time is out.
    """
    try:
        check = WebDriverWait(driver, timer, poll_frequency).until\
            (EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
    except TimeoutException:
        print('Crucial element has not been located on the page. Stopping script execution.')
        driver.close()
        sys.exit()


def parse_tweets(consumer_key, consumer_secret, access_key, access_secret):
    """ (str, str, str, str) -> set of str
    Arguments are Twitter API credentials.
    Return set of str with codes from parsed tweets (if any are found). Otherwise stop script execution.
    """
    try:
        twitter = Twython(consumer_key, consumer_secret, access_key, access_secret)
    except TwythonError as e:
        print(e.__class__.__name__)
        print('Can not access Twitter API. Check your API credentials, Internet connection and API Rate Limit.')
        sys.exit()
    # Search query to access tweets of CodesClub1909
    # How query is built: https://dev.twitter.com/rest/public/search
    date = datetime.datetime.today().strftime('%Y-%m-%d')    # Codes expire in one day, so we have to use today's date
    query = 'https://api.twitter.com/1.1/search/tweets.json?' + \
            'q=from%3ACodesClub1909' + '%20%27codes%20are%27' + '%20since%3A' + date
    # Query results stored in json format.
    timeline = twitter.get(query)
    # Tweets that sum up codes for a day usually have words 'codes are' in their text.
    # We can use that to filter out irrelevant tweets.
    # We will also clean up tweet's text on the fly using clean_input function.
    if timeline['statuses']:
        tweets = [clean_input(t['text']) for t in timeline['statuses'] if 'CODES ARE' in t['text'].upper()]
    else:
        print('Query request returned no results. There might be no tweets in specified time frame.')
        sys.exit()
    # Store codes in set to avoid duplicates.
    if tweets:
        codes = set()
        for tweet in tweets:
            for word in tweet.split():
                # Filter out exceptions and short words that can not be codes.
                if len(word) > 3 and word.upper() not in EXCEPTIONS:
                    codes.add(word.upper())              # Ensure that code is in upper case while adding it to set
        return codes
    else:
        print('"CODES ARE" tweets not found. No codes to collect.')
        sys.exit()


def submit_codes(codes, user, password, phantomjs_loc):
    """ (set of str, str, str, str) -> NoneType
    Log in to club1909 account using provided credentials. Locate code entry element and submit codes one by one.
    """
    driver = webdriver.PhantomJS(executable_path=phantomjs_loc)
    try:
        driver.get('https://club1909.com/')
    except WebDriverException:
        print('Site was not accessible. Stopping script execution.')
        driver.close()
        sys.exit()
    # Check for the presence of 'login' element.
    wait_for_element(driver, '.overlay-hover')
    # Click on login button and check that login form is accessible.
    driver.find_element_by_css_selector('.overlay-hover').click()
    wait_for_element(driver, '.form')
    # Enter and submit user's email and password.
    driver.find_element_by_name('email').send_keys(user)
    driver.find_element_by_name('password').send_keys(password)
    driver.find_element_by_css_selector('button.btn').click()       # login button
    # Wait for site's content to load. It may take a while, so we will use 20 seconds for wait timer.
    wait_for_element(driver, '#ctl00_CntMainBody_ctl11_VoucherCodeTextBox', timer=20)
    submit_window = driver.find_element_by_css_selector('#ctl00_CntMainBody_ctl11_VoucherCodeTextBox')
    submit_button = driver.find_element_by_css_selector('#ctl00_CntMainBody_ctl11_ProcessVoucherCodeLinkButton')
    # Loop over codes to submit them to the form.
    for code in codes:
        submit_window.send_keys(code)
        submit_button.click()
        time.sleep(0.75)
        # Collect submit time and result for log entry.
        log_time = datetime.datetime.today().strftime('%Y-%m-%d %H:%M:%S')
        log_result = driver.find_element_by_id('VoucherCodeMessageBox').text
        # Write result of code submission to log file.
        with open('log.csv', 'a', encoding='utf-8', newline='') as log:
            csv.writer(log, delimiter=';').writerow([log_time, code, log_result])
        print('Submitted code: %s | Result: %s' % (code, log_result), end='\n')
        # Clear previous input. "Ctrl+a Del" keys are used instead of clear() as they're more reliable in this case.
        submit_window.send_keys(Keys.CONTROL + 'a')
        submit_window.send_keys(Keys.DELETE)
        time.sleep(random.randint(2, 5))        # Randomise interval between codes submission.
    # Logout from club1909 account and close webdriver.
    driver.find_element_by_css_selector('#ctl00_NavigationControl_lnkLogOut').click()
    driver.close()
    print('Done.')

if __name__ == '__main__':
    # Ensure that working directory is set to clubcodes.py location to properly access credentials and log files.
    os.chdir(os.path.dirname(sys.argv[0]))
    # Get credentials for twitter API and club1909 account using configparser.
    config = configparser.ConfigParser()
    config.read('credentials.ini')
    CONSUMER_KEY = config.get('twitter', 'CONSUMER_KEY')
    CONSUMER_SECRET = config.get('twitter', 'CONSUMER_SECRET')
    ACCESS_KEY = config.get('twitter', 'ACCESS_KEY')
    ACCESS_SECRET = config.get('twitter', 'ACCESS_SECRET')
    USER = config.get('club1909', 'user')
    PASSWORD = config.get('club1909', 'password')
    # Parse tweets and submit codes to club1909.
    codes = parse_tweets(CONSUMER_KEY, CONSUMER_SECRET, ACCESS_KEY, ACCESS_SECRET)
    print(codes)
    submit_codes(codes, USER, PASSWORD, PHANTOMJS_LOC)

