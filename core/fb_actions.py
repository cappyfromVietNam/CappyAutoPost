"""
CappyAutoPost - Facebook Automation Actions
Handles:
- Cookie injection and session validation
- Group navigation and status checks
- Lexical React Editor text injection (preserving emojis & newlines)
- Anonymous post toggle
- Multi-image uploads
- Post submission and approval detection
"""
import os
import re
import time
import logging
from typing import Dict, Any, List, Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from core.cookie_helper import parse_cookie_input, cookie_dict_to_selenium_list
from core.human_behavior import HumanSimulator

logger = logging.getLogger("CappyFB")

class FacebookActions:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 12)

    def inject_cookies_and_login(self, cookie_raw: str) -> bool:
        """
        Navigates to facebook.com and injects cookies into the browser session.
        """
        cookie_dict = parse_cookie_input(cookie_raw)
        if not cookie_dict:
            logger.error("Empty or invalid cookie string provided.")
            return False

        # Navigate to Facebook root first to set domain cookies
        self.driver.get("https://www.facebook.com/")
        time.sleep(2)

        selenium_cookies = cookie_dict_to_selenium_list(cookie_dict)
        for cookie in selenium_cookies:
            try:
                self.driver.add_cookie(cookie)
            except Exception as e:
                logger.debug(f"Could not add cookie {cookie.get('name')}: {e}")

        # Refresh page to apply session
        self.driver.get("https://www.facebook.com/")
        time.sleep(3)

        # Check if login succeeded
        current_url = self.driver.current_url.lower()
        if "login" in current_url or "checkpoint" in current_url:
            logger.warning("Session checkpoint or login redirect detected.")
            return False

        return True

    def open_group(self, group_url: str) -> bool:
        """Navigates to a specific group URL and verifies page readiness."""
        clean_url = group_url.strip()
        if not clean_url.startswith("http"):
            clean_url = f"https://www.facebook.com/groups/{clean_url}"
        
        self.driver.get(clean_url)
        time.sleep(random_delay := HumanSimulator.smart_sleep(4.0, 1.0, 2.5))
        
        current_url = self.driver.current_url.lower()
        if "checkpoint" in current_url or "login" in current_url:
            return False

        # Smooth scroll slightly to trigger Facebook feed loading
        HumanSimulator.smooth_scroll(self.driver, scroll_amount=250, steps=3)
        return True

    def find_and_click_post_box(self) -> bool:
        """
        Finds the 'Write something...' trigger button using multi-tier XPath selectors.
        Uses JavaScript clicks to prevent mouse hijacking and element click interception.
        """
        selectors = [
            # Tier 1: Vietnamese & English text triggers
            "//span[contains(text(), 'Bạn viết gì đi') or contains(text(), 'Write something')]",
            "//span[contains(text(), 'Tạo bài viết công khai') or contains(text(), 'Create a public post')]",
            "//span[contains(text(), 'Hãy viết gì đó') or contains(text(), 'Write a public post')]",
            # Tier 2: Role button containing text triggers
            "//div[@role='button']//span[contains(text(), 'Bạn viết gì đi') or contains(text(), 'Write something')]",
            # Tier 3: Search within main pagelet for trigger input
            "//div[@role='main']//div[@role='button' and contains(., 'viết')]",
            "//div[@role='main']//div[@role='button' and contains(., 'Write')]"
        ]

        for xpath in selectors:
            try:
                elements = self.driver.find_elements(By.XPATH, xpath)
                for el in elements:
                    if el.is_displayed():
                        # Use JavaScript click to avoid moving physical mouse and prevent overlay interception
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'}); arguments[0].click();", el)
                        time.sleep(2.5)
                        return True
            except Exception:
                continue

        return False

    def toggle_anonymous_mode(self) -> bool:
        """
        Attempts to toggle 'Post Anonymously' if available in the post dialog.
        """
        anon_selectors = [
            "//span[contains(text(), 'Đăng ẩn danh') or contains(text(), 'Post anonymously')]",
            "//div[@role='button']//span[contains(text(), 'ẩn danh') or contains(text(), 'Anonymous')]"
        ]

        for xpath in anon_selectors:
            try:
                elements = self.driver.find_elements(By.XPATH, xpath)
                for el in elements:
                    if el.is_displayed():
                        self.driver.execute_script("arguments[0].click();", el)
                        time.sleep(1.5)
                        # Look for confirmation dialog button (e.g., 'Tôi muốn đăng ẩn danh' / 'I want to post anonymously')
                        confirm_btn = self.driver.find_elements(
                            By.XPATH, 
                            "//div[@aria-label='Tôi muốn đăng ẩn danh' or @aria-label='I want to post anonymously' or contains(., 'Tôi muốn')]"
                        )
                        for c_btn in confirm_btn:
                            if c_btn.is_displayed():
                                self.driver.execute_script("arguments[0].click();", c_btn)
                                time.sleep(1)
                                break
                        return True
            except Exception:
                continue

        return False

    def enter_content_lexical(self, text: str) -> bool:
        """
        Injects text into Facebook's Lexical/Draft.js contenteditable editor.
        Excludes comment boxes and operates via DOM-level focus (never steals mouse or focus).
        """
        editor_selectors = [
            # 1. Inside modal dialog (post creation popup - highest priority)
            "//div[@role='dialog']//div[@role='textbox' and @contenteditable='true' and not(contains(@aria-label, 'Bình luận')) and not(contains(@aria-placeholder, 'Bình luận')) and not(contains(@aria-label, 'Comment'))]",
            "//div[@role='dialog']//div[@contenteditable='true' and @data-lexical-editor='true']",
            "//div[@role='dialog']//div[contains(@class, 'notranslate') and @role='textbox' and not(contains(@aria-label, 'Bình luận'))]",
            # 2. Main post area (if inline on feed)
            "//div[@role='main']//div[@role='textbox' and @contenteditable='true' and not(contains(@aria-label, 'Bình luận')) and not(contains(@aria-placeholder, 'Bình luận')) and not(contains(@aria-label, 'Comment'))]",
            # 3. Fallback: Any contenteditable textbox that is strictly NOT a comment box
            "//div[@role='textbox' and @contenteditable='true' and not(contains(@aria-label, 'Bình luận')) and not(contains(@aria-placeholder, 'Bình luận')) and not(contains(@aria-label, 'Comment')) and not(contains(@aria-placeholder, 'Comment'))]"
        ]

        editor = None
        for xpath in editor_selectors:
            try:
                elements = self.driver.find_elements(By.XPATH, xpath)
                for el in elements:
                    if el.is_displayed():
                        # Additional safety check against comment box
                        aria_label = (el.get_attribute("aria-label") or "").lower()
                        aria_placeholder = (el.get_attribute("aria-placeholder") or "").lower()
                        if "bình luận" in aria_label or "comment" in aria_label or "bình luận" in aria_placeholder or "comment" in aria_placeholder:
                            continue
                        editor = el
                        break
                if editor:
                    break
            except Exception:
                continue

        if not editor:
            logger.error("Could not find post creation editor element (excluding comment boxes).")
            return False

        try:
            # Focus & click purely via JavaScript - NO physical mouse movement, NO click intercepted error!
            self.driver.execute_script("""
                arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});
                arguments[0].focus();
                arguments[0].click();
            """, editor)
            time.sleep(0.5)

            # Split content by newlines
            lines = text.split("\n")

            for line_idx, line in enumerate(lines):
                if line:
                    # Method: insertText via JS execCommand ensures emojis and full Unicode text work flawlessly
                    self.driver.execute_script("document.execCommand('insertText', false, arguments[0]);", line)
                    # Natural human pause after a sentence/line
                    delay = HumanSimulator.get_keystroke_delay(".")
                    time.sleep(delay)

                # Send Shift+Enter for newline inside Facebook's editor directly to the focused editor
                if line_idx < len(lines) - 1:
                    editor.send_keys(Keys.SHIFT, Keys.ENTER)
                    time.sleep(0.2)

            time.sleep(1)
            return True

        except Exception as e:
            logger.error(f"Error entering content: {e}")
            return False

    def upload_images(self, image_paths: List[str]) -> bool:
        """
        Uploads local image files using the post modal's file input element.
        Strictly targets inputs inside the active post dialog (excluding comment inputs),
        clicks the Photo/Video trigger if hidden, and handles single vs multiple inputs safely.
        """
        valid_paths = [os.path.abspath(p) for p in image_paths if p and os.path.exists(p)]
        if not valid_paths:
            return True

        def _find_dialog_file_inputs():
            # 1. Highest priority: multi-file input inside active post dialog
            inputs = self.driver.find_elements(By.XPATH, "//div[@role='dialog']//input[@type='file' and @multiple]")
            if inputs:
                return inputs
            # 2. Any file input inside active post dialog
            inputs = self.driver.find_elements(By.XPATH, "//div[@role='dialog']//input[@type='file']")
            if inputs:
                return inputs
            return []

        try:
            file_inputs = _find_dialog_file_inputs()

            if not file_inputs:
                # Click Photo/video button inside the modal to reveal/mount the file input
                photo_triggers = self.driver.find_elements(
                    By.XPATH,
                    "//div[@role='dialog']//div[@aria-label='Ảnh/video' or @aria-label='Photo/video' or contains(@aria-label, 'Ảnh') or contains(@aria-label, 'Photo')]"
                )
                for pt in photo_triggers:
                    if pt.is_displayed():
                        self.driver.execute_script("arguments[0].click();", pt)
                        time.sleep(1.5)
                        break
                file_inputs = _find_dialog_file_inputs()

            if not file_inputs:
                # Fallback: multi-file input anywhere in main post composer
                file_inputs = self.driver.find_elements(By.XPATH, "//div[@role='main']//input[@type='file' and @multiple]")

            if not file_inputs:
                logger.warning("Could not find file input inside post dialog for photo upload.")
                return False

            target_input = file_inputs[0]
            supports_multiple = target_input.get_attribute("multiple") is not None

            if supports_multiple or len(valid_paths) == 1:
                combined_paths = "\n".join(valid_paths)
                target_input.send_keys(combined_paths)
            else:
                # Input does not have 'multiple' attribute -> upload one by one safely
                for idx, path in enumerate(valid_paths):
                    current_inputs = _find_dialog_file_inputs() or file_inputs
                    current_inputs[0].send_keys(path)
                    time.sleep(1.5)

            # Wait for image thumbnails/upload to complete
            time.sleep(3 + len(valid_paths) * 1.5)
            return True

        except Exception as e:
            logger.error(f"Failed to upload images: {e}")
            return False

    def submit_post(self) -> Dict[str, Any]:
        """
        Finds and clicks the 'Post' button, then determines if the post succeeded or requires approval.
        Uses JavaScript click to guarantee execution without interception.
        """
        post_btn_selectors = [
            "//div[@aria-label='Đăng' or @aria-label='Post' or @aria-label='Submit' or @aria-label='Gửi bài']",
            "//div[@role='button']//span[text()='Đăng' or text()='Post' or text()='Gửi bài']/ancestor::div[@role='button']"
        ]

        post_button = None
        for xpath in post_btn_selectors:
            try:
                elements = self.driver.find_elements(By.XPATH, xpath)
                for el in elements:
                    if el.is_displayed() and el.is_enabled():
                        # Make sure it's not aria-disabled='true'
                        if el.get_attribute("aria-disabled") != "true":
                            post_button = el
                            break
                if post_button:
                    break
            except Exception:
                continue

        if not post_button:
            return {"status": "Failed", "message": "Nút 'Đăng' không sẵn sàng hoặc bị vô hiệu hóa."}

        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'}); arguments[0].click();", post_button)
            time.sleep(4)

            # Wait for modal dialog to disappear or confirmation notice
            page_text = self.driver.page_source.lower()
            
            # Detect Pending Approval message
            approval_keywords = [
                "phê duyệt", "chờ duyệt", "pending approval", "đang chờ quản trị viên", "submitted to admin"
            ]
            for kw in approval_keywords:
                if kw in page_text:
                    return {
                        "status": "Pending_Approval",
                        "message": "Bài viết đã gửi và đang chờ Quản trị viên nhóm phê duyệt."
                    }

            return {
                "status": "Success",
                "message": "Đăng bài thành công!"
            }

        except Exception as e:
            return {"status": "Failed", "message": f"Lỗi khi nhấn Đăng: {str(e)}"}

    @staticmethod
    def is_relative_time_within_hours(text: str, cooldown_hours: int) -> bool:
        """
        Parses Vietnamese/English Facebook relative timestamps (e.g. 'Vừa xong', '15 phút',
        '2 giờ', '3 hrs', 'Hôm qua', '2d') and returns True if within `cooldown_hours`.
        """
        if not text or int(cooldown_hours) <= 0:
            return False

        norm = " ".join(text.lower().strip().split())
        if not norm:
            return False

        # Immediate timestamps
        immediate_kw = ("vừa xong", "just now", "vài giây", "a moment ago", "a few seconds ago")
        if any(kw in norm for kw in immediate_kw):
            return True

        # Seconds
        sec_match = re.search(r"\b(\d+)\s*(?:giây|secs?|seconds?|s)\b", norm)
        if sec_match:
            return True

        # Minutes
        min_match = re.search(r"\b(\d+)\s*(?:phút|mins?|minutes?|m|p)\b", norm)
        if min_match:
            mins = int(min_match.group(1))
            return mins <= int(cooldown_hours) * 60

        # Hours
        hr_match = re.search(r"\b(\d+)\s*(?:giờ|hrs?|hours?|h)\b", norm)
        if hr_match:
            hrs = int(hr_match.group(1))
            return hrs <= int(cooldown_hours)

        # Yesterday (~24h)
        if "hôm qua" in norm or "yesterday" in norm:
            return int(cooldown_hours) >= 24

        # Days
        day_match = re.search(r"\b(\d+)\s*(?:ngày|days?|d)\b", norm)
        if day_match:
            days = int(day_match.group(1))
            return (days * 24) <= int(cooldown_hours)

        return False

    def check_already_posted_in_group(
        self,
        group_url: str,
        uid: Optional[str] = None,
        cooldown_hours: int = 24,
        deep_scan: bool = True
    ) -> Dict[str, Any]:
        """
        Live scan on the opened Facebook group page (and optionally /my_posted_content)
        to detect pending posts or recently published posts within `cooldown_hours`.
        Returns {"already_posted": bool, "reason": str, "requires_approval": bool}.
        """
        if int(cooldown_hours) <= 0:
            return {"already_posted": False, "reason": "", "requires_approval": False}

        clean_uid = str(uid).strip() if uid else ""

        # Phase A: Quick check on the currently opened group page
        try:
            main_els = self.driver.find_elements(By.XPATH, "//div[@role='main']")
            main_text = (main_els[0].text if main_els else self.driver.find_element(By.TAG_NAME, "body").text).lower()
        except Exception:
            main_text = ""

        pending_banner_phrases = [
            "bài viết của bạn đang chờ",
            "bạn có 1 bài viết đang chờ",
            "bài viết đang chờ phê duyệt",
            "đang chờ quản trị viên phê duyệt",
            "your post is pending",
            "you have 1 pending post",
            "pending admin approval",
        ]
        for phrase in pending_banner_phrases:
            if phrase in main_text:
                return {
                    "already_posted": True,
                    "reason": "Phát hiện bài viết đang chờ duyệt trên trang nhóm.",
                    "requires_approval": True,
                }

        # Check top feed articles for current account UID + recent timestamp
        if clean_uid:
            try:
                articles = self.driver.find_elements(By.XPATH, "//div[@role='main']//div[@role='article']")[:6]
                for article in articles:
                    links = article.find_elements(By.TAG_NAME, "a")
                    author_matched = False
                    recent_time_found = False
                    for link in links:
                        href = (link.get_attribute("href") or "").lower()
                        if f"/user/{clean_uid.lower()}" in href or f"id={clean_uid.lower()}" in href or f"facebook.com/{clean_uid.lower()}" in href:
                            author_matched = True
                        link_text = (link.text or "").strip()
                        if link_text and len(link_text) <= 32 and self.is_relative_time_within_hours(link_text, cooldown_hours):
                            recent_time_found = True

                    if author_matched:
                        if not recent_time_found:
                            # Also check span timestamps inside the article
                            spans = article.find_elements(By.TAG_NAME, "span")
                            for sp in spans[:20]:
                                sp_text = (sp.text or "").strip()
                                if sp_text and len(sp_text) <= 32 and self.is_relative_time_within_hours(sp_text, cooldown_hours):
                                    recent_time_found = True
                                    break
                        if recent_time_found:
                            return {
                                "already_posted": True,
                                "reason": f"Phát hiện bài đăng gần đây của UID {clean_uid} trong bảng tin nhóm.",
                                "requires_approval": False,
                            }
            except Exception as e:
                logger.debug(f"Quick feed scan warning: {e}")

        if not deep_scan:
            return {"already_posted": False, "reason": "", "requires_approval": False}

        # Phase B: Deep scan via /my_posted_content tab of the group
        base_url = group_url.split("?")[0].rstrip("/")
        if not base_url.startswith(("http://", "https://")):
            return {"already_posted": False, "reason": "", "requires_approval": False}

        my_posted_url = f"{base_url}/my_posted_content"
        try:
            self.driver.get(my_posted_url)
            time.sleep(2.5)

            curr_url = (self.driver.current_url or "").lower()
            if "login" in curr_url or "checkpoint" in curr_url:
                logger.debug("Redirected during my_posted_content scan; failing open.")
                return {"already_posted": False, "reason": "", "requires_approval": False}

            # Check if pending badge count > 0, e.g., "Đang chờ · 1" or "Pending (1)"
            main_els = self.driver.find_elements(By.XPATH, "//div[@role='main']")
            my_text = (main_els[0].text if main_els else self.driver.find_element(By.TAG_NAME, "body").text).lower()

            if re.search(r"(?:đang chờ|pending)\s*[·:(]\s*[1-9]\d*", my_text):
                return {
                    "already_posted": True,
                    "reason": "Phát hiện bài viết đang chờ duyệt trong mục Nội dung của bạn.",
                    "requires_approval": True,
                }

            articles = self.driver.find_elements(By.XPATH, "//div[@role='main']//div[@role='article']")[:6]
            for article in articles:
                art_text = (article.text or "").lower()
                if any(kw in art_text for kw in ("đang chờ quản trị viên", "đang chờ duyệt", "pending approval", "awaiting approval")):
                    return {
                        "already_posted": True,
                        "reason": "Phát hiện bài viết đang chờ duyệt trong Nội dung của bạn.",
                        "requires_approval": True,
                    }

                # Check timestamps inside article
                candidate_els = article.find_elements(By.XPATH, ".//a | .//span")[:25]
                for el in candidate_els:
                    t = (el.text or "").strip()
                    if t and len(t) <= 32 and self.is_relative_time_within_hours(t, cooldown_hours):
                        return {
                            "already_posted": True,
                            "reason": f"Đã có bài đăng gần đây ({t}) trong Nội dung của bạn.",
                            "requires_approval": False,
                        }

            # Clear: navigate back to main group page so composer is ready
            self.open_group(group_url)
            return {"already_posted": False, "reason": "", "requires_approval": False}

        except Exception as e:
            logger.debug(f"Deep scan my_posted_content warning (fail-open): {e}")
            try:
                self.open_group(group_url)
            except Exception:
                pass
            return {"already_posted": False, "reason": "", "requires_approval": False}
