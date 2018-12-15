"""
By: Ryan Stanbury
To run the project run the following pip commands
pip install --upgrade google-api-python-client oauth2client
pip install bs4
pip install lxml
"""

import time  # Timer to test speed of program

import urllib3  # Obtain web pages for downloading and parsing
from bs4 import BeautifulSoup  # Parse html page

import Scraper.globals as my_globals
import Scraper.items as my_items
import Scraper.tools as my_tools


def get_champ():
    """
    Get the stat information for each champion
    :return: return double array of each champion and their stats
    """

    champ_url = []  # Each champion wiki page
    all_champ_threads = []  # Hold all threads

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

    my_tools.log_status("Getting champion info for;")

    for champ in champ_url:
        # Create a thread for each champion
        while True:
            # Only create new thread if limit has not been exceeded
            if my_globals.thread_count < 20:
                # Signal a new thread is being created
                with my_globals.counter_lock:
                    my_globals.thread_count += 1

                # Create thread for current champion
                thread = my_globals.threading.Thread(target=get_champ_info,
                                                     args=(champ, http_pool),
                                                     name=champ)

                # Append curren thread to list and start thread
                all_champ_threads.append(thread)
                thread.start()

                # Exit loop once processing is done
                break

            # Wait if the thread queue is full
            time.sleep(2)

    # Wait for all threads to finish processing
    for thread in all_champ_threads:
        thread.join()

    temp = my_globals.champion_info.copy()
    print()


def get_champ_info(champ, http_pool):

    champion_stats = {}  # Hold the stats for the current champion
    stat_type = ["Health",  # Keep track of each stat
                 "HealthRegen",
                 "ResourceBar",
                 "ResourceRegen",
                 "AttackDamage",
                 "AttackSpeed",
                 "Armor",
                 "MagicResist",
                 "MovementSpeed"]

    # Open champion page
    main_url = my_tools.get_web_page(page_name=champ[6:].replace('%27', '\'').replace('_', ' '),
                                     path='/Champions/',
                                     http_pool=http_pool)
    with my_globals.bs4_lock:
        champions_html = BeautifulSoup(markup=main_url, features='lxml')

    # Append stats to array
    for stat in stat_type:
        champ_roster_stat_html = champions_html.find(id=''.join([stat, "_", champ[6:].replace("%27", "_")]))

        # If the champion does not have that stat (eg. energy), write None instead
        try:
            champion_stats[stat] = champ_roster_stat_html.text
        except AttributeError:
            champion_stats[stat] = '0'

    # Append stats/lvl to array
    for stat in stat_type:
        # Attack speed is named differently on site
        if stat == "AttackSpeed":
            stat = "AttackSpeedBonus"

        champ_roster_stat_html = champions_html.find(id=''.join([stat, "_", champ[6:].replace("%27", "_"), "_lvl"]))

        # If the champion does not scale in that stat, write 0 instead
        try:
            champion_stats[''.join([stat, '/lvl'])] = champ_roster_stat_html.text[2:]
        except AttributeError:
            champion_stats[''.join([stat, '/lvl'])] = '0'

    # Find the mana type, location of "Secondary Bar:" test
    champions_resource_html = champions_html.find(style="font-size:10px; line-height:1em; display:block; "
                                                        "color:rgb(147, 115, 65); margin-top:3px; margin-bottom:0;")

    # Try and get the direct path of the bar
    try:
        champ_resource = champions_resource_html.next_sibling.next_element.contents[2].text
    except IndexError:
        champ_resource = "Manaless"
    # Add stat to stat array
    champion_stats['ResourceType'] = champ_resource

    # Write champs with stats into array
    my_globals.champion_info[champ[6:].replace("%27", "-")] = champion_stats

    my_tools.log_status(champ[6:])

    # Signal thread is complete
    with my_globals.counter_lock:
        my_globals.thread_count -= 1


def champ_google_sheets():
    """
    Prepare data to insert to google sheets API
    :return:
    """

    # Create a local copy of the champion info list for speed
    champion_list = my_globals.champion_info.copy()

    # Array to hold all of the champion info in rows
    all_champ_rows = []

    # Create a row for each champion
    for champ in champion_list:
        champ_row = [champ.replace('_', ' ').replace('-', '\'')]

        # Add the stats for current champion
        for stat in champion_list[champ]:
            champ_row.append(champion_list[champ][stat])

        # Append current champion to master list
        all_champ_rows.append(champ_row)

    status = ""  # Status of update
    while status != "pass":  # Try again if the update does not pass
        request = {  # Dictionary to hold updates
            "values": all_champ_rows
        }
        # Try and update sheet and get return status
        status = my_tools.push_to_sheets(request=request,
                                         type_of_request=1,
                                         range_of_update=''.join(['Champ Stats!A2:T',
                                                                  str(len(all_champ_rows) + 1)]),
                                         page_updating='Champ Stats')

        # If a new page is needed create one for the champion
        if status == "newPage":
            request = {
                "requests": {
                    "addSheet": {
                        "properties": {
                            "title": 'Champ Stats'
                        }
                    }
                }
            }
            # Create new page for the current champion
            my_tools.push_to_sheets(request=request,
                                    type_of_request=0)


def main():

    # Start time of program
    start_time = time.time()

    # Get current patch
    my_tools.get_patch()

    # Processes stat for each champion
    get_champ()
    champ_google_sheets()

    # Process all item information
    my_items.get_item(my_globals.home_directory)
    my_items.item_google_sheets()

    # End time of program
    end_time = time.time()

    # Formatting
    total_time = end_time - start_time
    minutes = round(total_time / 60)
    seconds = round(total_time % 60)
    if seconds > 10:
        # Log the duration of the program
        my_tools.log_status('M:S')
        my_tools.log_status(''.join([str(minutes), ':', str(seconds)]))
    else:
        # Log the duration of the program
        my_tools.log_status('M:S')
        my_tools.log_status(''.join([str(minutes), ':0', str(seconds)]))


if __name__ == '__main__':
    main()
