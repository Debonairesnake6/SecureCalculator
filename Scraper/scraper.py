"""
By: Ryan Stanbury
To run the project run the following pip commands
pip install --upgrade google-api-python-client oauth2client
pip install requests
pip install bs4
"""

from requests import get  # Download html page
from requests.exceptions import RequestException  # Get download exceptions
from contextlib import closing  # Close connection after receiving page
from bs4 import BeautifulSoup  # Parse html page
from googleapiclient.discovery import build  # Build connection for authentication
from googleapiclient.errors import HttpError  # Catch HttpErrors
from httplib2 import Http  # Use Http to connect to API
from oauth2client import file, client, tools  # Used for authentication with API


def get_url(url):
    """
    Send GET request to url and return HTML/XML if it exists,
    if not return None.
    :param url:
    :return:
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
    :param resp:
    :return:
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
    :param e:
    :return:
    """

    # Print error message
    print(e)


def push_to_sheets(request, typeofrequest, rangeofupdate="none", champ=""):
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
        if typeofrequest == 0:
            service.spreadsheets().batchUpdate(
                spreadsheetId=sheet_id,
                body=request).execute()
        elif typeofrequest == 1:
            service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                body=request,
                range=rangeofupdate,
                valueInputOption="USER_ENTERED").execute()

    # Catch error on changes and print error message
    except HttpError as e:
        error = str(e)
        message = []
        for pos, char in enumerate(error):
            if char == "\"":
                message.append(pos)

        if error[message[0] + 1:message[0] + 23] == "Unable to parse range:":
            log_error("Creating new page for " + champ)
            return "newPage"
        else:
            log_error(error[message[0] + 1:message[message.__len__() - 1]])

    return "pass"


def get_champ_stat_info():
    """
    Get the stat information for each champion
    :return:
    """

    stat_type = ["Health",  # Keep track of each stat
                 "HealthRegen",
                 "ResourceBar",
                 "ResourceRegen",
                 #"Range",
                 "AttackDamage",
                 "AttackSpeed",
                 "Armor",
                 "MagicResist",
                 "MovementSpeed"]
    champ_list = [[], []]  # Champion Names with stats
    champ_url = []  # Each champion wiki page
    main_url = get_url('http://leagueoflegends.wikia.com/wiki/League_of_Legends_Wiki')

    # Parse the HTML page for champion names
    champions_html = BeautifulSoup(main_url, 'html5lib')
    champ_roster_ol = champions_html.find(class_="champion_roster")
    champ_roster_li = champ_roster_ol.find_all('a')

    # Get wiki page for each champion
    for champ_roster_name in champ_roster_li:
        champ_url.append(champ_roster_name.get('href').strip())

    print("Getting champion info for;")

    #FOR DEBUGGING ONLY REMOVE AFTER COMPLETE
    champ_list_testing = ["/wiki/Aatrox",
                          "/wiki/Ahri"]

    # Parse each champion
    for cnt, champ in enumerate(champ_list_testing): #champ_url): # FOR DEBUGGING ONLY REMOVE AFTER COMPLETE
        champ_stats = []  # Hold the stats for a champion

        # Open champion page
        main_url = get_url('http://leagueoflegends.wikia.com' + champ)
        champions_html = BeautifulSoup(main_url, 'html.parser')

        # Append stats to array
        for stat in stat_type:
            champ_roster_stat_html = champions_html.find(id=stat + "_" + champ[6:].replace("%27", "_"))

            # If the champion does not have that stat (eg. energy), write None instead
            try:
                #champ_stats.append(stat + ": " + champ_roster_stat_html.text)
                champ_stats.append(champ_roster_stat_html.text)
            except AttributeError:
                #champ_stats.append(stat + ": None")
                champ_stats.append("0")

        # Append stats/lvl to array
        for stat in stat_type:
            # Attack speed is named differently on site
            if stat == "AttackSpeed":
                stat = "AttackSpeedBonus"

            champ_roster_stat_html = champions_html.find(id=stat + "_" + champ[6:].replace("%27", "_") + "_lvl")

            # If the champion does not scale in that stat, write 0 instead
            try:
                #champ_stats.append(stat + "Lvl: " + champ_roster_stat_html.text[2:])
                champ_stats.append(champ_roster_stat_html.text[2:])
            except AttributeError:
                #champ_stats.append(stat + "Lvl: 0")
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
        champ_stats.append("ResourceType: " + champ_resource)

        # Write champs with stats into array
        champ_list[0].insert(len(champ_list[0]), champ[6:].replace("%27", "-"))
        champ_list[1].insert(len(champ_list[1]), champ_stats)

        print(champ[6:])

        '''
        # Debug output
        print(champ_list[0][cnt])
        print(champ_list[1][cnt])
        print("\n")
        '''

    return champ_list


def google_sheets(champ_list):

    # FOR TESTING ONLY
    sheet_ranges = ['Aatrox',
                    'Ahri']

    # Update champion stats and create new page if needed
    for cnt, champ in enumerate(sheet_ranges):  # REPLACE WITH CHAMP_LIST ONCE FINISHED
        status = ""  # Status of update
        while status != "pass":  # Try again if the update does not pass
            request = {  # Dictionary to old updates
                "values": [
                    [champ, "HP", "HPRgn", "MP", "MPRgn", "AP", "AD", "AS",
                     "AR", "MR", "MS", "CDR", "Pass. Stacks", "Lvl"],
                    ["Base",
                     "=" + champ_list[1][cnt][0] + "+(" + champ_list[1][cnt][9] + "*(N3-1))*(0.7025+0.0175*(N3-1))",
                     "=" + champ_list[1][cnt][1] + "+(" + champ_list[1][cnt][10] + "*(N3-1))*(0.7025+0.0175*(N3-1))",
                     "=" + champ_list[1][cnt][2] + "+(" + champ_list[1][cnt][11] + "*(N3-1))*(0.7025+0.0175*(N3-1))",
                     "=" + champ_list[1][cnt][3] + "+(" + champ_list[1][cnt][12] + "*(N3-1))*(0.7025+0.0175*(N3-1))",
                     "",  # AP
                     "=" + champ_list[1][cnt][4] + "+(" + champ_list[1][cnt][13] + "*(N3-1))*(0.7025+0.0175*(N3-1))",
                     "=" + champ_list[1][cnt][5] + "+(" + champ_list[1][cnt][14] + "*(N3-1))*(0.7025+0.0175*(N3-1))",
                     "=" + champ_list[1][cnt][6] + "+(" + champ_list[1][cnt][15] + "*(N3-1))*(0.7025+0.0175*(N3-1))",
                     "=" + champ_list[1][cnt][7] + "+(" + champ_list[1][cnt][16] + "*(N3-1))*(0.7025+0.0175*(N3-1))",
                     "=" + champ_list[1][cnt][8] + "+(" + champ_list[1][cnt][17] + "*(N3-1))*(0.7025+0.0175*(N3-1))",
                     "",  # CDR
                     "",  # Stacks
                     "18"]  # Lvl
                ]
            }
            # Try and update sheet and get return status
            status = push_to_sheets(request, 1, champ + "!A2:N3", champ=champ)

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


def main():
    champ_list = get_champ_stat_info()  # TODO send champ info to spreadsheet
    google_sheets(champ_list)


if __name__ == '__main__':
    main()
