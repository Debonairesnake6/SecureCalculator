from requests import get
from requests.exceptions import RequestException
from contextlib import closing
from bs4 import BeautifulSoup


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
        log_no_response('Did not get response from request to {0} : {1}'.format(url, str(e)))
        return None


def got_response(resp):
    """
    Return true if response was HTML/XML
    :param resp:
    :return:
    """

    # Get the type of page (waanting HTML)
    content_type = resp.headers['Content-Type'].lower()
    # Return page contents
    return (resp.status_code == 200
            and content_type is not None
            and content_type.find('html') > -1)


def log_no_response(e):
    """
    Print error to stdout
    :param e:
    :return:
    """

    # Print error message
    print(e)


def get_champs():
    """
    Get a list of champion names from the website
    :return:
    """

    champ_names = []
    main_url = get_url('http://leagueoflegends.wikia.com/wiki/League_of_Legends_Wiki')

    # Parse the HTML page for champion names
    champions_html = BeautifulSoup(main_url, 'html.parser')
    champ_roster_ol = champions_html.find(class_="champion_roster")
    champ_roster_li = champ_roster_ol.find_all('span')

    # Added each champion name to an array
    for champ_roster_name in champ_roster_li:
        champ_names.append(champ_roster_name.get('data-champion').strip())
    return champ_names


def get_champ_info():
    """
    Get the start information for each champion
    :return:
    """

    health = None
    health_regen = None
    champ_stats = []
    champ_list = [[], []]
    champ_url = []
    main_url = get_url('http://leagueoflegends.wikia.com/wiki/League_of_Legends_Wiki')

    # Parse the HTML page for champion names
    champions_html = BeautifulSoup(main_url, 'html.parser')
    champ_roster_ol = champions_html.find(class_="champion_roster")
    champ_roster_li = champ_roster_ol.find_all('a')

    # Get wiki page for each champion
    for champ_roster_name in champ_roster_li:
        champ_url.append(champ_roster_name.get('href').strip())

    # Parse each champion
    for x, champ in enumerate(champ_url):
        stat_count = 0

        # Open champion page
        main_url = get_url('http://leagueoflegends.wikia.com' + champ)
        champions_html = BeautifulSoup(main_url, 'html.parser')

        # Get champion health
        champ_roster_stat = champions_html.find(id="Health_" + champ[6:].replace("%27", "_"))
        health = champ_roster_stat.text
        stat_count += 1

        # Get champion health regen
        champ_roster_stat = champions_html.find(id="HealthRegen_" + champ[6:].replace("%27", "_"))
        health_regen = champ_roster_stat.text
        stat_count += 1

        champ_stats = [health, health_regen]
        champ_list = [champ[6:], champ_stats]
        print(champ_list[0])

        for stat in range(stat_count):
            print(champ_list[1][stat])

    return champ_list


def main():
    champ_names = get_champs()
    champ_info = get_champ_info()
    #for champ in champ_info:
    #    print(champ)


if __name__ == '__main__':
    main()