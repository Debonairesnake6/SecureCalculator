import os  # Detect if file directory for patch exists
from shutil import rmtree  # Delete old patch folder

import urllib3  # Obtain web pages for downloading and parsing
from bs4 import BeautifulSoup  # Parse html page
from googleapiclient.discovery import build  # Build connection for authentication
from googleapiclient.errors import HttpError  # Catch HttpErrors
from httplib2 import Http  # Use Http to connect to API
from oauth2client import file, client, tools  # Used for authentication with API

import Scraper.globals as my_globals


def get_web_page(page_name, path='', sub_path='', http_pool=None, browser=None):
    """
    Either fetch page from saved pages or get it from the wiki
    :return: contents of the web page
    """

    # Paths for the folder and containing file
    folder_path = ''.join([my_globals.patch, path, sub_path, '/'])
    file_path = ''.join([folder_path, page_name, '_Page.html'])

    # Create directories if they do not already exist
    with my_globals.mkdir_lock:
        if not os.path.exists(folder_path):
            try:
                os.mkdir(folder_path)
            except OSError:
                log_error(''.join(['Failed to create directory for path: ', folder_path]))

    # Try to open downloaded page
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

        if browser is None:
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

        else:
            with open(file=file_path, mode='w', encoding='utf-8') as web_page:
                browser.get(''.join(['http://leagueoflegends.wikia.com/wiki/', page_name]))
                web_page.write(browser.page_source)

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

    with my_globals.logging_lock:
        print(status)


def get_patch():
    """
    Get the current patch to determine if a re-download of the pages are necessary
    :return:
    """

    # Url to parse for current patch
    home_url = 'http://leagueoflegends.wikia.com/wiki/League_of_Legends_Wiki'

    # Create a pool and download the requested url
    http_pool = urllib3.PoolManager()
    main_url = http_pool.request(method='GET', url=home_url).data.decode('utf-8', 'ignore')

    # Parse page and look for patch version
    with my_globals.bs4_lock:
        patch_html = BeautifulSoup(markup=main_url, features='lxml')
    current_patch_html = patch_html.find(id='navigation')
    my_globals.patch = current_patch_html.contents[55].contents[2].text.split(' ', 1)[1]

    # Grab home directory for project
    my_globals.home_directory = os.getcwd()

    # Local patch to hold saved web pages
    path = 'HTML Pages/'

    # Create main folder if not already existing
    if not os.path.isdir(path):
        try:
            os.mkdir(path)
        except OSError:
            log_error(''.join(['Failed to create directory for path: ', os.getcwd(), my_globals.patch]))

    # Detect if current patch is a new patch
    if not os.path.isdir(''.join([path, my_globals.patch])):
        try:
            # Remove old saved pages and create folder for new patch
            rmtree(path)
            os.mkdir(path)
            os.mkdir(''.join([path, my_globals.patch]))
        except OSError:
            log_error(''.join(['Failed to create directory for patch: ', os.getcwd(), path, my_globals.patch]))

    # Change path to write files
    os.chdir(path)


def push_to_sheets(request=None, type_of_request=None, range_of_update=None, page_updating=""):
    """
    Put data collected onto spreadsheet for calculations
    :param request: data to be inserted on sheet
    :param type_of_request: create page (0), or update cell (1)
    :param range_of_update: cell range to update
    :param page_updating: object being modified
    :return:
    """

    # Set current directory to project's home directory
    os.chdir(my_globals.home_directory)

    # This section connects to the Google Sheets API and is mostly copied from their tutorial
    sheet_id = '1ercODhUtMmEjI4230hZwXBOa-V7yPquwzuNjkJ98Ux4'
    scopes = 'https://www.googleapis.com/auth/spreadsheets'
    store = file.Storage('Sheets/storage.json')
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets('Sheets/googleSheetsAPI.json', scopes)
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
        # Read sheet for info
        elif type_of_request == 2:
            response = service.spreadsheets().get(
                spreadsheetId=sheet_id
            )
            return response.execute()

    # Catch error on changes and print error message
    except HttpError as error:
        # Find position of quotation marks
        error_message = str(error)
        message = []
        for pos, char in enumerate(error_message):
            if char == "\"":
                message.append(pos)

        # Display creating sheet for champion if said sheet does not exist
        if error_message[message[0] + 1:message[0] + 23] == "Unable to parse range:":
            log_error("Creating new page for " + page_updating)
            return "newPage"
        # Log error message (not including type of error)
        else:
            log_error(error_message[message[0] + 1:message[message.__len__() - 1]])

    return "pass"
