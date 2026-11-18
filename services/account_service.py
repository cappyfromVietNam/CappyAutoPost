"""
CappyAutoPost - Account Service & Fast HTTP Validator
Validates Facebook cookies in ~0.5s via lightweight HTTP requests without opening Chrome.
"""
import re
import requests
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from core.cookie_helper import (
    parse_cookie_input,
    extract_c_user_and_xs,
    cookie_dict_to_header_string,
    format_proxy,
)
from database.models import AccountModel

USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
)

class AccountService:
    @staticmethod
    def check_cookie_status_http(cookie_input: str, proxy_str: Optional[str] = None, timeout: int = 6) -> Dict[str, Any]:
        """
        Fast validator using mbasic.facebook.com.
        Returns:
            {
                "status": "Live" | "Die" | "Checkpoint" | "Error",
                "uid": str or None,
                "name": str or None,
                "message": str
            }
        """
        cookie_dict = parse_cookie_input(cookie_input)
        c_user, xs = extract_c_user_and_xs(cookie_dict)

        if not c_user or not xs:
            return {
                "status": "Die",
                "uid": c_user,
                "name": None,
                "message": "Cookie thiếu c_user hoặc xs hợp lệ."
            }

        cookie_header = cookie_dict_to_header_string(cookie_dict)
        proxies = format_proxy(proxy_str)

        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            "Cookie": cookie_header,
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1"
        }

        try:
            session = requests.Session()
            if proxies:
                session.proxies.update(proxies)

            resp = session.get(
                "https://mbasic.facebook.com/me",
                headers=headers,
                timeout=timeout,
                allow_redirects=True
            )

            final_url = resp.url.lower()
            text = resp.text

            # 1. Check for Checkpoint
            if "checkpoint" in final_url or "checkpoint" in text.lower() or "xác minh danh tính" in text.lower():
                return {
                    "status": "Checkpoint",
                    "uid": c_user,
                    "name": None,
                    "message": "Tài khoản bị dính Checkpoint (cần xác minh)."
                }

            # 2. Check for Login page / Die
            if "login.php" in final_url or "login" in final_url or 'name="email"' in text:
                return {
                    "status": "Die",
                    "uid": c_user,
                    "name": None,
                    "message": "Cookie đã hết hạn hoặc không hợp lệ."
                }

            # 3. Check for Live profile
            # Look for account name in <title> or <strong> or meta
            name = None
            title_match = re.search(r"<title>(.*?)</title>", text, re.IGNORECASE)
            if title_match:
                title_text = title_match.group(1).strip()
                if title_text and "facebook" not in title_text.lower():
                    name = title_text

            if not name:
                name_match = re.search(r'<strong[^>]*>([^<]+)</strong>', text)
                if name_match:
                    name = name_match.group(1).strip()

            if not name:
                name = f"FB_{c_user}"

            return {
                "status": "Live",
                "uid": c_user,
                "name": name,
                "message": "Cookie hoạt động bình thường (Live)."
            }

        except requests.exceptions.ProxyError:
            return {
                "status": "Error",
                "uid": c_user,
                "name": None,
                "message": "Lỗi kết nối Proxy (Proxy die hoặc sai cấu hình)."
            }
        except requests.exceptions.Timeout:
            return {
                "status": "Error",
                "uid": c_user,
                "name": None,
                "message": "Hết thời gian chờ kết nối (Timeout)."
            }
        except Exception as e:
            return {
                "status": "Error",
                "uid": c_user,
                "name": None,
                "message": f"Lỗi kiểm tra: {str(e)}"
            }

    @classmethod
    def import_account(cls, cookie_raw: str, proxy: str = None, name: str = None, auto_check: bool = True) -> Dict[str, Any]:
        """
        Imports an account from cookie string/JSON, optionally checking status immediately.
        """
        cookie_dict = parse_cookie_input(cookie_raw)
        c_user, xs = extract_c_user_and_xs(cookie_dict)
        if not c_user:
            raise ValueError("Không tìm thấy c_user (UID) trong Cookie đã nhập.")

        account_name = name or f"Account_{c_user}"
        status = "Unknown"

        if auto_check:
            check_result = cls.check_cookie_status_http(cookie_raw, proxy)
            status = check_result["status"]
            if check_result.get("name") and not name:
                account_name = check_result["name"]

        account_id = AccountModel.create_or_update(
            name=account_name,
            uid=c_user,
            cookie_raw=cookie_raw,
            proxy=proxy,
            notes=None
        )

        AccountModel.update_status(account_id, status, datetime.now())
        return {
            "id": account_id,
            "uid": c_user,
            "name": account_name,
            "status": status,
            "proxy": proxy
        }

    @classmethod
    def recheck_account(cls, account_id: int) -> Dict[str, Any]:
        """Re-checks an existing account by its database ID."""
        acc = AccountModel.get_by_id(account_id)
        if not acc:
            raise ValueError(f"Không tìm thấy tài khoản ID {account_id}")

        result = cls.check_cookie_status_http(acc["cookie_raw"], acc.get("proxy"))
        AccountModel.update_status(account_id, result["status"], datetime.now())
        if result.get("name") and (acc["name"].startswith("Account_") or acc["name"].startswith("FB_")):
            # Update name if previously generic
            with AccountModel.get_by_id(account_id):
                from database.connection import get_db
                with get_db() as conn:
                    conn.execute("UPDATE accounts SET name = ? WHERE id = ?", (result["name"], account_id))

        return {
            "id": account_id,
            "status": result["status"],
            "name": result.get("name") or acc["name"],
            "message": result["message"]
        }
