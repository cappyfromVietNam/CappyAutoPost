"""
CappyAutoPost - Campaign Worker & Multi-Account Dispatcher
Executes posting campaigns in a managed background thread:
- Rotates accounts intelligently on limit or checkpoint
- Emits real-time progress events to UI
- Respects safe human delays and error recovery
"""
import time
import threading
import logging
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime

from core.browser import BrowserManager
from core.fb_actions import FacebookActions
from core.spintax import SpintaxEngine
from core.human_behavior import HumanSimulator
from database.models import AccountModel, GroupModel, PostModel, HistoryModel

logger = logging.getLogger("CampaignWorker")

class CampaignWorker:
    def __init__(
        self,
        account_ids: List[int],
        group_ids: List[int],
        post_id: int,
        min_delay: int = 180,
        max_delay: int = 360,
        safe_wait_seconds: int = 0,
        max_posts_per_account: int = 5,
        skip_already_posted: bool = True,
        cooldown_hours: int = 24,
        check_fb_live: bool = True,
        headless: bool = True,
        on_event: Optional[Callable[[str, Dict[str, Any]], None]] = None
    ):
        self.account_ids = account_ids
        self.group_ids = group_ids
        self.post_id = post_id
        self.min_delay = max(0, int(min_delay))
        self.max_delay = max(self.min_delay, int(max_delay))
        self.safe_wait_seconds = max(0, int(safe_wait_seconds))
        self.max_posts_per_account = max_posts_per_account
        self.skip_already_posted = bool(skip_already_posted)
        self.cooldown_hours = max(0, int(cooldown_hours))
        self.check_fb_live = bool(check_fb_live)
        self.headless = headless
        self.on_event = on_event or (lambda event, data: None)

        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.is_running = False

    def emit(self, event_name: str, **kwargs):
        """Emits an event to the UI callback."""
        payload = {"timestamp": datetime.now().strftime("%H:%M:%S"), **kwargs}
        try:
            self.on_event(event_name, payload)
        except Exception as e:
            logger.error(f"Error in on_event callback: {e}")

    def start(self):
        """Starts the campaign thread."""
        if self.is_running:
            return
        self._stop_event.clear()
        self._pause_event.clear()
        self.is_running = True
        self._thread = threading.Thread(target=self._run_campaign, daemon=True)
        self._thread.start()

    def stop(self):
        """Signals the campaign thread to gracefully stop."""
        self._stop_event.set()
        self._pause_event.clear()
        self.is_running = False
        self.emit("log", message="[Hệ thống] Đang dừng chiến dịch...", level="warning")

    def pause(self):
        """Pauses the worker."""
        self._pause_event.set()
        self.emit("log", message="[Hệ thống] Đã tạm dừng chiến dịch.", level="info")

    def resume(self):
        """Resumes the worker."""
        self._pause_event.clear()
        self.emit("log", message="[Hệ thống] Tiếp tục chiến dịch.", level="info")

    def _run_campaign(self):
        try:
            post = PostModel.get_by_id(self.post_id)
            if not post:
                self.emit("log", message=f"[Lỗi] Không tìm thấy bài viết ID {self.post_id}", level="error")
                self.emit("finished", success=False)
                return

            accounts = [AccountModel.get_by_id(aid) for aid in self.account_ids]
            accounts = [a for a in accounts if a and a.get("status") != "Die"]

            if not accounts:
                self.emit("log", message="[Lỗi] Không có tài khoản khả dụng nào để chạy.", level="error")
                self.emit("finished", success=False)
                return

            groups = [g for g in GroupModel.get_all() if g["id"] in self.group_ids]
            if not groups:
                self.emit("log", message="[Lỗi] Danh sách nhóm trống.", level="error")
                self.emit("finished", success=False)
                return

            total_targets = len(groups)
            self.emit("log", message=f"Khởi động chiến dịch: {len(accounts)} tài khoản x {total_targets} nhóm.", level="info")
            self.emit("progress", current=0, total=total_targets)

            current_account_idx = 0
            posts_with_current_acc = 0
            browser_mgr: Optional[BrowserManager] = None
            driver = None
            fb: Optional[FacebookActions] = None

            processed_groups = 0

            for group_idx, group in enumerate(groups):
                if self._stop_event.is_set():
                    break

                while self._pause_event.is_set():
                    time.sleep(1)
                    if self._stop_event.is_set():
                        break

                if self._stop_event.is_set():
                    break

                group_name = group.get("name") or group["url"]

                # 1. Instant DB Cooldown Check (avoids opening browser if already posted recently)
                if self.skip_already_posted and self.cooldown_hours > 0:
                    recent_post = HistoryModel.has_recent_post_in_group(group["id"], hours=self.cooldown_hours)
                    if recent_post:
                        status_label = "đang chờ duyệt" if recent_post["status"] == "Pending_Approval" else "đã đăng"
                        self.emit(
                            "log",
                            message=f"[{group_idx + 1}/{total_targets}] Bỏ qua nhóm {group_name} ({status_label} lúc {recent_post['posted_at']} UTC bởi {recent_post['account_name']}).",
                            level="warning"
                        )
                        processed_groups += 1
                        self.emit("progress", current=processed_groups, total=total_targets)
                        continue

                # Check if need to rotate account
                if driver is None or posts_with_current_acc >= self.max_posts_per_account:
                    if driver:
                        self.emit("log", message=f"Tài khoản đã đăng {posts_with_current_acc} bài. Tiến hành đổi tài khoản...", level="info")
                        browser_mgr.close()
                        driver = None
                        fb = None
                        posts_with_current_acc = 0
                        current_account_idx = (current_account_idx + 1) % len(accounts)

                    curr_acc = accounts[current_account_idx]
                    self.emit("log", message=f"Đăng nhập tài khoản: {curr_acc['name']} ({curr_acc['uid']})...", level="info")

                    browser_mgr = BrowserManager(proxy_str=curr_acc.get("proxy"), headless=self.headless)
                    driver = browser_mgr.start()
                    fb = FacebookActions(driver)

                    login_ok = fb.inject_cookies_and_login(curr_acc["cookie_raw"])
                    if not login_ok:
                        self.emit("log", message=f"Tài khoản {curr_acc['name']} đăng nhập thất bại / Checkpoint!", level="error")
                        AccountModel.update_status(curr_acc["id"], "Checkpoint")
                        browser_mgr.close()
                        driver = None
                        fb = None
                        # Remove bad account from rotation
                        accounts.pop(current_account_idx)
                        if not accounts:
                            self.emit("log", message="Tất cả tài khoản đều bị lỗi đăng nhập. Dừng chiến dịch.", level="error")
                            break
                        current_account_idx = current_account_idx % len(accounts)
                        continue

                curr_acc = accounts[current_account_idx]
                group_name = group.get("name") or group["url"]
                self.emit("log", message=f"[{group_idx + 1}/{total_targets}] Đang mở nhóm: {group_name}...", level="info")

                # Navigate to Group
                nav_ok = fb.open_group(group["url"])
                if not nav_ok:
                    self.emit("log", message=f"Không mở được nhóm {group_name}. Bỏ qua.", level="warning")
                    HistoryModel.add(curr_acc["id"], group["id"], post["id"], "Failed", "Không mở được URL nhóm")
                    processed_groups += 1
                    self.emit("progress", current=processed_groups, total=total_targets)
                    continue

                # 2. Live Facebook Group Scan (optional when skip_already_posted is active)
                if self.skip_already_posted and self.check_fb_live and self.cooldown_hours > 0:
                    self.emit("log", message=f"Đang quét kiểm tra bài đã đăng tại {group_name}...", level="info")
                    dup_check = fb.check_already_posted_in_group(
                        group_url=group["url"],
                        uid=curr_acc.get("uid"),
                        cooldown_hours=self.cooldown_hours,
                        deep_scan=True
                    )
                    if dup_check.get("already_posted"):
                        if dup_check.get("requires_approval"):
                            GroupModel.update_attributes(group["id"], requires_approval=True)
                        self.emit(
                            "log",
                            message=f"[{group_idx + 1}/{total_targets}] Bỏ qua nhóm {group_name}: {dup_check.get('reason')}",
                            level="warning"
                        )
                        processed_groups += 1
                        self.emit("progress", current=processed_groups, total=total_targets)
                        continue

                # Find post box
                box_ok = fb.find_and_click_post_box()
                if not box_ok:
                    self.emit("log", message=f"Không tìm thấy ô tạo bài viết tại nhóm {group_name}.", level="warning")
                    HistoryModel.add(curr_acc["id"], group["id"], post["id"], "Failed", "Không tìm thấy nút tạo bài")
                    processed_groups += 1
                    self.emit("progress", current=processed_groups, total=total_targets)
                    continue

                # Toggle anonymous if needed
                if post.get("use_anonymous") or group.get("allow_anonymous"):
                    self.emit("log", message="Đang thử bật chế độ đăng ẩn danh...", level="info")
                    fb.toggle_anonymous_mode()

                # Process Spintax
                final_content = SpintaxEngine.process(post["content_spintax"])
                self.emit("log", message="Đang nhập nội dung bài viết (Spintax tự nhiên)...", level="info")
                content_ok = fb.enter_content_lexical(final_content)

                if not content_ok:
                    self.emit("log", message="Lỗi khi điền nội dung vào trình soạn thảo.", level="error")
                    HistoryModel.add(curr_acc["id"], group["id"], post["id"], "Failed", "Lỗi nhập nội dung")
                    processed_groups += 1
                    self.emit("progress", current=processed_groups, total=total_targets)
                    continue

                # Upload images if any
                images = post.get("image_paths") or []
                if images:
                    self.emit("log", message=f"Đang tải lên {len(images)} hình ảnh đính kèm...", level="info")
                    fb.upload_images(images)

                # Submit Post
                self.emit("log", message="Đang nhấn Đăng bài...", level="info")
                result = fb.submit_post()
                post_status = result["status"]
                post_msg = result["message"]

                if post_status == "Success":
                    self.emit("log", message=f"Đăng thành công lên nhóm: {group_name}!", level="success")
                    HistoryModel.add(curr_acc["id"], group["id"], post["id"], "Success", post_msg)
                    AccountModel.increment_post_count(curr_acc["id"])
                    posts_with_current_acc += 1
                elif post_status == "Pending_Approval":
                    self.emit("log", message=f"Đã gửi bài lên nhóm: {group_name} (Đang chờ Quản trị viên duyệt).", level="warning")
                    HistoryModel.add(curr_acc["id"], group["id"], post["id"], "Pending_Approval", post_msg)
                    GroupModel.update_attributes(group["id"], requires_approval=True)
                    AccountModel.increment_post_count(curr_acc["id"])
                    posts_with_current_acc += 1
                else:
                    self.emit("log", message=f"Đăng thất bại lên nhóm {group_name}: {post_msg}", level="error")
                    HistoryModel.add(curr_acc["id"], group["id"], post["id"], "Failed", post_msg)

                processed_groups += 1
                self.emit("progress", current=processed_groups, total=total_targets)

                # Safe Gaussian Delay + Configured Safe Wait before next group if not last
                if group_idx < total_targets - 1 and not self._stop_event.is_set():
                    rand_delay = HumanSimulator.compute_gaussian_delay(self.min_delay, self.max_delay)
                    total_wait = max(0, int(round(rand_delay)) + self.safe_wait_seconds)
                    if total_wait > 0:
                        self.emit("log", message=f"Chờ an toàn {total_wait}s trước nhóm tiếp theo...", level="info")
                        elapsed = 0.0
                        while elapsed < total_wait:
                            if self._stop_event.is_set():
                                break
                            while self._pause_event.is_set():
                                if self._stop_event.is_set():
                                    break
                                time.sleep(0.5)
                            time.sleep(0.5)
                            elapsed += 0.5

        except Exception as e:
            logger.exception("Unexpected exception in campaign run")
            self.emit("log", message=f"[Ngoại lệ hệ thống] {str(e)}", level="error")
        finally:
            if browser_mgr:
                try:
                    browser_mgr.close()
                except Exception:
                    pass
            self.is_running = False
            self.emit("log", message="Chiến dịch đã hoàn tất hoặc dừng lại.", level="info")
            self.emit("finished", success=True)
