# from .scraper import push_to_sheets, get_web_page, log_status
import os  # Detect if file directory for patch exists
import threading  # Used for threading items
import time  # Timer to test speed of program

import urllib3  # Obtain web pages for downloading and parsing
from bs4 import BeautifulSoup  # Parse html page

import Scraper.globals
import Scraper.tools


def item_switch_case(column):
    """
    Dictionary to return value a stat should be placed in the array
    :param column: stat to place in array
    :return: position of stat in array
    """

    # Array holding each stats and their location
    switch_case = {
        'name': 0,
        'ability power': 1,
        'armor': 2,
        'attack damage': 3,
        'attack speed': 4,
        'base health regeneration': 5,
        'base mana regeneration': 6,
        'bonus health': 7,
        'cooldown reduction': 8,
        'critical strike chance': 9,
        'gold per 10 seconds': 10,
        'health': 11,
        'health on-hit': 12,
        'life steal': 13,
        'magic penetration': 14,
        'magic resistance': 15,
        'mana': 16,
        'movement speed': 17,
        'spell vamp': 18,
        'category': 19,
        'SR': 20,
        'TT': 21,
        'HA': 22,
        'NB': 23,
        1: 24,  # Passive
        2: 25,  # Passive
        3: 26,  # Passive
        4: 27,  # Passive
        'cost': 28
    }

    # Return Invalid Column if value not found
    return switch_case.get(column, 'Invalid Column')


def item_google_sheets():
    """
    Prepare item data to insert into google sheets API
    :return:
    """

    # Create local copy of item dict for speed purposes
    all_item_info = Scraper.globals.item_info.copy()

    # Array to hold each item update for the spreadsheet
    all_item_rows = []

    # Parse through the entire item dictionary
    for category in all_item_info:
        for item in all_item_info[category]:
            # Dictionary to hold info for the current item row
            item_row = [
                '',  # 0 name
                '',  # 1 ability power
                '',  # 2 armor
                '',  # 3 attack damage
                '',  # 4 attack speed
                '',  # 5 base health regeneration
                '',  # 6 base mana regeneration
                '',  # 7 bonus health
                '',  # 8 cooldown reduction
                '',  # 9 critical strike chance
                '',  # 10 gold per 10 seconds
                '',  # 11 health
                '',  # 12 health on-hit
                '',  # 13 life steal
                '',  # 14 magic penetration
                '',  # 15 magic resistance
                '',  # 16 mana
                '',  # 17 movement speed
                '',  # 18 spell vamp
                '',  # 19 category
                '',  # 20 SR
                '',  # 21 TT
                '',  # 22 HA
                '',  # 23 NB
                '',  # 24 passive 1
                '',  # 25 passive 2
                '',  # 26 passive 3
                '',  # 27 passive 4
                ''  # 28 cost
            ]

            # Set the name for the current item
            item_row[0] = item

            # Loop through all of the stats for the current item
            for info in all_item_info[category][item]:

                # Set value if current stat is cost, as it is not a nested dictionary
                if info == 'cost':
                    array_position = item_switch_case(info)
                    item_row[array_position] = all_item_info[category][item][info]

                # Loop through the current type of stat to add each value
                else:
                    for info_section in all_item_info[category][item][info]:

                        # Find the correct position to enter the current stat into the array
                        array_position = item_switch_case(info_section)

                        # Add the current stat into the array for the current item
                        try:
                            item_row[array_position] = all_item_info[category][item][info][info_section].replace('+',
                                                                                                                 '')

                        # If the stat is not being used by the calculator then skip (e.g. lifesteal vs monsters)
                        except TypeError:
                            pass

                # Add the item category to the array
                item_row[19] = category

                # If map section does not have yes/no, it is available on all maps
                if item_row[20] == '':
                    item_row[20] = 'yes'
                    item_row[21] = 'yes'
                    item_row[22] = 'yes'
                    item_row[23] = 'yes'

            # Append the current item to the array holding all items
            all_item_rows.append(item_row)

    # Sort the item array by name
    all_item_rows = sorted(all_item_rows)

    # Create the request dictionary to insert into google sheets
    request = {
        'values': all_item_rows
    }

    # Try to insert data into google sheets until it succeeds
    status = ''
    while status != 'pass':

        # Update the item info on the Items page
        status = Scraper.tools.push_to_sheets(request=request,
                                              type_of_request=1,
                                              range_of_update=''.join(['Items!A2:AC', str(len(all_item_rows) + 1)]),
                                              page_updating='Items')

        if status == 'pass':

            # Get sheet numerical sheet ID
            item_build_id = Scraper.tools.push_to_sheets(type_of_request=2)
            item_sheet_id = ''
            if item_build_id != 'pass' or \
                    item_build_id != 'newPage':
                for sheet in item_build_id.get('sheets'):
                    if sheet['properties'].get('title') == 'Items':
                        item_sheet_id = sheet['properties'].get('sheetId')
                        continue

            resize = {
                'requests': [
                    {
                        'autoResizeDimensions': {
                            'dimensions': {
                                'sheetId': item_sheet_id,
                                'dimension': 'COLUMNS',
                                'startIndex': 0,
                                'endIndex': 29
                            }
                        }
                    },
                    {
                        'updateDimensionProperties': {
                            'range': {
                                'sheetId': item_sheet_id,
                                'dimension': 'COLUMNS',
                                'startIndex': 24,
                                'endIndex': 28
                            },
                            'properties': {
                                'pixelSize': 500
                            },
                            'fields': 'pixelSize'
                        }
                    }
                ]
            }

            status = Scraper.tools.push_to_sheets(request=resize,
                                                  type_of_request=0)

            # If the Items page does not exist, create it
        if status == "newPage":
            new_page = {
                "requests": {
                    "addSheet": {
                        "properties": {
                            "title": 'Items'
                        }
                    }
                }
            }

            # Create new page for the Items
            Scraper.tools.push_to_sheets(request=new_page,
                                         type_of_request=0)

            # Dictionary to hold the titles for the Items page
            titles = {
                'values': [['name', 'AP', 'AR', 'AD', 'AS', 'Base HPRgn', 'Base MPRgn', 'Bonus HP', 'CDR', 'Crit',
                            'Gp/10', 'HP', 'HP On-Hit', 'LifeStl', 'Mpen', 'MR', 'MP', 'MS', 'SpellVmp', 'category',
                            'SR', 'TT', 'HA', 'NB', 'Passive 1', 'Passive 2', 'Passive 3', 'Passive 4', 'cost']]
            }

            # Update titles on the Items page
            Scraper.tools.push_to_sheets(request=titles,
                                         type_of_request=1,
                                         range_of_update='Items!A1:AC1',
                                         page_updating='Items')

    return


def get_item_page(item, cnt, finished_items_html, category, http_pool):
    """
    Retrieve information for the current item and pass it on for processing
    :param item: BS4 object for item being processed
    :param cnt: Item number within the current section
    :param finished_items_html: BS4 object to obtain current section
    :param category: Section of item being processes
    :param http_pool: Pool for urllib3 requests
    :return:
    """

    # Get item directory and name
    item_name = item.contents[0].contents[0].contents[0].get('href')
    saved_item_name = item_name[6:].replace('%27', '\'').replace('_', ' ')

    # Retrieve the html page for the current item
    item_grid_html = Scraper.tools.get_web_page(page_name=saved_item_name,
                                                path='/Items/',
                                                sub_path=category,
                                                http_pool=http_pool)

    # Parse current item html page and process the information
    with Scraper.globals.bs4_lock:
        item_html = BeautifulSoup(item_grid_html, 'lxml')
    get_item_info(item_name=item_name,
                  cnt=cnt,
                  finished_items_html=finished_items_html,
                  item_html=item_html)

    # Signal current thread is done processing
    with Scraper.globals.counter_lock:
        Scraper.globals.thread_count -= 1


def get_item_info(item_name, cnt, finished_items_html, item_html):
    """
    Process current item html page and add information to global dictionary
    :param item_name: Item path for current item
    :param cnt: Item number within the current section
    :param finished_items_html: URL of item being processed
    :param item_html:
    :return:
    """

    # Get readable item name and section
    name = item_name[6:].replace('%27', '\'').replace('_', ' ')
    item_section = finished_items_html.contents[cnt - 2].text.strip()

    # Get item info box
    item_list = item_html.find(class_='portable-infobox pi-background pi-theme-wikia pi-layout-stacked')

    # Check if item, if not then skip (e.g. skip GP ult upgrades)
    try:
        # Check if item is sub-item (e.g. Doran's Lost Shield)
        if name != item_list.contents[1].contents[0]:
            return
    except AttributeError:
        return

    # Create local dict to not constantly call global, used to improve speed
    current_info = {}

    # Get all information about the current item
    try:
        # Search through each section in the item info box
        for cnt, info_box_section in enumerate(item_list):
            try:
                # Retrieve current section name in item box
                if len(info_box_section) > 1:
                    info_box_section_name = info_box_section.contents[1].text.strip()
                else:
                    continue

                # Conduct appropriate parsing depending on current section name
                if info_box_section_name == 'Stats':  # todo add item actives
                    current_info = get_stats(info_box_section_name=info_box_section,
                                             current_info=current_info)
                elif info_box_section_name == 'Passive':
                    current_info = get_passive(info_box_section_name=info_box_section,
                                               current_info=current_info)
                elif info_box_section_name[:12] == 'Availability':
                    current_info = get_map(info_box_section_name=info_box_section,
                                           current_info=current_info)
                elif info_box_section_name[:4] == 'Cost':
                    cost = info_box_section.contents[1].contents[3].contents[1].contents[1].text
                    current_info['cost'] = cost
            except AttributeError:
                pass
            except TypeError:
                pass
    except TypeError:
        return

    # Log status of job complete and add local dictionary to global dictionary
    Scraper.tools.log_status(''.join(['Item completed: ', name]))
    Scraper.globals.item_info[item_section][name] = current_info
    return


def get_stats(info_box_section_name, current_info):
    """
    Parse the stats for current item
    :param info_box_section_name: Current section of the info box to parse
    :param current_info: Local dictionary
    :return:
    """

    # Create entry in local dictionary for stats section
    current_info['stats'] = {}

    # Loop through each stat row
    try:
        for part, item in enumerate(info_box_section_name):
            # Skip filler from HTML page
            if part % 2 == 1: # and part != 0:
                # Check if stat is being added (will raise error if otherwise and will then be skipped)
                if item.text.strip()[0] == "+":
                    # Get number value for current stat being added
                    stat_amount = item.text.strip().split(' ', 1)[0][1:]

                    # If stat_amount is not a number, the stat is adding gold instead
                    if stat_amount != '':
                        type_of_stat = item.text.strip().split(' ', 1)[1]
                    else:
                        stat_amount = item.text.strip().split(' ', 2)[1]
                        type_of_stat = ''.join(['gold ', item.text.strip().split(' ', 2)[2]])

                    # Add stat info to local dictionary
                    current_info['stats'][type_of_stat] = stat_amount
    except AttributeError:
        pass

    return current_info


def get_passive(info_box_section_name, current_info):
    """
    Parse the passive for current item
    :param info_box_section_name: Current section of the info box to parse
    :param current_info: Local dictionary
    :return:
    """

    # Create entry in local dictionary for passive section
    current_info['passive'] = {}

    # Loop though each passive row
    try:
        for part, item in enumerate(info_box_section_name):
            # Skip through filler from HTML page
            if part % 2 == 1: # and part != 0:
                passive = item.text.strip()

                if passive == 'Passive':
                    continue

                # Check if double space is present (if so that means gold is part of the passive
                if passive.find('  ') == -1:
                    # Add passive info to local dictionary
                    current_info['passive'][part // 2] = item.text.strip()
                else:
                    # Replace double space with gold
                    passive_edit = passive.replace('  +', ' gold +')

                    # Further check to verify gold is being added as other items have double space (e.g. Seraph's)
                    if passive == passive_edit:
                        passive_edit = passive.replace('  ', ' ')

                    # Add passive info to local dictionary
                    current_info['passive'][part // 2] = passive_edit

    except AttributeError:
        pass

    return current_info


def get_map(info_box_section_name, current_info):
    """
    Parse the map for current item
    :param info_box_section_name: Current section of the info box to parse
    :param current_info: Local dictionary
    :return:
    """

    # Create entry in local dictionary for map section
    current_info['map'] = {}

    # Loop though section for individual maps
    for cnt, map_section in enumerate(info_box_section_name.contents[1].contents[5].contents[1]):
        # Skip filler from HTML page
        if cnt % 2 == 0:
            continue

        # Obtain current map abbreviation (2 characters long)
        map_name = info_box_section_name.contents[1].contents[3].contents[1].contents[cnt].text

        # Check if the current map uses the item or not
        if map_section.contents[0].contents[0].get('alt') == 'Done':
            # Add map info to local dictionary
            current_info['map'][map_name] = 'yes'
        else:
            # Add map info to local dictionary
            current_info['map'][map_name] = 'no'

    return current_info


def get_item(home_directory):
    """
    Return all item information from all maps
    :return: item information
    """

    # Log current status of program
    Scraper.tools.log_status('Getting Item Grid')

    # Change directory to HTML pages
    os.chdir(''.join([home_directory, '/HTML Pages']))

    # Create urllib3 pool to download each web page
    http_pool = urllib3.PoolManager()
    main_url = Scraper.tools.get_web_page(page_name='Item', path='/Items', http_pool=http_pool)

    # For formatting
    Scraper.tools.log_status('\n')

    # Use the item page and set up parsing
    with Scraper.globals.bs4_lock:
        item_grid_html = BeautifulSoup(markup=main_url, features='lxml')

    # Find the item grid and start to parse
    finished_items_html = item_grid_html.find(id='item-grid')

    # Loop through item grid for each item section
    for cnt, null in enumerate(finished_items_html.contents):

        # Add section to dictionary
        if cnt % 4 == 1:
            # Save current section being worked on
            category = finished_items_html.contents[cnt].text.strip()

            # Skip sections not used by calculator
            if category == 'Potions and Consumables' or \
               category == 'Distributed' or \
               category == 'Removed items' or \
               category == 'Trinkets':
                continue

            # Log status of program
            Scraper.tools.log_status(''.join(['Starting Section: ', finished_items_html.contents[cnt].text.strip()]))

            # Create entry for current section in global dictionary
            Scraper.globals.item_info[finished_items_html.contents[cnt].text.strip()] = {}

        # Search though section for items
        if cnt % 4 == 3:
            # Save current section being worked on
            category = finished_items_html.contents[cnt - 2].text.strip()

            # Skip sections not used by calculator
            if category == 'Potions and Consumables' or \
               category == 'Distributed' or \
               category == 'Removed items' or \
               category == 'Trinkets':
                continue

            # Array to hold threads
            all_item_threads = []

            # Get the page for each item in the category and start to parse
            for item in finished_items_html.contents[cnt]:
                # Save item path and readable names
                item_name = item.contents[0].contents[0].contents[0].get('href')
                current_item_name = item_name[6:].replace('%27', '\'').replace('_', ' ')

                # Create thread for each item being parsed
                while True:
                    # Only create a thread if limit has not been exceeded
                    if Scraper.globals.thread_count < len(finished_items_html) / 2:
                        # Signal a new thread is being created
                        with Scraper.globals.counter_lock:
                            Scraper.globals.thread_count += 1

                        # Create thread and process each item
                        thread = threading.Thread(target=get_item_page,
                                                  args=(item, cnt, finished_items_html, category, http_pool),
                                                  name=current_item_name)

                        # Append current thread to list and start thread
                        all_item_threads.append(thread)
                        thread.start()

                        # Exit loop once processing is done
                        break

                    # Wait if a thread queue is full
                    time.sleep(2)
                # break

            # Wait for all threads to finish processing
            for thread in all_item_threads:
                thread.join()

            # For formatting
            Scraper.tools.log_status('\n')

            #FOR DEBUGGING, STOP AFTER FIRST SECTION
            # break
    #FOR DEBUGGING, CREATE LOCAL COPY AS GLOBAL VARIABLE DOES NOT SHOW UP IN THE DEBUGGER
    temp = Scraper.globals.item_info.copy()
    return


if __name__ == '__main__':
    print('test')
