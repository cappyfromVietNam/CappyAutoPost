"""
CappyAutoPost - RULE.md Compliance Test Suite
Verifies all mandatory test requirements defined in RULE.md:
1. Cookie Parser (edge cases, delimiters, JSON, empty, malformed)
2. Spintax & Dynamic Variables (nested brackets, token substitutions, zero leftover brackets)
3. SQLite DB (CRUD, multi-threading, WAL mode, integrity)
4. Campaign Worker (threading, stop/pause events, cleanup)
5. Anti-Detection & Chrome Browser (navigator.webdriver check, profile cleanup)
"""
import os
import sys
import time
import unittest
import threading
from pathlib import Path

# Add project root to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from database import init_db, get_db, AccountModel, GroupModel, PostModel, HistoryModel
from core.cookie_helper import parse_cookie_input, extract_c_user_and_xs, format_proxy
from core.spintax import SpintaxEngine
from core.browser import BrowserManager
from services.campaign_worker import CampaignWorker
from services.group_service import GroupService

class TestRuleCompliance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    # ==================== TEST 1: COOKIE PARSER ====================
    def test_01_cookie_parser_edge_cases(self):
        """Test Cookie Parser across all mandated formats and edge cases."""
        # Case A: Standard String
        c1 = "c_user=100012345678; xs=38%3Afake_token%3A2; fr=0random_fr; sb=random_sb;"
        res1 = parse_cookie_input(c1)
        self.assertEqual(res1.get("c_user"), "100012345678")
        self.assertEqual(res1.get("xs"), "38%3Afake_token%3A2")

        # Case B: String containing pipes and proxies
        raw_with_proxy = "c_user=1000999888; xs=99%3Atoken%3A1|192.168.1.50:8080"
        cookie_part = raw_with_proxy.split("|")[0]
        res2 = parse_cookie_input(cookie_part)
        self.assertEqual(res2.get("c_user"), "1000999888")

        # Case C: JSON Array from Extension
        json_array = '[{"name": "c_user", "value": "1000444555"}, {"name": "xs", "value": "json_token"}]'
        res3 = parse_cookie_input(json_array)
        self.assertEqual(res3.get("c_user"), "1000444555")
        self.assertEqual(res3.get("xs"), "json_token")

        # Case D: Empty, None, Whitespace, Malformed
        self.assertEqual(parse_cookie_input(""), {})
        self.assertEqual(parse_cookie_input(None), {})
        self.assertEqual(parse_cookie_input("   \n\t  "), {})
        self.assertEqual(parse_cookie_input("malformed-no-equal-sign"), {})
        self.assertEqual(parse_cookie_input("====;;;==="), {})

        # Verify c_user & xs extraction handles missing fields safely
        uid, xs = extract_c_user_and_xs({"other_key": "val"})
        self.assertIsNone(uid)
        self.assertIsNone(xs)

    # ==================== TEST 2: SPINTAX & DYNAMIC VARS ====================
    def test_02_spintax_and_dynamic_variables(self):
        """Test deeply nested Spintax and dynamic variable substitutions."""
        # Deeply nested Spintax: 3 levels
        nested_template = "Xin chào {anh/chị|{bạn bè|{người anh em|đồng nghiệp}}}!"
        for _ in range(50):
            resolved = SpintaxEngine.process(nested_template)
            # Ensure NO leftover curly braces
            self.assertNotIn("{", resolved)
            self.assertNotIn("}", resolved)
            self.assertNotIn("|", resolved)
            self.assertTrue(any(w in resolved for w in ["anh/chị", "bạn bè", "người anh em", "đồng nghiệp"]))

        # Dynamic variable substitutions
        dynamic_template = "Đăng lúc {time} ngày {date} mã đơn {rand_id} số {rand_num}."
        processed = SpintaxEngine.process(dynamic_template)
        self.assertNotIn("{time}", processed)
        self.assertNotIn("{date}", processed)
        self.assertNotIn("{rand_id}", processed)
        self.assertNotIn("{rand_num}", processed)
        self.assertIn("#", processed)

    # ==================== TEST 3: SQLITE DB & CONCURRENCY ====================
    def test_03_sqlite_database_concurrency(self):
        """Test multi-threaded writes and WAL mode integrity."""
        errors = []

        def worker_task(thread_id: int):
            try:
                # Insert account
                uid = f"1000000{thread_id}"
                acc_id = AccountModel.create_or_update(
                    name=f"User Thread {thread_id}",
                    uid=uid,
                    cookie_raw=f"c_user={uid}; xs=thread_token;"
                )
                # Update status
                AccountModel.update_status(acc_id, "Live")
                # Add group
                grp_id = GroupModel.add(f"https://www.facebook.com/groups/thread_{thread_id}/", category="MultiThread")
                # Add post
                post_id = PostModel.save(f"Title {thread_id}", "Content Spintax")
                # Add history
                HistoryModel.add(acc_id, grp_id, post_id, "Success")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker_task, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Concurrent DB writes produced errors: {errors}")

        # Check stats
        stats = HistoryModel.get_statistics()
        self.assertGreaterEqual(stats["total_accounts"], 10)
        self.assertGreaterEqual(stats["total_groups"], 10)
        self.assertGreaterEqual(stats["history_success"], 10)

        # Cleanup test entries
        with get_db() as conn:
            conn.execute("DELETE FROM accounts WHERE name LIKE 'User Thread %'")
            conn.execute("DELETE FROM groups WHERE category = 'MultiThread'")
            conn.execute("DELETE FROM posts WHERE title LIKE 'Title %'")
            conn.execute("DELETE FROM posting_history WHERE error_message IS NULL AND status = 'Success'")

    # ==================== TEST 4: CAMPAIGN WORKER THREADING ====================
    def test_04_campaign_worker_threading_and_stop(self):
        """Test CampaignWorker lifecycle, pause, resume, and graceful stop."""
        events_received = []

        def event_listener(event_name, data):
            events_received.append((event_name, data))

        # Setup mock entities
        acc_id = AccountModel.create_or_update("Worker Acc", "88888888", "c_user=88888888; xs=mock_token;")
        AccountModel.update_status(acc_id, "Live")
        grp_id = GroupModel.add("https://www.facebook.com/groups/mock_worker_grp/", category="Test")
        post_id = PostModel.save("Worker Post", "Nội dung {A|B}")

        worker = CampaignWorker(
            account_ids=[acc_id],
            group_ids=[grp_id],
            post_id=post_id,
            min_delay=1,
            max_delay=2,
            on_event=event_listener
        )

        worker.start()
        self.assertTrue(worker.is_running)

        # Send pause and resume
        worker.pause()
        self.assertTrue(worker._pause_event.is_set())
        worker.resume()
        self.assertFalse(worker._pause_event.is_set())

        # Send stop signal immediately
        worker.stop()
        self.assertTrue(worker._stop_event.is_set())
        
        # Wait up to 5s for worker thread to terminate
        if worker._thread:
            worker._thread.join(timeout=5.0)

        self.assertFalse(worker.is_running)
        self.assertTrue(any(e[0] == "log" for e in events_received))

        # Cleanup
        AccountModel.delete(acc_id)
        GroupModel.delete(grp_id)
        PostModel.delete(post_id)

    # ==================== TEST 5: ANTI-DETECTION BROWSER ====================
    def test_05_anti_detection_and_cleanup(self):
        """
        Launches undetected-chromedriver in headless mode:
        1. Verifies browser starts with stealth arguments
        2. Executes JS to confirm anti-detection properties
        3. Closes driver and asserts temporary profile directory is completely purged.
        """
        browser_mgr = BrowserManager(headless=True)
        user_dir = None
        driver = None

        try:
            driver = browser_mgr.start()
            user_dir = browser_mgr.user_data_dir
            self.assertIsNotNone(user_dir)
            self.assertTrue(os.path.exists(user_dir), "Temp user data dir should exist while running")

            # Navigate to a blank page to test JS attributes
            driver.get("about:blank")

            # Check navigator.webdriver property
            webdriver_val = driver.execute_script("return navigator.webdriver;")
            # In undetected-chromedriver, navigator.webdriver is undefined or false (not True)
            self.assertIn(webdriver_val, [None, False], "navigator.webdriver should not be True in stealth mode")

        finally:
            browser_mgr.close()

        # Assert temporary profile directory was deleted
        self.assertFalse(os.path.exists(user_dir), f"Profile directory {user_dir} was not cleaned up!")

    # ==================== TEST 6: MULTI-IMAGE UPLOAD & DIALOG SCOPING ====================
    def test_06_multi_image_upload_dialog_scoping(self):
        """
        Tests FacebookActions.upload_images against a mock DOM containing:
        - A single-file comment <input type="file"> outside the dialog (trap!)
        - A post <div role="dialog"> with <input type="file" multiple>
        - A post <div role="dialog"> with <input type="file"> (without multiple)
        Ensures multiple images upload without 'element can not hold multiple files'.
        """
        import tempfile
        from core.fb_actions import FacebookActions

        img1 = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        img2 = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        img1.write(b"fake png 1")
        img2.write(b"fake png 2")
        img1.close()
        img2.close()

        browser_mgr = BrowserManager(headless=True)
        try:
            driver = browser_mgr.start()
            fb = FacebookActions(driver)

            # Case 1: Feed comment single input outside dialog + multiple input inside dialog
            driver.get("about:blank")
            driver.execute_script("""
                document.body.innerHTML = `
                    <div role="main">
                        <input id="comment-trap" type="file" accept="image/*" />
                    </div>
                    <div role="dialog">
                        <input id="post-multi" type="file" accept="image/*" multiple />
                    </div>
                `;
            """)
            ok_multi = fb.upload_images([img1.name, img2.name])
            self.assertTrue(ok_multi)
            files_count = driver.execute_script("return document.getElementById('post-multi').files.length;")
            trap_count = driver.execute_script("return document.getElementById('comment-trap').files.length;")
            self.assertEqual(files_count, 2)
            self.assertEqual(trap_count, 0)

            # Case 2: Dialog input WITHOUT 'multiple' attribute when passing 2 images
            driver.execute_script("""
                document.body.innerHTML = `
                    <div role="dialog">
                        <input id="post-single" type="file" accept="image/*" />
                    </div>
                `;
            """)
            ok_single_fallback = fb.upload_images([img1.name, img2.name])
            self.assertTrue(ok_single_fallback)
            single_files_count = driver.execute_script("return document.getElementById('post-single').files.length;")
            self.assertGreaterEqual(single_files_count, 1)

        finally:
            browser_mgr.close()
            for p in (img1.name, img2.name):
                if os.path.exists(p):
                    os.remove(p)

    # ==================== TEST 7: DUPLICATE POST LIVE FB DOM SCAN ====================
    def test_07_duplicate_post_fb_scan(self):
        """
        Tests FacebookActions.check_already_posted_in_group against mock FB group DOMs:
        1) Pending admin approval banner -> detected as already_posted + requires_approval
        2) Top feed article by matching UID within cooldown -> detected as already_posted
        3) Top feed article by matching UID outside cooldown ('3 ngày') -> NOT blocked
        4) Top feed article by different UID -> NOT blocked
        """
        from core.fb_actions import FacebookActions

        browser_mgr = BrowserManager(headless=True)
        try:
            driver = browser_mgr.start()
            fb = FacebookActions(driver)
            driver.get("about:blank")

            # Case 1: Pending approval banner
            driver.execute_script("""
                document.body.innerHTML = `
                    <div role="main">
                        <div>Bài viết của bạn đang chờ quản trị viên phê duyệt.</div>
                    </div>
                `;
            """)
            res_pending = fb.check_already_posted_in_group(
                "https://www.facebook.com/groups/mock/",
                uid="100087294850584",
                cooldown_hours=24,
                deep_scan=False
            )
            self.assertTrue(res_pending["already_posted"])
            self.assertTrue(res_pending["requires_approval"])

            # Case 2: Recent feed post by matching UID ('2 giờ' <= 24h)
            driver.execute_script("""
                document.body.innerHTML = `
                    <div role="main">
                        <div role="article">
                            <a href="https://www.facebook.com/groups/mock/user/100087294850584/">Lê Đạt</a>
                            <a href="https://www.facebook.com/groups/mock/posts/12345/">2 giờ</a>
                        </div>
                    </div>
                `;
            """)
            res_recent = fb.check_already_posted_in_group(
                "https://www.facebook.com/groups/mock/",
                uid="100087294850584",
                cooldown_hours=24,
                deep_scan=False
            )
            self.assertTrue(res_recent["already_posted"])
            self.assertFalse(res_recent["requires_approval"])

            # Case 3: Old feed post by matching UID ('3 ngày' > 24h) -> allowed
            driver.execute_script("""
                document.body.innerHTML = `
                    <div role="main">
                        <div role="article">
                            <a href="https://www.facebook.com/groups/mock/user/100087294850584/">Lê Đạt</a>
                            <a href="https://www.facebook.com/groups/mock/posts/12345/">3 ngày</a>
                        </div>
                    </div>
                `;
            """)
            res_old = fb.check_already_posted_in_group(
                "https://www.facebook.com/groups/mock/",
                uid="100087294850584",
                cooldown_hours=24,
                deep_scan=False
            )
            self.assertFalse(res_old["already_posted"])

            # Case 4: Recent feed post by a DIFFERENT UID -> allowed
            driver.execute_script("""
                document.body.innerHTML = `
                    <div role="main">
                        <div role="article">
                            <a href="https://www.facebook.com/groups/mock/user/999999999/">Other User</a>
                            <a href="https://www.facebook.com/groups/mock/posts/67890/">Vừa xong</a>
                        </div>
                    </div>
                `;
            """)
            res_other = fb.check_already_posted_in_group(
                "https://www.facebook.com/groups/mock/",
                uid="100087294850584",
                cooldown_hours=24,
                deep_scan=False
            )
            self.assertFalse(res_other["already_posted"])

        finally:
            browser_mgr.close()

if __name__ == "__main__":
    unittest.main(verbosity=2)
