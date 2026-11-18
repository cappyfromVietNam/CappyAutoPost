"""
CappyAutoPost - Cookie Helper & Parser
Supports:
- Raw string: "c_user=1000123; xs=38%...; datr=...;"
- JSON format (J2TEAM Cookies, EditThisCookie, Cookie-Editor): [{"name": "...", "value": "..."}, ...]
- Standard proxy formatting
"""
import json
import re
from typing import Dict, List, Optional, Tuple, Any

def parse_cookie_input(raw_input: str) -> Dict[str, str]:
    """
    Parses various cookie formats into a clean key-value dictionary.
    """
    if not raw_input or not isinstance(raw_input, str):
        return {}

    cleaned = raw_input.strip()

    # Try parsing as JSON first
    if (cleaned.startswith("[") and cleaned.endswith("]")) or (cleaned.startswith("{") and cleaned.endswith("}")):
        try:
            data = json.loads(cleaned)
            cookie_dict = {}
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and "name" in item and "value" in item:
                        cookie_dict[str(item["name"])] = str(item["value"])
            elif isinstance(data, dict):
                # Check if it has a cookies list or is a direct map
                if "cookies" in data and isinstance(data["cookies"], list):
                    for item in data["cookies"]:
                        if "name" in item and "value" in item:
                            cookie_dict[str(item["name"])] = str(item["value"])
                else:
                    for k, v in data.items():
                        cookie_dict[str(k)] = str(v)
            if cookie_dict:
                return cookie_dict
        except Exception:
            pass

    # Parse standard cookie string: "c_user=...; xs=...; sb=..."
    cookie_dict = {}
    items = re.split(r"[;\n]+", cleaned)
    for item in items:
        item = item.strip()
        if not item or "=" not in item:
            continue
        key, val = item.split("=", 1)
        key = key.strip()
        val = val.strip()
        if key:
            cookie_dict[key] = val

    return cookie_dict

def extract_c_user_and_xs(cookie_dict: Dict[str, str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Extracts c_user (Facebook UID) and xs token from a cookie dict.
    """
    c_user = cookie_dict.get("c_user")
    xs = cookie_dict.get("xs")
    return c_user, xs

def cookie_dict_to_header_string(cookie_dict: Dict[str, str]) -> str:
    """
    Converts a cookie dict back to a standard HTTP Cookie header string.
    """
    return "; ".join([f"{k}={v}" for k, v in cookie_dict.items()])

def cookie_dict_to_selenium_list(cookie_dict: Dict[str, str], domain: str = ".facebook.com") -> List[Dict[str, Any]]:
    """
    Converts a cookie dict to a list of dicts suitable for driver.add_cookie()
    """
    selenium_cookies = []
    for name, value in cookie_dict.items():
        selenium_cookies.append({
            "name": name,
            "value": value,
            "domain": domain,
            "path": "/",
            "secure": True,
            "sameSite": "Lax"
        })
    return selenium_cookies

def format_proxy(proxy_str: Optional[str]) -> Optional[Dict[str, str]]:
    """
    Parses proxy string in formats:
    - host:port
    - host:port:username:password
    - http://user:pass@host:port
    Returns requests-compatible proxies dict: {'http': '...', 'https': '...'}
    """
    if not proxy_str or not proxy_str.strip():
        return None

    raw = proxy_str.strip()
    if raw.startswith("http://") or raw.startswith("https://") or raw.startswith("socks5://"):
        return {"http": raw, "https": raw}

    parts = raw.split(":")
    if len(parts) == 2:
        host, port = parts
        url = f"http://{host}:{port}"
        return {"http": url, "https": url}
    elif len(parts) == 4:
        host, port, user, pwd = parts
        url = f"http://{user}:{pwd}@{host}:{port}"
        return {"http": url, "https": url}

    return None
