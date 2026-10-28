"""The self-hosted avatar catalog shared by the user model and profile picker."""

import secrets

LEGACY_AVATAR_CHOICES = (
    ("avatar-smile", "Smile"),
    ("avatar-cat", "Cat"),
    ("avatar-fox", "Fox"),
    ("avatar-bear", "Bear"),
    ("avatar-panda", "Panda"),
    ("avatar-rabbit", "Rabbit"),
    ("avatar-owl", "Owl"),
    ("avatar-frog", "Frog"),
    ("avatar-penguin", "Penguin"),
    ("avatar-koala", "Koala"),
    ("avatar-bot", "Robot"),
    ("avatar-astronaut", "Astronaut"),
    ("avatar-ghost", "Ghost"),
    ("avatar-ninja", "Ninja"),
    ("avatar-dino", "Dinosaur"),
    ("avatar-whale", "Whale"),
    ("avatar-rocket", "Rocket"),
    ("avatar-planet", "Planet"),
    ("avatar-moon", "Moon"),
    ("avatar-sun", "Sun"),
    ("avatar-leaf", "Leaf"),
    ("avatar-mountain", "Mountain"),
    ("avatar-crown", "Crown"),
    ("avatar-bolt", "Bolt"),
)
# The original sheet is kept byte-for-byte; SVG viewports select whole cells.
PORTRAIT_SOURCE = "accounts/avatars/source.png"
PORTRAIT_SIZE = (1024, 765)
PORTRAIT_COLUMNS = (0, 174, 343, 513, 683, 853, 1024)
PORTRAIT_ROWS = (0, 154, 309, 462, 616, 765)
PORTRAIT_PADDING = 18
PORTRAIT_LABELS = (
    "Playful",
    "Confident",
    "Big smile",
    "Orange quiff",
    "Relaxed",
    "Painted smile",
    "Backwards cap",
    "Surprised",
    "Laughing",
    "Braces",
    "Cheeky grin",
    "White cat",
    "Bearded",
    "Bandana",
    "Curly hair",
    "Headset",
    "Goofy",
    "Warm smile",
    "Serious",
    "Calm",
    "White spikes",
    "Pout",
    "Wide-eyed",
    "Bald grin",
    "Mustache",
    "Side glance",
    "Pilot",
    "Spiky grin",
    "Wolf",
    "Wild grin",
)
AVATAR_CHOICES = tuple(
    (f"portrait-{index + 1:02d}", label) for index, label in enumerate(PORTRAIT_LABELS)
)
AVATAR_KEYS = tuple(key for key, _ in AVATAR_CHOICES)
STORED_AVATAR_CHOICES = (*AVATAR_CHOICES, *LEGACY_AVATAR_CHOICES)
STORED_AVATAR_KEYS = tuple(key for key, _ in STORED_AVATAR_CHOICES)
PORTRAIT_REGIONS = {
    key: (
        PORTRAIT_COLUMNS[index % 6],
        PORTRAIT_ROWS[index // 6],
        PORTRAIT_COLUMNS[index % 6 + 1] - PORTRAIT_COLUMNS[index % 6],
        PORTRAIT_ROWS[index // 6 + 1] - PORTRAIT_ROWS[index // 6],
    )
    for index, key in enumerate(AVATAR_KEYS)
}


def random_avatar():
    """Preserve the legacy default used by migration 0002."""
    return secrets.choice(tuple(key for key, _ in LEGACY_AVATAR_CHOICES))


def random_portrait():
    """Give new accounts a portrait from the selected library."""
    return secrets.choice(AVATAR_KEYS)
