"""Constants for the Samsung TV Local (QN90B) component."""

DOMAIN = "samsung_tv_local"

CONF_HOST = "host"
CONF_MAC = "mac"
CONF_TOKEN = "token"
CONF_NAME = "name"

DEFAULT_NAME = "Samsung TV"
WS_PORT = 8002
WOL_PORT = 9
WOL_BCAST = "255.255.255.255"

# Friendly key name -> raw key code sent to the TV.
KEYS = {
    "power": "KEY_POWER",
    "volup": "KEY_VOLUP",
    "voldown": "KEY_VOLDOWN",
    "mute": "KEY_MUTE",
    "chup": "KEY_CHUP",
    "chdown": "KEY_CHDOWN",
    "up": "KEY_UP",
    "down": "KEY_DOWN",
    "left": "KEY_LEFT",
    "right": "KEY_RIGHT",
    "ok": "KEY_ENTER",
    "back": "KEY_RETURN",
    "exit": "KEY_EXIT",
    "home": "KEY_HOME",
    "source": "KEY_SOURCE",
    "guide": "KEY_GUIDE",
    "info": "KEY_INFO",
    "play": "KEY_PLAY",
    "pause": "KEY_PAUSE",
    "stop": "KEY_STOP",
    "ff": "KEY_FF",
    "rew": "KEY_REW",
    "rec": "KEY_REC",
    "red": "KEY_RED",
    "green": "KEY_GREEN",
    "yellow": "KEY_YELLOW",
    "blue": "KEY_BLUE",
    "menu": "KEY_MENU",
    "tools": "KEY_TOOLS",
    "list": "KEY_CH_LIST",
    "0": "KEY_0",
    "1": "KEY_1",
    "2": "KEY_2",
    "3": "KEY_3",
    "4": "KEY_4",
    "5": "KEY_5",
    "6": "KEY_6",
    "7": "KEY_7",
    "8": "KEY_8",
    "9": "KEY_9",
}

# Friendly app id -> label (the runtime installed list is authoritative).
KNOWN_APPS = {
    "org.tizen.netflix": "Netflix",
    "11101200001": "YouTube",
    "320160100764": "YouTube",
    "3201512006785": "Prime Video",
    "3201901017640": "Disney+",
    "9Ur5IzDK1D": "Spotify",
    "org.tizen.browser": "Internet",
    "3201801011689": "Apple TV",
    "xTxLOQN1a6": "Twitch",
}

PLATFORMS = ["media_player", "remote", "button"]
