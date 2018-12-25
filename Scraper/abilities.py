import re  # Regex for
import time  # Timer to test speed of program

import urllib3  # Obtain web pages for downloading and parsing
from bs4 import BeautifulSoup  # Parse html page
from selenium import webdriver  # Browser to load ability boxes

import Scraper.globals as my_globals
import Scraper.tools as my_tools


def get_abilities():

    champ_url = []  # Each champion wiki page
    all_ability_threads = []  # Hold all threads

    # Start headless chrome to get javascript from pages
    driver = webdriver.ChromeOptions()
    driver.add_argument('headless')

    # try:  #todo detect if selenium is installed
    # Current directory is Scraper\HTML Pages
    chrome = webdriver.Chrome(chrome_options=driver, executable_path='../Chrome Driver/chromedriver.exe')
    chrome.implicitly_wait(30)
    # except:
    #     pass

    # Fetch main wiki page
    http_pool = urllib3.PoolManager()
    main_url = my_tools.get_web_page(page_name='League_of_Legends_Wiki', http_pool=http_pool)

    # Parse the HTML page for champion names
    with my_globals.bs4_lock:
        champions_html = BeautifulSoup(markup=main_url, features='lxml')
    champ_roster_ol = champions_html.find(class_="champion_roster")
    champ_roster_li = champ_roster_ol.find_all('a')

    # Get wiki page for each champion
    for champ_roster_name in champ_roster_li:
        champ_url.append(champ_roster_name.get('href').strip())

    # General log message
    my_tools.log_status("Getting ability info for;")

    for champ in champ_url:

        # Change formatting for readability
        champ = champ[6:].replace('%27', '\'').replace('_', ' ')

        #FOR DEBUGGING ONLY
        if champ != "Akali":
            # continue
            pass

        # Create a thread for each champion
        while True:
            # Only create new thread if limit has not been exceeded
            if my_globals.thread_count < my_globals.thread_max:
                # Signal a new thread is being created
                with my_globals.counter_lock:
                    my_globals.thread_count += 1

                # Create thread for current champion
                thread = my_globals.threading.Thread(target=get_ability_info,
                                                     args=(champ, chrome),
                                                     name=champ)

                # Append curren thread to list and start thread
                all_ability_threads.append(thread)
                thread.start()

                # Exit loop once processing is done
                break

            # Wait if the thread queue is full
            time.sleep(2)

        #FOR DEBUGGING ONLY
        # break

    # Wait for all threads to finish processing
    for thread in all_ability_threads:
        thread.join()

    temp = my_globals.champion_info.copy() #FOR DEBUGGING ONLY
    return


def get_ability_info(champ, chrome):
    """
    Process all ability info
    :param champ: Champion being processed
    :param chrome: Selenium browser to load ability boxes
    :return:
    """

    # Log wich champion is currently being processed
    my_tools.log_status(champ)

    # Open champion page
    with my_globals.selenium_lock:
        ability_url = my_tools.get_web_page(page_name=champ,
                                            path='/Abilities',
                                            browser=chrome)
        abilities_html = BeautifulSoup(markup=ability_url, features='lxml')

    # Use regex to find each skill box
    passive_html = abilities_html.find_all('div', {'class': re.compile('skill skill.*')})

    # Hold the current abilities for this champion
    current_abilities = {}
    cnt_test = 0 #DEBUG ONLY

    # Loop through each ability box
    for ability in passive_html:
        # 0 = passive
        # 1 = q
        # 2 = w
        # 3 = e
        # 4 = r or q2
        # 5 = w2
        # 6 = e2
        # 7 = r
        if cnt_test != 3:  # and cnt_test != 6: #DEBUG ONLY
            cnt_test += 1
            # continue
        else:
            cnt_test += 1

        # Get the button name
        button = ability.get('class')[1].split('_', 1)[1]
        if button == 'innate':
            button = 'passive'

        # Detect if already has ability key (eg. for Jayce/Rek'sai)
        try:
            if current_abilities[button]:
                button += '2'
        except KeyError:
            pass

        # Create entry for current button
        current_abilities[button] = {}

        # Get name for current ability
        ability = ability.contents[1].contents[2]
        current_abilities[button]['name'] = ability.get('id').replace('_', ' ').replace('.27', '\'')

        # Get string for all ability stat
        info = ability.contents[1].contents[1].contents[0].contents[2]

        # Split up the list based on stats
        all_stats = info.text.split(':')

        # Detect if there is an html element (eg. image) in the text and remove it
        image_start = [stat for stat in all_stats if '<' in stat]
        for illegal in image_start:
            all_stats.remove(illegal)

        # Remove the remaining part of the tag
        image_end = [stat for stat in all_stats if '>' in stat]
        for illegal in image_end:
            location = [pos for pos, char in enumerate(illegal) if char == '>']
            legal = illegal[location[len(location) - 1] + 2:]
            for cnt, stat in enumerate(all_stats):
                if stat == illegal:
                    all_stats[cnt] = legal

        # Go throgh each stat
        for cnt, stat in enumerate(all_stats):

            # Don't process last one, already handled
            if cnt + 1 < len(all_stats):

                # Split up the current stat
                full_effect = ''
                effect = stat.split(' ')

                # Loop through each stat
                for word in effect:

                    # Upper case is often used for a new type of effect
                    if word.isupper():
                        if full_effect == '':
                            full_effect += word.lower()
                        else:
                            full_effect += ''.join([' ', word.lower()])

                    # These words are not in uppercase
                    elif word == 'On-Target':
                        full_effect += word.lower()
                    elif word == 'Cooldown':
                        full_effect += ''.join([' ', word.lower()])

                # Get the next stat
                full_value = ''
                value = all_stats[cnt + 1].split(' ')

                # Loop through for each number in the next stat
                for number in value:
                    # Often writen like 5/10/15 for values
                    if number.isdigit():
                        full_value += number
                    elif number == '/':

                        full_value += '/'

                    # Global is still a valid value
                    elif number == 'Global':
                        full_value += number

                    # Test if text has a decimal
                    else:
                        try:
                            # Will error out if word, but will take decimals (eg. 2.5)
                            float(number)
                            full_value += number
                        except ValueError:
                            pass

                # Put them together
                current_abilities[button][full_effect] = full_value.strip()

    # Add current ability to list
    my_globals.ability_info[champ.replace('\'', '_')] = current_abilities
    tmp = my_globals.ability_info.copy() #DEBUG ONLY

    # Signal current thread is done processing
    with my_globals.counter_lock:
        my_globals.thread_count -= 1
