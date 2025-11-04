# utils/config.py
BASE_URL = "https://govgpt.sandbox.dge.gov.ae/"
EMAIL = "farrukh.mohsin@northbaysolutions.net"
PASSWORD = "test"

# Timeouts
SHORT_WAIT = 10
LONG_WAIT = 30

# Poll config
POLL_INTERVAL = 0.25

# Directories
SCREENSHOT_DIR = "screenshots"
REPORT_DIR = "reports"

# Embedding cache path
EMBEDDING_CACHE = "reports/embeddings_cache.json"

SIMILARITY_THRESHOLD_EN = 0.60
SIMILARITY_THRESHOLD_AR = 0.60




MIN_ACCEPTABLE_LEN = 60          # treat responses shorter than this as "possibly incomplete"
EXTRA_WAIT_AFTER_SHORT = 12       # seconds to wait for additional content if short response seen
MAX_EXTRA_WAIT = 30            

POLL_INTERVAL = 0.25

LONG_WAIT = 45

SHORT_WAIT = 5   
LONG_WAIT = 30   

