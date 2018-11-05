"""
By: Ryan Stanbury
To run the project run the following pip commands
pip install --upgrade google-api-python-client oauth2client
pip install requests
pip install bs4
pip install pywebcopy
pip install pathlib
"""

import os  # Detect if file directory for patch exists
import sys  # Flush stdout to print in child process
import threading  # Used for threading items
import time  # Timer to test speed of program
from contextlib import closing  # Close connection after receiving page
from shutil import rmtree  # Delete old patch folder

from bs4 import BeautifulSoup  # Parse html page
from googleapiclient.discovery import build  # Build connection for authentication
from googleapiclient.errors import HttpError  # Catch HttpErrors
from httplib2 import Http  # Use Http to connect to API
from oauth2client import file, client, tools  # Used for authentication with API
from pywebcopy import WebPage  # Download html pages
from requests import get  # Download html page
from requests.exceptions import RequestException  # Get download exceptions

# Global variables
info = {}  # Start of dictionary to hold all items
mkdir_lock = threading.Lock()  # Lock for creating directories to store web pages
counter_lock = threading.Lock()  # Lock for limiting the number of threads
patch = ''  # Current patch version
cwd = ''  # Main directory to store web pages
thread_count = 0  # Current thread count


def get_web_page(page_name, path='', sub_path=''):
    """
    Either fetch page from saved pages or get it from the wiki
    :return: contents of the web page
    """

    global patch
    global cwd
    folder_path = ''.join([patch, path, sub_path, '/'])
    file_path = ''.join([folder_path, page_name, '_Page.html'])

    # Create directories if they do not already exist
    with mkdir_lock:
        if sub_path is not '':
            if not os.path.exists(folder_path):
                os.mkdir(folder_path)
        else:
            if not os.path.exists(folder_path):
                os.mkdir(folder_path)

    # Try to open downloaded Item page
    try:
        if os.stat(file_path).st_size == 0:
            os.remove(file_path)
            raise FileNotFoundError

        with open(file_path) as web_page:
            main_url = web_page.read()

        return main_url

    # If correct patch item page is not found, generate a new one
    except FileNotFoundError:
        # Create/close item page html file
        with open(file_path, 'w') as web_page:
            # Use pywebcopy to obtain web page with encoding and save to file
            web_page_copy = WebPage(
                url=''.join(['http://leagueoflegends.wikia.com/wiki/', page_name]),
                project_folder=cwd,
            ).encode('ascii')
            web_page.write(web_page_copy.decode('utf-8'))

        # Open and read newly created file
        with open(file_path, 'r') as web_page:
            main_url = web_page.read()

        return main_url


def get_url(url):
    """
    Send GET request to url and return HTML/XML if it exists,
    if not return None.
    :param url: url to download
    :return: return page if successful
    """

    try:
        # Get response from server
        with closing(get(url, stream=True)) as resp:
            # Return content if successful
            if got_response(resp):
                return resp.content
            else:
                return None

    # Print error message on failure
    except RequestException as e:
        log_error('Did not get response from request to {0} : {1}'.format(url, str(e)))
        return None


def got_response(resp):
    """
    Return true if response was HTML/XML
    :param resp: get response from website
    :return: return html page
    """

    # Get the type of page (wanting HTML)
    content_type = resp.headers['Content-Type'].lower()
    # Return page contents
    return (resp.status_code == 200
            and content_type is not None
            and content_type.find('html') > -1)


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

    print(status)


def get_patch():
    """
    Get the current patch to determine if a re-download of the pages are necessary
    :return:
    """

    global patch
    global cwd

    # Get the current patch number
    main_url = get_url('http://leagueoflegends.wikia.com/wiki/League_of_Legends_Wiki')
    patch_html = BeautifulSoup(main_url, 'html5lib')
    current_patch_html = patch_html.find(id='navigation')
    patch = current_patch_html.contents[55].contents[2].text.split(' ', 1)[1]
    path = 'leagueoflegends.wikia.com/'

    # Create main folder if not already existing
    if not os.path.isdir(path):
        try:
            os.mkdir(path)
        except OSError:
            log_error(''.join(['Failed to create directory for path: ', os.getcwd(), patch]))

    # Detect if current patch is a new patch
    if not os.path.isdir(''.join([path, patch])):
        try:
            rmtree(path)
            os.mkdir(path)
            os.mkdir(''.join([path, patch]))
        except OSError:
            log_error(''.join(['Failed to create directory for patch: ', os.getcwd(), path, patch]))

    # Grab current directory for pywebcopy and change path to write files
    cwd = os.getcwd()
    os.chdir(path)


def push_to_sheets(request, typeofrequest, rangeofupdate="none", champ=""):
    """
    Put data collected onto spreadsheet for calculations
    :param request: data to be inserted on sheet
    :param typeofrequest: create page (0), or update cell (1)
    :param rangeofupdate: cell range to update
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
        if typeofrequest == 0:
            service.spreadsheets().batchUpdate(
                spreadsheetId=sheet_id,
                body=request).execute()
        # Update cells on sheet
        elif typeofrequest == 1:
            service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                body=request,
                range=rangeofupdate,
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
    champions_html = BeautifulSoup(main_url, 'html5lib')
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
        champions_html = BeautifulSoup(main_url, 'html5lib')

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


def get_item_page(section, cnt, finished_items_html, category):
    global thread_count
    item_name = section.contents[0].contents[0].contents[0].get('href')
    saved_item_name = item_name[6:].replace('%27', '\'').replace('_', ' ')
    item_grid_html = get_web_page(saved_item_name, '/Items/', category)
    item_html = BeautifulSoup(item_grid_html, 'html5lib')
    get_item_info(item_name, cnt, finished_items_html, item_html)
    with counter_lock:
        thread_count -= 1


def get_item_info(item_name, cnt, finished_items_html, item_html):
    # Get info for dictionary entry
    global info
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

    current_info = {}

    # Get all information about the current item
    try:
        for section in item_list:
            try:
                section_name = section.contents[0].text.strip()
                if section_name == 'Stats':
                    current_info = get_stats(section, current_info)
                elif section_name == 'Passive':
                    current_info = get_passive(section, current_info)
                elif section_name[:12] == 'Availability':
                    current_info = get_map(section, current_info)
                elif section_name[:4] == 'Cost':
                    cost = section.contents[0].contents[3].contents[1].contents[1].text
                    current_info['cost'] = cost
            except AttributeError:
                pass
            except TypeError:
                pass
    except TypeError:
        return

    log_status(''.join(['Item completed: ', name]))
    sys.stdout.flush()
    info[item_section][name] = current_info
    return


def get_stats(section, current_info):
    current_info['stats'] = {}

    # Loop through each stat row
    try:
        for part, item in enumerate(section):
            if part % 2 == 0 and part != 0:
                if item.text.strip()[0] == "+":
                    stat_amount = item.text.strip().split(' ', 1)[0][1:]

                    if stat_amount != '':
                        type_of_stat = item.text.strip().split(' ', 1)[1]
                    else:
                        stat_amount = item.text.strip().split(' ', 2)[1]
                        type_of_stat = ''.join(['gold ', item.text.strip().split(' ', 2)[2]])
                    current_info['stats'][type_of_stat] = stat_amount
    except AttributeError:
        pass

    return current_info


def get_passive(section, current_info):
    global info
    current_info['passive'] = {}

    # Loop though each passive row
    try:
        for part, item in enumerate(section):
            if part % 2 == 0 and part != 0:
                passive = item.text.strip()
                if passive.find('  ') == -1:
                    current_info['passive'][part // 2] = item.text.strip()
                else:
                    passive_edit = passive.replace('  +', ' gold +')
                    if passive == passive_edit:
                        passive_edit = passive.replace('  ', ' ')
                    current_info['passive'][part // 2] = passive_edit

    except AttributeError:
        pass

    return current_info


def get_map(section, current_info):
    global info
    current_info['map'] = {}

    for cnt, map_section in enumerate(section.contents[0].contents[5].contents[1]):
        if cnt % 2 == 0:
            continue

        map_name = section.contents[0].contents[3].contents[1].contents[cnt].text
        if map_section.contents[0].contents[0].get('alt') == 'Done':
            current_info['map'][map_name] = 'yes'
        else:
            current_info['map'][map_name] = 'no'

    return current_info


def get_item():
    """
    Return all item information from all maps
    :return: item information
    """

    # Start of dictionary to hold all items
    global info
    global patch
    global thread_count

    main_url = get_web_page('Item', '/Items')

    # Use the item page and set up parsing
    item_grid_html = BeautifulSoup(main_url, 'html5lib')

    # Find the item grid and start to parse
    finished_items_html = item_grid_html.find(id='item-grid')
    sections = finished_items_html.contents

    for cnt, null in enumerate(sections):

        # Add section to dictionary
        if cnt % 4 == 1:
            category = finished_items_html.contents[cnt].text.strip()

            if category == 'Potions and Consumables' or \
               category == 'Distributed' or \
               category == 'Removed items' or \
               category == 'Trinkets':
                continue

            log_status(''.join(['Starting Section: ', finished_items_html.contents[cnt].text.strip()]))
            sys.stdout.flush()
            info[finished_items_html.contents[cnt].text.strip()] = {}

        # Go to each item's page
        if cnt % 4 == 3:
            category = finished_items_html.contents[cnt - 2].text.strip()

            if category == 'Potions and Consumables' or \
               category == 'Distributed' or \
               category == 'Removed items' or \
               category == 'Trinkets':
                continue

            all_item_threads = []

            # Get the page for each item in the category and start to parse
            for section in finished_items_html.contents[cnt]:
                item_name = section.contents[0].contents[0].contents[0].get('href')
                current_item_name = item_name[6:].replace('%27', '\'').replace('_', ' ')

                while True:
                    if thread_count < len(finished_items_html):
                        # Get information about item
                        thread = threading.Thread(target=get_item_page,
                                                  args=(section, cnt, finished_items_html, category),
                                                  name=current_item_name)
                        all_item_threads.append(thread)
                        thread.start()
                        with counter_lock:
                            thread_count += 1
                        break

            for thread in all_item_threads:
                thread.join()
            log_status('\n')

            break
    temp = info.copy()
    return


def main():
    start_time = time.time()
    get_patch()
    champ_list = get_champ_stat_info()
    google_sheets(champ_list)
    get_item()
    end_time = time.time()
    total_time = end_time - start_time
    minutes = round(total_time / 60)
    seconds = round(total_time % 60)
    if seconds > 10:
        log_status('M:S')
        log_status(''.join([str(minutes), ':', str(seconds)]))
    else:
        log_status('M:S')
        log_status(''.join([str(minutes), ':0', str(seconds)]))


if __name__ == '__main__':
    main()
