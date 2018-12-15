import threading  # Used for threading items

# Global variables
item_info = {}  # Dictionary to hold all items
champion_info = {}  # Dictionary to hold all champions
home_directory = ''  # Home directory of project
mkdir_lock = threading.Lock()  # Lock for creating directories to store web pages
counter_lock = threading.Lock()  # Lock for limiting the number of threads
logging_lock = threading.Lock()  # Lock for logging the status of the program
bs4_lock = threading.Lock()  # Lock for beautiful soup to reduce errors
patch = ''  # Current patch version
thread_count = 0  # Current thread count
