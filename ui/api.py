"""
CappyAutoPost - PyWebView JS-Python Bridge API
Exposes secure backend methods to the frontend user interface.
"""
import os
import json
import webview
from typing import Dict, Any, List, Optional
from database.models import AccountModel, GroupModel, PostModel, HistoryModel, SettingsModel
from services.account_service import AccountService
from services.group_service import GroupService
from services.campaign_worker import CampaignWorker
from core.spintax import SpintaxEngine

class WebviewAPI:
    def __init__(self):
        self._window: Optional[webview.Window] = None
        self.active_worker: Optional[CampaignWorker] = None

    def set_window(self, window: webview.Window):
        self._window = window

    def _emit_to_frontend(self, event_name: str, data: Any):
        """Dispatches an event directly into the Webview JavaScript context."""
        if self._window:
            try:
                js_code = f"window.onBackendEvent({json.dumps(event_name)}, {json.dumps(data)});"
                self._window.evaluate_js(js_code)
            except Exception as e:
                print(f"Error evaluating JS: {e}")

    # ==================== DASHBOARD ====================
    def get_dashboard_stats(self) -> Dict[str, Any]:
        return HistoryModel.get_statistics()

    # ==================== ACCOUNTS ====================
    def get_accounts(self) -> List[Dict[str, Any]]:
        return AccountModel.get_all()

    def import_accounts(self, raw_input: str, auto_check: bool = True) -> Dict[str, Any]:
        """
        Supports multi-line input:
        - Format 1: cookie_string (one per line)
        - Format 2: cookie_string|proxy (one per line)
        - Format 3: JSON array
        """
        imported = 0
        errors = 0
        lines = raw_input.strip().splitlines()

        # Handle full JSON array input
        if raw_input.strip().startswith("[") and raw_input.strip().endswith("]"):
            try:
                AccountService.import_account(raw_input, auto_check=auto_check)
                return {"success": True, "count": 1, "message": "Đã nhập tài khoản từ định dạng JSON."}
            except Exception as e:
                return {"success": False, "count": 0, "message": str(e)}

        for line in lines:
            line = line.strip()
            if not line:
                continue
            proxy = None
            cookie = line
            if "|" in line:
                parts = line.split("|")
                cookie = parts[0].strip()
                if len(parts) > 1 and parts[1].strip():
                    proxy = parts[1].strip()

            try:
                AccountService.import_account(cookie_raw=cookie, proxy=proxy, auto_check=auto_check)
                imported += 1
            except Exception:
                errors += 1

        return {
            "success": True,
            "count": imported,
            "errors": errors,
            "message": f"Đã nạp {imported} tài khoản thành công ({errors} lỗi)."
        }

    def check_account(self, account_id: int) -> Dict[str, Any]:
        return AccountService.recheck_account(account_id)

    def check_all_accounts(self) -> Dict[str, Any]:
        accounts = AccountModel.get_all()
        results = []
        for acc in accounts:
            try:
                res = AccountService.recheck_account(acc["id"])
                results.append(res)
            except Exception as e:
                results.append({"id": acc["id"], "status": "Error", "message": str(e)})
        return {"success": True, "results": results}

    def delete_account(self, account_id: int) -> bool:
        return AccountModel.delete(account_id)

    # ==================== GROUPS ====================
    def get_groups(self, category: str = None) -> List[Dict[str, Any]]:
        return GroupModel.get_all(category)

    def get_categories(self) -> List[str]:
        return GroupModel.get_categories()

    def import_groups(self, raw_text: str, category: str = "Chung", default_name: str = None) -> Dict[str, Any]:
        return GroupService.import_groups(raw_text, category, default_name)

    def delete_group(self, group_id: int) -> bool:
        return GroupModel.delete(group_id)

    # ==================== POSTS ====================
    def get_posts(self) -> List[Dict[str, Any]]:
        return PostModel.get_all()

    def get_post(self, post_id: int) -> Optional[Dict[str, Any]]:
        return PostModel.get_by_id(post_id)

    def save_post(self, data: Dict[str, Any]) -> Dict[str, Any]:
        post_id = data.get("id")
        title = data.get("title", "Bài viết mới")
        content = data.get("content_spintax", "")
        images = data.get("image_paths", [])
        use_anon = bool(data.get("use_anonymous", False))
        category = data.get("category", "Chung")

        saved_id = PostModel.save(
            title=title,
            content_spintax=content,
            image_paths=images,
            use_anonymous=use_anon,
            category=category,
            post_id=post_id
        )
        return {"success": True, "id": saved_id}

    def delete_post(self, post_id: int) -> bool:
        return PostModel.delete(post_id)

    def preview_spintax(self, content: str) -> str:
        return SpintaxEngine.process(content)

    def select_images(self) -> List[str]:
        """Native OS file dialog to select image files."""
        if not self._window:
            return []
        result = self._window.create_file_dialog(
            webview.FileDialog.OPEN,
            allow_multiple=True,
            file_types=('Hình ảnh (*.png;*.jpg;*.jpeg;*.webp)', 'Tất cả file (*.*)')
        )
        return list(result) if result else []

    # ==================== HISTORY ====================
    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        return HistoryModel.get_recent(limit)

    # ==================== CAMPAIGN RUNNER ====================
    def get_campaign_config(self) -> Dict[str, Any]:
        def _to_bool(val: Any, default: bool = True) -> bool:
            if val is None:
                return default
            if isinstance(val, bool):
                return val
            return str(val).strip().lower() in ("1", "true", "yes")

        return {
            "max_posts_per_account": int(SettingsModel.get("campaign_max_per_acc", 3)),
            "min_delay": int(SettingsModel.get("campaign_min_delay", 120)),
            "max_delay": int(SettingsModel.get("campaign_max_delay", 240)),
            "safe_wait_seconds": int(SettingsModel.get("campaign_safe_wait", 0)),
            "skip_already_posted": _to_bool(SettingsModel.get("campaign_skip_posted", True), True),
            "cooldown_hours": int(SettingsModel.get("campaign_cooldown_hours", 24)),
            "check_fb_live": _to_bool(SettingsModel.get("campaign_check_fb_live", True), True),
        }

    def save_campaign_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        max_per_acc = max(1, int(config.get("max_posts_per_account", 3)))
        min_delay = max(0, int(config.get("min_delay", 120)))
        max_delay = max(min_delay, int(config.get("max_delay", 240)))
        safe_wait = max(0, int(config.get("safe_wait_seconds", 0)))
        skip_posted = bool(config.get("skip_already_posted", True))
        cooldown_hours = max(1, int(config.get("cooldown_hours", 24)))
        check_fb_live = bool(config.get("check_fb_live", True))

        SettingsModel.set("campaign_max_per_acc", max_per_acc)
        SettingsModel.set("campaign_min_delay", min_delay)
        SettingsModel.set("campaign_max_delay", max_delay)
        SettingsModel.set("campaign_safe_wait", safe_wait)
        SettingsModel.set("campaign_skip_posted", skip_posted)
        SettingsModel.set("campaign_cooldown_hours", cooldown_hours)
        SettingsModel.set("campaign_check_fb_live", check_fb_live)
        return {"success": True}

    def start_campaign(self, config: Dict[str, Any]) -> Dict[str, Any]:
        if self.active_worker and (self.active_worker.is_running or (self.active_worker._thread and self.active_worker._thread.is_alive())):
            return {"success": False, "message": "Chiến dịch khác đang chạy hoặc đang đóng trình duyệt!"}

        account_ids = config.get("account_ids", [])
        group_ids = config.get("group_ids", [])
        post_id = config.get("post_id")
        min_delay = max(0, int(config.get("min_delay", 120)))
        max_delay = max(min_delay, int(config.get("max_delay", 240)))
        safe_wait = max(0, int(config.get("safe_wait_seconds", 0)))
        max_per_acc = max(1, int(config.get("max_posts_per_account", 5)))
        skip_posted = bool(config.get("skip_already_posted", True))
        cooldown_hours = max(1, int(config.get("cooldown_hours", 24)))
        check_fb_live = bool(config.get("check_fb_live", True))
        headless = bool(config.get("headless", True))

        if not account_ids:
            return {"success": False, "message": "Vui lòng chọn ít nhất 1 tài khoản."}
        if not group_ids:
            return {"success": False, "message": "Vui lòng chọn ít nhất 1 nhóm."}
        if not post_id:
            return {"success": False, "message": "Vui lòng chọn bài viết cần đăng."}

        # Persist user configuration automatically
        self.save_campaign_config({
            "max_posts_per_account": max_per_acc,
            "min_delay": min_delay,
            "max_delay": max_delay,
            "safe_wait_seconds": safe_wait,
            "skip_already_posted": skip_posted,
            "cooldown_hours": cooldown_hours,
            "check_fb_live": check_fb_live,
        })

        self.active_worker = CampaignWorker(
            account_ids=account_ids,
            group_ids=group_ids,
            post_id=post_id,
            min_delay=min_delay,
            max_delay=max_delay,
            safe_wait_seconds=safe_wait,
            max_posts_per_account=max_per_acc,
            skip_already_posted=skip_posted,
            cooldown_hours=cooldown_hours,
            check_fb_live=check_fb_live,
            headless=headless,
            on_event=self._emit_to_frontend
        )
        self.active_worker.start()
        return {"success": True, "message": "Chiến dịch đã được khởi chạy thành công!"}

    def pause_campaign(self) -> Dict[str, Any]:
        if self.active_worker and self.active_worker.is_running:
            self.active_worker.pause()
            return {"success": True, "message": "Đã tạm dừng chiến dịch."}
        return {"success": False, "message": "Không có chiến dịch nào đang chạy."}

    def resume_campaign(self) -> Dict[str, Any]:
        if self.active_worker and self.active_worker.is_running:
            self.active_worker.resume()
            return {"success": True, "message": "Đã tiếp tục chiến dịch."}
        return {"success": False, "message": "Không có chiến dịch nào đang chạy."}

    def stop_campaign(self) -> Dict[str, Any]:
        if self.active_worker and self.active_worker.is_running:
            self.active_worker.stop()
            return {"success": True, "message": "Đã gửi lệnh dừng chiến dịch."}
        return {"success": False, "message": "Không có chiến dịch nào đang chạy."}
