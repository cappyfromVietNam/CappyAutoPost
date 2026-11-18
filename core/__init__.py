"""
CappyAutoPost - Core Automation Package
"""
from .browser import BrowserManager
from .human_behavior import HumanSimulator
from .cookie_helper import parse_cookie_input, extract_c_user_and_xs, format_proxy
from .spintax import SpintaxEngine
from .fb_actions import FacebookActions

__all__ = [
    "BrowserManager",
    "HumanSimulator",
    "parse_cookie_input",
    "extract_c_user_and_xs",
    "format_proxy",
    "SpintaxEngine",
    "FacebookActions",
]
