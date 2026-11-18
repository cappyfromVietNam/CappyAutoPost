"""
CappyAutoPost - Comprehensive Unit Test Suite
"""
import sys
import unittest
from pathlib import Path

# Add project root to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from database import init_db, get_db, AccountModel, GroupModel, PostModel, HistoryModel
from core.cookie_helper import parse_cookie_input, extract_c_user_and_xs, format_proxy
from core.spintax import SpintaxEngine
from core.human_behavior import HumanSimulator
from services.group_service import GroupService
from ui.api import WebviewAPI

class TestCappyAutoPost(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def test_spintax_engine(self):
        template = "{A|B|C}"
        results = {SpintaxEngine.resolve_spintax(template) for _ in range(20)}
        self.assertTrue(results.issubset({"A", "B", "C"}))
        self.assertGreater(len(results), 1)

        # Test nested
        nested_template = "{Xin chào|{Hello|Hi}}"
        nested_results = {SpintaxEngine.resolve_spintax(nested_template) for _ in range(30)}
        self.assertTrue(nested_results.issubset({"Xin chào", "Hello", "Hi"}))

        # Test dynamic tags
        dynamic_template = "Test {time} {date} {rand_id}"
        processed = SpintaxEngine.process(dynamic_template)
        self.assertNotIn("{time}", processed)
        self.assertNotIn("{date}", processed)
        self.assertNotIn("{rand_id}", processed)
        self.assertIn("#", processed)

    def test_cookie_helper(self):
        cookie_str = "c_user=1000888999; xs=38%3Aabc123xyz; fr=0abc; datr=foo;"
        parsed = parse_cookie_input(cookie_str)
        self.assertEqual(parsed.get("c_user"), "1000888999")
        self.assertEqual(parsed.get("xs"), "38%3Aabc123xyz")

        c_user, xs = extract_c_user_and_xs(parsed)
        self.assertEqual(c_user, "1000888999")
        self.assertEqual(xs, "38%3Aabc123xyz")

        # Test JSON format
        json_str = '[{"name": "c_user", "value": "1000777888"}, {"name": "xs", "value": "secret_token"}]'
        parsed_json = parse_cookie_input(json_str)
        self.assertEqual(parsed_json.get("c_user"), "1000777888")
        self.assertEqual(parsed_json.get("xs"), "secret_token")

    def test_proxy_formatter(self):
        p1 = format_proxy("192.168.1.100:8080")
        self.assertEqual(p1["http"], "http://192.168.1.100:8080")

        p2 = format_proxy("192.168.1.100:8080:myuser:mypassword")
        self.assertEqual(p2["http"], "http://myuser:mypassword@192.168.1.100:8080")

    def test_group_service_extraction(self):
        raw_text = """
        https://www.facebook.com/groups/1234567890/
        https://m.facebook.com/groups/congdongmarketing?ref=share
        998877665544
        groups/nhadathanoi
        """
        urls = GroupService.extract_group_urls(raw_text)
        self.assertIn("https://www.facebook.com/groups/1234567890/", urls)
        self.assertIn("https://www.facebook.com/groups/congdongmarketing/", urls)
        self.assertIn("https://www.facebook.com/groups/998877665544/", urls)
        self.assertIn("https://www.facebook.com/groups/nhadathanoi/", urls)

        # Test line parsing with names
        mixed_text = """
        Bất Động Sản Hà Nội | https://www.facebook.com/groups/111222333/
        https://www.facebook.com/groups/444555666/ | Hội Việc Làm
        https://www.facebook.com/groups/777888999/
        """
        parsed = GroupService.parse_group_lines(mixed_text, default_name="Nhóm Bất Động Sản")
        self.assertEqual(len(parsed), 3)
        self.assertEqual(parsed[0]["name"], "Bất Động Sản Hà Nội")
        self.assertEqual(parsed[1]["name"], "Hội Việc Làm")
        self.assertEqual(parsed[2]["name"], "Nhóm Bất Động Sản")

    def test_database_crud(self):
        # Account
        acc_id = AccountModel.create_or_update(
            name="Test User",
            uid="1000999000",
            cookie_raw="c_user=1000999000; xs=token123;"
        )
        self.assertIsInstance(acc_id, int)
        acc = AccountModel.get_by_id(acc_id)
        self.assertEqual(acc["name"], "Test User")

        # Group
        grp_id = GroupModel.add(url="https://www.facebook.com/groups/test_group/", name="Test Group")
        self.assertIsInstance(grp_id, int)

        # Post
        post_id = PostModel.save(
            title="Post Mau",
            content_spintax="{A|B} test spintax",
            image_paths=["test.png"],
            use_anonymous=True
        )
        self.assertIsInstance(post_id, int)
        p = PostModel.get_by_id(post_id)
        self.assertEqual(p["title"], "Post Mau")
        self.assertEqual(p["image_paths"], ["test.png"])
        self.assertTrue(p["use_anonymous"])

        # History
        hist_id = HistoryModel.add(acc_id, grp_id, post_id, "Success", "Posted successfully")
        self.assertIsInstance(hist_id, int)

        # Stats
        stats = HistoryModel.get_statistics()
        self.assertGreaterEqual(stats["total_accounts"], 1)
        self.assertGreaterEqual(stats["total_groups"], 1)
        self.assertGreaterEqual(stats["total_posts"], 1)
        self.assertGreaterEqual(stats["history_success"], 1)

        # Cleanup
        AccountModel.delete(acc_id)
        GroupModel.delete(grp_id)
        PostModel.delete(post_id)

    def test_api_layer(self):
        api = WebviewAPI()
        stats = api.get_dashboard_stats()
        self.assertIn("total_accounts", stats)
        preview = api.preview_spintax("{Hello|Hi} world")
        self.assertIn(preview, ["Hello world", "Hi world"])

    def test_safe_wait_and_delay_bounds(self):
        # 1. Verify compute_gaussian_delay strictly respects [min, max] including 0
        for _ in range(50):
            d = HumanSimulator.compute_gaussian_delay(0, 1)
            self.assertGreaterEqual(d, 0.0)
            self.assertLessEqual(d, 1.0)
        self.assertEqual(HumanSimulator.compute_gaussian_delay(0, 0), 0.0)

        # 2. Verify CampaignWorker stores safe_wait_seconds and min_delay=0
        from services.campaign_worker import CampaignWorker
        w = CampaignWorker(account_ids=[], group_ids=[], post_id=1, min_delay=0, max_delay=1, safe_wait_seconds=15)
        self.assertEqual(w.min_delay, 0)
        self.assertEqual(w.max_delay, 1)
        self.assertEqual(w.safe_wait_seconds, 15)

        # 3. Verify API config persistence preserves 0 values
        api = WebviewAPI()
        prev_cfg = api.get_campaign_config()
        try:
            api.save_campaign_config({
                "max_posts_per_account": 10,
                "min_delay": 0,
                "max_delay": 1,
                "safe_wait_seconds": 5
            })
            loaded = api.get_campaign_config()
            self.assertEqual(loaded["min_delay"], 0)
            self.assertEqual(loaded["max_delay"], 1)
            self.assertEqual(loaded["safe_wait_seconds"], 5)
            self.assertEqual(loaded["max_posts_per_account"], 10)
        finally:
            api.save_campaign_config(prev_cfg)

    def test_duplicate_post_cooldown_and_config(self):
        from core.fb_actions import FacebookActions
        from services.campaign_worker import CampaignWorker

        # 1. Timestamp parser checks
        self.assertTrue(FacebookActions.is_relative_time_within_hours("Vừa xong", 24))
        self.assertTrue(FacebookActions.is_relative_time_within_hours("Just now", 24))
        self.assertTrue(FacebookActions.is_relative_time_within_hours("15 phút", 24))
        self.assertTrue(FacebookActions.is_relative_time_within_hours("15m", 24))
        self.assertTrue(FacebookActions.is_relative_time_within_hours("2 giờ", 24))
        self.assertTrue(FacebookActions.is_relative_time_within_hours("3 hrs", 24))
        self.assertTrue(FacebookActions.is_relative_time_within_hours("Hôm qua", 24))
        self.assertFalse(FacebookActions.is_relative_time_within_hours("Hôm qua", 12))
        self.assertFalse(FacebookActions.is_relative_time_within_hours("2 ngày", 24))
        self.assertFalse(FacebookActions.is_relative_time_within_hours("3 days", 24))
        self.assertFalse(FacebookActions.is_relative_time_within_hours("25 giờ", 24))
        self.assertFalse(FacebookActions.is_relative_time_within_hours("12 tháng 5", 24))

        # 2. DB cooldown & CampaignWorker instant skip checks
        acc_id = AccountModel.create_or_update(name="DupTestAcc", uid="999888777", cookie_raw="c_user=999888777; xs=abc")
        grp_id = GroupModel.add(url="https://www.facebook.com/groups/duptest999/", name="Dup Test Group")
        post_id = PostModel.save(title="DupTestPost", content_spintax="Hello test")
        hist_ids = []
        try:
            self.assertIsNone(HistoryModel.has_recent_post_in_group(grp_id, hours=24))

            # Failed attempts must NOT block future posts
            h_fail = HistoryModel.add(acc_id, grp_id, post_id, "Failed", "Network hiccup")
            hist_ids.append(h_fail)
            self.assertIsNone(HistoryModel.has_recent_post_in_group(grp_id, hours=24))

            # Success within window MUST block
            h_ok = HistoryModel.add(acc_id, grp_id, post_id, "Success", "OK")
            hist_ids.append(h_ok)
            recent = HistoryModel.has_recent_post_in_group(grp_id, hours=24)
            self.assertIsNotNone(recent)
            self.assertEqual(recent["status"], "Success")

            # Push Success back 30h -> outside 24h cooldown, inside 48h cooldown
            with get_db() as conn:
                conn.execute("UPDATE posting_history SET posted_at = datetime('now', '-30 hours') WHERE id = ?", (h_ok,))
            self.assertIsNone(HistoryModel.has_recent_post_in_group(grp_id, hours=24))
            self.assertIsNotNone(HistoryModel.has_recent_post_in_group(grp_id, hours=48))

            # Pending_Approval within window MUST block
            h_pend = HistoryModel.add(acc_id, grp_id, post_id, "Pending_Approval", "Waiting admin")
            hist_ids.append(h_pend)
            recent_pend = HistoryModel.has_recent_post_in_group(grp_id, hours=24)
            self.assertIsNotNone(recent_pend)
            self.assertEqual(recent_pend["status"], "Pending_Approval")

            # CampaignWorker skips cleanly without starting browser when DB cooldown triggers
            events = []
            worker = CampaignWorker(
                account_ids=[acc_id],
                group_ids=[grp_id],
                post_id=post_id,
                min_delay=0,
                max_delay=0,
                safe_wait_seconds=0,
                skip_already_posted=True,
                cooldown_hours=24,
                check_fb_live=False,
                on_event=lambda ev, data: events.append((ev, data))
            )
            worker._run_campaign()
            log_msgs = [d["message"] for ev, d in events if ev == "log"]
            self.assertTrue(any("Bỏ qua nhóm Dup Test Group" in m for m in log_msgs))
            progress_events = [d for ev, d in events if ev == "progress"]
            self.assertTrue(any(p["current"] == 1 and p["total"] == 1 for p in progress_events))

            # API config persistence for duplicate-check keys
            api = WebviewAPI()
            prev_cfg = api.get_campaign_config()
            try:
                api.save_campaign_config({
                    "max_posts_per_account": 3,
                    "min_delay": 10,
                    "max_delay": 20,
                    "safe_wait_seconds": 0,
                    "skip_already_posted": False,
                    "cooldown_hours": 48,
                    "check_fb_live": False,
                })
                loaded = api.get_campaign_config()
                self.assertFalse(loaded["skip_already_posted"])
                self.assertEqual(loaded["cooldown_hours"], 48)
                self.assertFalse(loaded["check_fb_live"])
            finally:
                api.save_campaign_config(prev_cfg)
        finally:
            with get_db() as conn:
                for hid in hist_ids:
                    conn.execute("DELETE FROM posting_history WHERE id = ?", (hid,))
            AccountModel.delete(acc_id)
            GroupModel.delete(grp_id)
            PostModel.delete(post_id)

    def test_campaign_worker_live_duplicate_skip_updates_approval(self):
        from unittest.mock import MagicMock, patch
        from services.campaign_worker import CampaignWorker

        acc_id = AccountModel.create_or_update(name="LiveDupAcc", uid="888777666", cookie_raw="c_user=888777666; xs=xyz")
        grp_id = GroupModel.add(url="https://www.facebook.com/groups/livedup999/", name="Live Dup Group", requires_approval=False)
        post_id = PostModel.save(title="LiveDupPost", content_spintax="Hello test")
        events = []

        try:
            mock_browser = MagicMock()
            mock_browser.start.return_value = MagicMock()

            mock_fb = MagicMock()
            mock_fb.inject_cookies_and_login.return_value = True
            mock_fb.open_group.return_value = True
            mock_fb.check_already_posted_in_group.return_value = {
                "already_posted": True,
                "reason": "Phát hiện bài viết đang chờ duyệt trên trang nhóm.",
                "requires_approval": True,
            }

            with patch("services.campaign_worker.BrowserManager", return_value=mock_browser), \
                 patch("services.campaign_worker.FacebookActions", return_value=mock_fb):
                worker = CampaignWorker(
                    account_ids=[acc_id],
                    group_ids=[grp_id],
                    post_id=post_id,
                    min_delay=0,
                    max_delay=0,
                    safe_wait_seconds=0,
                    skip_already_posted=True,
                    cooldown_hours=24,
                    check_fb_live=True,
                    on_event=lambda ev, data: events.append((ev, data)),
                )
                worker._run_campaign()

            log_msgs = [d["message"] for ev, d in events if ev == "log"]
            self.assertFalse(any("Lỗi nghiêm trọng" in m for m in log_msgs))
            self.assertTrue(any("Bỏ qua nhóm Live Dup Group" in m for m in log_msgs))

            updated_grp = next((g for g in GroupModel.get_all() if g["id"] == grp_id), None)
            self.assertIsNotNone(updated_grp)
            self.assertEqual(updated_grp["requires_approval"], 1)
        finally:
            AccountModel.delete(acc_id)
            GroupModel.delete(grp_id)
            PostModel.delete(post_id)

if __name__ == "__main__":
    unittest.main()
