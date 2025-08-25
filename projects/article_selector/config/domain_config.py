"""Domain configuration for article selector agents."""

PREFERRED_DOMAINS = [
    "darkreading.com", "bleepingcomputer.com", "helpnetsecurity.com",
    "securityweek.com", "arstechnica.com", "wired.com", "theverge.com",
    "apnews.com", "reuters.com", "thehackernews.com", "theregister.com",
    "krebsonsecurity.com", "cisa.gov", "googleprojectzero.blogspot.com",
    "snyk.io", "pythonsafety.io", "openssf.org", "linuxfoundation.org",
    "mozilla.org", "arxiv.org", "threatpost.com", "securityaffairs.co", "seclists.org"
]

PROJECT_VENDOR_AUTH_BUT_NOT_PRIMARY_NEWS = [
    "postgresql.org", "kernelnewbies.org", "openjsf.org", "home-assistant.io",
    "openmrs.org", "debian.org", "raspberrypi.com", "w3.org", "owasp.org",
    "github.com", "redis.io", "nextcloud.com", "drupal.org", "fossa.com"
]

CAUTION_AVOID_PRIMARY = [
    "mashable.com", "techradar.com", "forbes.com", "venturebeat.com",
    "coindesk.com", "zdnet.com", "isc2.org", "paloaltonetworks.com",
    "recordedfuture.com", "akamai.com", "lifehacker.com"
]

EURACTIV_DOMAIN = "euractiv.com"