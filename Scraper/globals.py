import threading  # Used for threading items

# Global variables
item_info = {}  # Dictionary to hold all items
champion_info = {}  # Dictionary to hold all champions
ability_info = {}  # Dictionary to hold all champion abilities
home_directory = ''  # Home directory of project
mkdir_lock = threading.Lock()  # Lock for creating directories to store web pages
counter_lock = threading.Lock()  # Lock for limiting the number of threads
logging_lock = threading.Lock()  # Lock for logging the status of the program
bs4_lock = threading.Lock()  # Lock for beautiful soup to reduce errors
selenium_lock = threading.Lock()  # Lock for selenium browser
patch = ''  # Current patch version
thread_count = 0  # Current thread count
thread_max = 20  # Max number of threads to create
