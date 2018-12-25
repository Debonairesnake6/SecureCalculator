"""
By: Ryan Stanbury
To run the project run the following pip commands
pip install --upgrade google-api-python-client oauth2client
pip install bs4
pip install lxml
"""

import time  # Timer to test speed of program

import Scraper.abilities as my_abilities
import Scraper.globals as my_globals
import Scraper.tools as my_tools


def main():

    # Start time of program
    start_time = time.time()

    # Get current patch
    my_tools.get_patch()

    # Processes stat for each champion
    # my_champs.get_champ()
    # my_champs.champ_google_sheets()
    #
    # # Process all item information
    # my_items.get_item(my_globals.home_directory)
    # my_items.item_google_sheets()

    # Process all champion abilities
    my_abilities.get_abilities()
    tmp = my_globals.ability_info.copy()

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
