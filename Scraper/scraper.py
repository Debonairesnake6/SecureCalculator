from requests import get
from requests.exceptions import RequestException
from contextlib import closing
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

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


def get_champ_stat_info():
    """
    Get the stat information for each champion
    :return:
    """

    stat_type = ["Health",  # Keep track of each stat
                 "HealthRegen",
                 "ResourceBar",
                 "ResourceRegen",
                 "Range",
                 "AttackDamage",
                 "AttackSpeed",
                 "Armor",
                 "MagicResist",
                 "MovementSpeed"]
    ability_button = ["Innate",  # Each ability for each champion
                      "Q",
                      "W",
                      "E",
                      "R"]
    champ_list = [[], [], []]  # Champion Names with stats
    champ_url = []  # Each champion wiki page
    cnt = 0  # For Debugging
    main_url = get_url('http://leagueoflegends.wikia.com/wiki/League_of_Legends_Wiki')

    # Parse the HTML page for champion names
    champions_html = BeautifulSoup(main_url, 'html5lib')
    champ_roster_ol = champions_html.find(class_="champion_roster")
    champ_roster_li = champ_roster_ol.find_all('a')

    # Get wiki page for each champion
    for champ_roster_name in champ_roster_li:
        champ_url.append(champ_roster_name.get('href').strip())

    # Load headless chrome for champion abilities
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    driver = webdriver.Chrome("ChromeHeadless/chromedriver.exe", chrome_options=chrome_options)

    # Parse each champion
    for champ in champ_url:
        champ_stats = []  # Hold the stats for a champion
        champ_abilities = [[], [], [], [], []]  # Hold the abilities for a champion

        # Open champion page
        main_url = get_url('http://leagueoflegends.wikia.com' + champ)
        champions_html = BeautifulSoup(main_url, 'html.parser')

        # Append stats to array
        for stat in stat_type:
            champ_roster_stat_html = champions_html.find(id=stat + "_" + champ[6:].replace("%27", "_"))

            # If the champion does not have that stat (eg. energy), write None instead
            try:
                champ_stats.append(stat + ": " + champ_roster_stat_html.text)
            except AttributeError:
                champ_stats.append(stat + ": None")

        # Append stats/lvl to array
        for stat in stat_type:
            # Attack speed is named differently on site
            if stat == "AttackSpeed":
                stat = "AttackSpeedBonus"

            champ_roster_stat_html = champions_html.find(id=stat + "_" + champ[6:].replace("%27", "_") + "_lvl")

            # If the champion does not scale in that stat, write 0 instead
            try:
                champ_stats.append(stat + "Lvl: " + champ_roster_stat_html.text[2:])
            except AttributeError:
                champ_stats.append(stat + "Lvl: 0")

        # Find the mana type, location of "Secondary Bar:" test
        champions_resource_html = champions_html.find(style="font-size:10px; line-height:1em; display:block; color:rgb(147, 115, 65); margin-top:3px; margin-bottom:0;")
        # Try and get the direct path of the bar
        try:
            champ_resource = champions_resource_html.next_sibling.next_element.contents[2].text
        except IndexError:
            champ_resource = "Manaless"
        # Add stat to stat array
        champ_stats.append("ResourceType: " + champ_resource)

        # Dynamically load the page to access abilities
        driver.get('http://leagueoflegends.wikia.com' + champ)
        driver.set_page_load_timeout(30000)
        webpage = driver.execute_script('return document.body.innerHTML')
        champions_ability_html = BeautifulSoup(''.join(webpage), 'html.parser')

        # Get champion abilities
        for count, ability in enumerate(ability_button):
            # Find all stats on right side of ability bar
            champions_ability = champions_ability_html.find(class_="skill skill_" + ability.lower()).contents[1].contents[2].contents[2].contents[0].find_all('dd')
            for section in champions_ability:
                try:
                    # Combine description and stats then append to an array
                    info = section.previousSibling.text.replace("«", "").replace("»", "") + " " + section.text.replace("\xa0", "")
                    champ_abilities[count].append(info)
                except IndexError:
                    continue
                except AttributeError:
                    continue

        # Write champs with stats into array
        champ_list[0].insert(len(champ_list[0]), champ[6:].replace("%27", "-"))
        champ_list[1].insert(len(champ_list[1]), champ_stats)
        champ_list[2].insert(len(champ_list[2]), champ_abilities)

        #'''
        # Debug output
        print(champ_list[0][cnt])
        print(champ_list[1][cnt])
        for count, ability in enumerate(champ_list[2][cnt]):
            print(ability_button[count] + ": " + str(ability))
        cnt += 1
        print("\n")
        #'''

    driver.quit()

    return champ_list


def main():
    champ_names = get_champs()
    champ_info = get_champ_stat_info()  # TODO add champion ability status effects


if __name__ == '__main__':
    main()