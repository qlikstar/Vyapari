import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler

logger = logging.getLogger("__name__")

# Create a formatter
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')

# Create the "logs" folder if it doesn't exist
logs_folder = 'logs'
os.makedirs(logs_folder, exist_ok=True)

# Create a console handler and set the formatter
console_handler = logging.StreamHandler(sys.stdout)
log_file_path = os.path.join(logs_folder, 'app.log')
file_handler = TimedRotatingFileHandler(filename=log_file_path, when='midnight', interval=1, backupCount=14)

console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

# Add the console handler to the logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# Set loglevel
logger.setLevel(logging.INFO)
