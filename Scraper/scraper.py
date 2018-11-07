"""
By: Ryan Stanbury
To run the project run the following pip commands
pip install --upgrade google-api-python-client oauth2client
pip install bs4
pip install lxml
"""

import os  # Detect if file directory for patch exists
import threading  # Used for threading items
import time  # Timer to test speed of program
from shutil import rmtree  # Delete old patch folder

import urllib3  # Obtain web pages for downloading and parsing
from bs4 import BeautifulSoup  # Parse html page
from googleapiclient.discovery import build  # Build connection for authentication
from googleapiclient.errors import HttpError  # Catch HttpErrors
from httplib2 import Http  # Use Http to connect to API
from oauth2client import file, client, tools  # Used for authentication with API

# Global variables
info = {}  # Start of dictionary to hold all items
mkdir_lock = threading.Lock()  # Lock for creating directories to store web pages
counter_lock = threading.Lock()  # Lock for limiting the number of threads
logging_lock = threading.Lock()  # Lock for logging the status of the program
patch = ''  # Current patch version
thread_count = 0  # Current thread count


def get_web_page(page_name, path='', sub_path='', http_pool=None):
    """
    Either fetch page from saved pages or get it from the wiki
    :return: contents of the web page
    """

    # Paths for the folder and containing file
    folder_path = ''.join([patch, path, sub_path, '/'])
    file_path = ''.join([folder_path, page_name, '_Page.html'])

    # Create directories if they do not already exist
    with mkdir_lock:
        if not os.path.exists(folder_path):
            try:
                os.mkdir(folder_path)
            except OSError:
                log_error(''.join(['Failed to create directory for path: ', folder_path]))

    # Try to open downloaded Item page
    try:
        # Check the file size and raise not found error if the page was not downloaded correctly
        if os.stat(file_path).st_size == 0:
            os.remove(file_path)
            raise FileNotFoundError

        # Open the file using encoding
        with open(file=file_path, mode='r', encoding='utf-8') as web_page:
            main_url = web_page.read()

        return main_url

    # If correct patch item page is not found, generate a new one
    except FileNotFoundError:
        # Log status of current page being downloaded
        log_status(''.join(['Downloading HTML page for: ', page_name]))

        # Create/close item page html file
        with open(file=file_path, mode='w', encoding='utf-8') as web_page:
            web_url = ''.join(['http://leagueoflegends.wikia.com/wiki/', page_name.replace(' ', '_')])

            # Use urllib3 pool for speed and built in threading handling
            response = http_pool.request(method='GET', url=web_url)

            # Ignore characters that are not in utf-8 as they are not needed
            web_page.write(response.data.decode('utf-8', 'ignore'))

        # Open and read newly created file
        with open(file=file_path, mode='r', encoding='utf-8') as web_page:
            main_url = web_page.read()

        return main_url


def log_error(e):
    """
    Print error to stdout
    :param e: error message
    :return:
    """

    # Print error message
    print(e)


def log_status(status):
    """
    Print to stdout
    :param status: message to print
    :return:
    """

    with logging_lock:
        print(status)


def get_patch():
    """
    Get the current patch to determine if a re-download of the pages are necessary
    :return:
    """

    global patch

    # Url to parse for current patch
    home_url = 'http://leagueoflegends.wikia.com/wiki/League_of_Legends_Wiki'

    # Create a pool and download the requested url
    http_pool = urllib3.PoolManager()
    main_url = http_pool.request(method='GET', url=home_url).data.decode('utf-8', 'ignore')

    # Parse page and look for patch version
    patch_html = BeautifulSoup(markup=main_url, features='lxml')
    current_patch_html = patch_html.find(id='navigation')
    patch = current_patch_html.contents[55].contents[2].text.split(' ', 1)[1]

    # Local patch to hold saved web pages
    path = 'HTML Pages/'

    # Create main folder if not already existing
    if not os.path.isdir(path):
        try:
            os.mkdir(path)
        except OSError:
            log_error(''.join(['Failed to create directory for path: ', os.getcwd(), patch]))

    # Detect if current patch is a new patch
    if not os.path.isdir(''.join([path, patch])):
        try:
            # Remove old saved pages and create folder for new patch
            rmtree(path)
            os.mkdir(path)
            os.mkdir(''.join([path, patch]))
        except OSError:
            log_error(''.join(['Failed to create directory for patch: ', os.getcwd(), path, patch]))

    # Change path to write files
    os.chdir(path)


def push_to_sheets(request, type_of_request, range_of_update="none", champ=""):
    """
    Put data collected onto spreadsheet for calculations
    :param request: data to be inserted on sheet
    :param type_of_request: create page (0), or update cell (1)
    :param range_of_update: cell range to update
    :param champ: champion being modified
    :return:
    """

    os.chdir('..')

    # This section connects to the Google Sheets API and is copied from their tutorial
    sheet_id = '1ercODhUtMmEjI4230hZwXBOa-V7yPquwzuNjkJ98Ux4'
    scopes = 'https://www.googleapis.com/auth/spreadsheets'
    store = file.Storage('storage.json')
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets('googleSheetsAPI.json', scopes)
        credentials = tools.run_flow(flow, store)
    service = build('sheets', 'v4', http=credentials.authorize(Http()))

    # Attempt to update sheet with changes
    try:
        # Create new sheet
        if type_of_request == 0:
            service.spreadsheets().batchUpdate(
                spreadsheetId=sheet_id,
                body=request).execute()
        # Update cells on sheet
        elif type_of_request == 1:
            service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                body=request,
                range=range_of_update,
                valueInputOption="USER_ENTERED").execute()

    # Catch error on changes and print error message
    except HttpError as e:
        # Find position of quotation marks
        error = str(e)
        message = []
        for pos, char in enumerate(error):
            if char == "\"":
                message.append(pos)

        # Display creating sheet for champion if said sheet does not exist
        if error[message[0] + 1:message[0] + 23] == "Unable to parse range:":
            log_error("Creating new page for " + champ)
            return "newPage"
        # Log error message (not including type of error)
        else:
            log_error(error[message[0] + 1:message[message.__len__() - 1]])

    os.chdir('leagueoflegends.wikia.com')

    return "pass"


def get_champ_stat_info():
    """
    Get the stat information for each champion
    :return: return double array of each champion and their stats
    """

    stat_type = ["Health",  # Keep track of each stat
                 "HealthRegen",
                 "ResourceBar",
                 "ResourceRegen",
                 "AttackDamage",
                 "AttackSpeed",
                 "Armor",
                 "MagicResist",
                 "MovementSpeed"]
    champ_list = [[], []]  # Champion Names with stats
    champ_url = []  # Each champion wiki page
    main_url = get_web_page('League_of_Legends_Wiki')

    # Parse the HTML page for champion names
    champions_html = BeautifulSoup(markup=main_url, features='lxml')
    champ_roster_ol = champions_html.find(class_="champion_roster")
    champ_roster_li = champ_roster_ol.find_all('a')

    # Get wiki page for each champion
    for champ_roster_name in champ_roster_li:
        champ_url.append(champ_roster_name.get('href').strip())

    log_status("Getting champion info for;")

    #FOR DEBUGGING ONLY REMOVE AFTER COMPLETE
    champ_list_testing = ["/wiki/Aatrox",
                          "/wiki/Ahri"]

    # Parse each champion
    for cnt, champ in enumerate(champ_list_testing): #champ_url): # FOR DEBUGGING ONLY REMOVE AFTER COMPLETE
        champ_stats = []  # Hold the stats for a champion

        # Open champion page
        main_url = get_web_page(champ[6:].replace('%27', '\'').replace('_', ' '), '/Champions/')
        champions_html = BeautifulSoup(markup=main_url, features='lxml')

        # Append stats to array
        for stat in stat_type:
            champ_roster_stat_html = champions_html.find(id=''.join([stat, "_", champ[6:].replace("%27", "_")]))

            # If the champion does not have that stat (eg. energy), write None instead
            try:
                champ_stats.append(champ_roster_stat_html.text)
            except AttributeError:
                champ_stats.append("0")

        # Append stats/lvl to array
        for stat in stat_type:
            # Attack speed is named differently on site
            if stat == "AttackSpeed":
                stat = "AttackSpeedBonus"

            champ_roster_stat_html = champions_html.find(id=''.join([stat, "_", champ[6:].replace("%27", "_"), "_lvl"]))

            # If the champion does not scale in that stat, write 0 instead
            try:
                champ_stats.append(champ_roster_stat_html.text[2:])
            except AttributeError:
                champ_stats.append("0")

        # Find the mana type, location of "Secondary Bar:" test
        champions_resource_html = champions_html.find(style="font-size:10px; line-height:1em; display:block; "
                                                            "color:rgb(147, 115, 65); margin-top:3px; margin-bottom:0;")

        # Try and get the direct path of the bar
        try:
            champ_resource = champions_resource_html.next_sibling.next_element.contents[2].text
        except IndexError:
            champ_resource = "Manaless"
        # Add stat to stat array
        champ_stats.append(''.join(["ResourceType: ", champ_resource]))

        # Write champs with stats into array
        champ_list[0].insert(len(champ_list[0]), champ[6:].replace("%27", "-"))
        champ_list[1].insert(len(champ_list[1]), champ_stats)

        log_status(champ[6:])

    return champ_list


def google_sheets(champ_list):
    """
    Prepare data to insert to google sheets API
    :param champ_list: double array of each champion and their stats
    :return:
    """

    # FOR TESTING ONLY
    sheet_ranges = ['Aatrox',
                    'Ahri']

    # Update champion stats and create new page if needed
    for cnt, champ in enumerate(sheet_ranges):  # REPLACE WITH CHAMP_LIST ONCE FINISHED
        status = ""  # Status of update
        while status != "pass":  # Try again if the update does not pass
            request = {  # Dictionary to hold updates
                "values": [
                    [champ, "HP", "HPRgn", "MP", "MPRgn", "AP", "AD", "AS",
                     "AR", "MR", "MS", "CDR", "Pass. Stacks", "Lvl"],
                    ["Base",
                     ''.join(["=", champ_list[1][cnt][0], "+(", champ_list[1][cnt][9],
                              "*(N3-1))*(0.7025+0.0175*(N3-1))"]),
                     ''.join(["=", champ_list[1][cnt][1], "+(", champ_list[1][cnt][10],
                              "*(N3-1))*(0.7025+0.0175*(N3-1))"]),
                     ''.join(["=", champ_list[1][cnt][2], "+(", champ_list[1][cnt][11],
                              "*(N3-1))*(0.7025+0.0175*(N3-1))"]),
                     ''.join(["=", champ_list[1][cnt][3], "+(", champ_list[1][cnt][12],
                              "*(N3-1))*(0.7025+0.0175*(N3-1))"]),
                     "",  # AP
                     ''.join(["=", champ_list[1][cnt][4], "+(", champ_list[1][cnt][13],
                              "*(N3-1))*(0.7025+0.0175*(N3-1))"]),
                     ''.join(["=", champ_list[1][cnt][5], "+((", str(float(champ_list[1][cnt][14]) / 100), "*",
                              champ_list[1][cnt][5], ")*(N3-1))*(0.7025+0.0175*(N3-1))"]),
                     ''.join(["=", champ_list[1][cnt][6], "+(", champ_list[1][cnt][15],
                              "*(N3-1))*(0.7025+0.0175*(N3-1))"]),
                     ''.join(["=", champ_list[1][cnt][7], "+(", champ_list[1][cnt][16],
                              "*(N3-1))*(0.7025+0.0175*(N3-1))"]),
                     ''.join(["=", champ_list[1][cnt][8], "+(", champ_list[1][cnt][17],
                              "*(N3-1))*(0.7025+0.0175*(N3-1))"]),
                     "",  # CDR
                     "",  # Stacks
                     "18"]  # Lvl
                ]
            }
            # Try and update sheet and get return status
            status = push_to_sheets(request, 1, ''.join([champ, "!A2:N3"]), champ=champ)

            # If a new page is needed create one for the champion
            if status == "newPage":
                request = {
                    "requests": {
                        "addSheet": {
                            "properties": {
                                "title": champ
                            }
                        }
                    }
                }
                # Create new page for the current champion
                push_to_sheets(request, 0)


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

    global thread_count

    # Get item directory and name
    item_name = item.contents[0].contents[0].contents[0].get('href')
    saved_item_name = item_name[6:].replace('%27', '\'').replace('_', ' ')

    # Retrieve the html page for the current item
    item_grid_html = get_web_page(page_name=saved_item_name,
                                  path='/Items/',
                                  sub_path=category,
                                  http_pool=http_pool)

    # Parse current item html page and process the information
    item_html = BeautifulSoup(item_grid_html, 'lxml')
    get_item_info(item_name=item_name,
                  cnt=cnt,
                  finished_items_html=finished_items_html,
                  item_html=item_html)

    # Signal current thread is done processing
    with counter_lock:
        thread_count -= 1


def get_item_info(item_name, cnt, finished_items_html, item_html):
    """
    Process current item html page and add information to global dictionary
    :param item_name: Item path for current item
    :param cnt: Item number within the current section
    :param finished_items_html: URL of item being processed
    :param item_html:
    :return:
    """

    # Get info for dictionary entry
    global info

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
        for info_box_section in item_list:
            try:
                # Retrieve current section name in item box
                info_box_section_name = info_box_section.contents[0].text.strip()

                # Conduct appropriate parsing depending on current section name
                if info_box_section_name == 'Stats':
                    current_info = get_stats(info_box_section_name=info_box_section,
                                             current_info=current_info)
                elif info_box_section_name == 'Passive':
                    current_info = get_passive(info_box_section_name=info_box_section,
                                               current_info=current_info)
                elif info_box_section_name[:12] == 'Availability':
                    current_info = get_map(info_box_section_name=info_box_section,
                                           current_info=current_info)
                elif info_box_section_name[:4] == 'Cost':
                    cost = info_box_section.contents[0].contents[3].contents[1].contents[1].text
                    current_info['cost'] = cost
            except AttributeError:
                pass
            except TypeError:
                pass
    except TypeError:
        return

    # Log status of job complete and add local dictionary to global dictionary
    log_status(''.join(['Item completed: ', name]))
    info[item_section][name] = current_info
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
            if part % 2 == 0 and part != 0:
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
            if part % 2 == 0 and part != 0:
                passive = item.text.strip()

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
    for cnt, map_section in enumerate(info_box_section_name.contents[0].contents[5].contents[1]):
        # Skip filler from HTML page
        if cnt % 2 == 0:
            continue

        # Obtain current map abbreviation (2 characters long)
        map_name = info_box_section_name.contents[0].contents[3].contents[1].contents[cnt].text

        # Check if the current map uses the item or not
        if map_section.contents[0].contents[0].get('alt') == 'Done':
            # Add map info to local dictionary
            current_info['map'][map_name] = 'yes'
        else:
            # Add map info to local dictionary
            current_info['map'][map_name] = 'no'

    return current_info


def get_item():
    """
    Return all item information from all maps
    :return: item information
    """

    global info
    global patch
    global thread_count

    # Log current status of program
    log_status('Getting Item Grid')

    # Create urllib3 pool to download each web page
    http_pool = urllib3.PoolManager()
    main_url = get_web_page(page_name='Item', path='/Items', http_pool=http_pool)

    # For formatting
    log_status('\n')

    # Use the item page and set up parsing
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
            log_status(''.join(['Starting Section: ', finished_items_html.contents[cnt].text.strip()]))

            # Create entry for current section in global dictionary
            info[finished_items_html.contents[cnt].text.strip()] = {}

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
                    if thread_count < len(finished_items_html) / 2:
                        # Create thread and process each item
                        thread = threading.Thread(target=get_item_page,
                                                  args=(item, cnt, finished_items_html, category, http_pool),
                                                  name=current_item_name)

                        # Append current thread to list and start thread
                        all_item_threads.append(thread)
                        thread.start()

                        # Signal a new thread is being created
                        with counter_lock:
                            thread_count += 1

                        # Exit loop once processing is done
                        break

                    # Wait if a thread queue is full
                    time.sleep(2)

            # Wait for all threads to finish processing
            for thread in all_item_threads:
                thread.join()

            # For formatting
            log_status('\n')

            #FOR DEBUGGING, STOP AFTER FIRST SECTION
            #break
    # FOR DEBUGGING, CREATE LOCAL COPY AS GOLBAL VARIABLE DO NOT SHOW UP IN THE DEBUGGER
    temp = info.copy()

    #PLACEOLDER, EACH ITEM STAT NEEDED ON EXCEL SHEET
    """
    ability power
    armor
    attack damage
    attack speed
    base health regeneration
    base mana regeneration
    bonus health
    cooldown reduction
    critical strike chance
    gold per 10 seconds
    health
    health on-hit
    life steal
    magic penetration
    magic resistance
    mana
    movement speed
    spell vamp
    """
    return


def main():
    # Start time of program
    start_time = time.time()

    # Get current patch
    get_patch()

    # Processes stat for each champion
    #champ_list = get_champ_stat_info()
    #google_sheets(champ_list)

    # Process all item information
    get_item()

    # End time of program
    end_time = time.time()

    # Formatting
    total_time = end_time - start_time
    minutes = round(total_time / 60)
    seconds = round(total_time % 60)
    if seconds > 10:
        # Log the duration of the program
        log_status('M:S')
        log_status(''.join([str(minutes), ':', str(seconds)]))
    else:
        # Log the duration of the program
        log_status('M:S')
        log_status(''.join([str(minutes), ':0', str(seconds)]))


if __name__ == '__main__':
    main()
