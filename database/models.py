"""
CappyAutoPost - Database Models & CRUD Data Access
"""
import json
import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime
from .connection import get_db

class AccountModel:
    @staticmethod
    def get_all() -> List[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM accounts ORDER BY id DESC")
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_by_id(account_id: int) -> Optional[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM accounts WHERE id = ?", (account_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def get_by_uid(uid: str) -> Optional[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM accounts WHERE uid = ?", (uid,))
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def create_or_update(name: str, uid: str, cookie_raw: str, proxy: str = None, notes: str = None) -> int:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO accounts (name, uid, cookie_raw, proxy, notes, status, last_checked)
                VALUES (?, ?, ?, ?, ?, 'Unknown', NULL)
                ON CONFLICT(uid) DO UPDATE SET
                    name = excluded.name,
                    cookie_raw = excluded.cookie_raw,
                    proxy = excluded.proxy,
                    notes = excluded.notes;
            """, (name, uid, cookie_raw, proxy, notes))
            return cursor.lastrowid

    @staticmethod
    def update_status(account_id: int, status: str, last_checked: datetime = None) -> None:
        last_checked = last_checked or datetime.now()
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE accounts
                SET status = ?, last_checked = ?
                WHERE id = ?
            """, (status, last_checked.strftime("%Y-%m-%d %H:%M:%S"), account_id))

    @staticmethod
    def increment_post_count(account_id: int) -> None:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE accounts
                SET posts_count_today = posts_count_today + 1
                WHERE id = ?
            """, (account_id,))

    @staticmethod
    def reset_daily_post_counts() -> None:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE accounts SET posts_count_today = 0")

    @staticmethod
    def delete(account_id: int) -> bool:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
            return cursor.rowcount > 0


class GroupModel:
    @staticmethod
    def get_all(category: str = None) -> List[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            if category:
                cursor.execute("SELECT * FROM groups WHERE category = ? ORDER BY id DESC", (category,))
            else:
                cursor.execute("SELECT * FROM groups ORDER BY id DESC")
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_categories() -> List[str]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT category FROM groups WHERE category IS NOT NULL AND category != ''")
            return [row["category"] for row in cursor.fetchall()]

    @staticmethod
    def add(url: str, name: str = None, category: str = "Chung", requires_approval: bool = False, allow_anonymous: bool = False) -> int:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO groups (url, name, category, requires_approval, allow_anonymous)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(url) DO UPDATE SET
                    name = COALESCE(excluded.name, groups.name),
                    category = excluded.category;
            """, (url, name or url, category, 1 if requires_approval else 0, 1 if allow_anonymous else 0))
            return cursor.lastrowid

    @staticmethod
    def update_attributes(group_id: int, requires_approval: Optional[bool] = None, allow_anonymous: Optional[bool] = None) -> None:
        updates = []
        params = []
        if requires_approval is not None:
            updates.append("requires_approval = ?")
            params.append(1 if requires_approval else 0)
        if allow_anonymous is not None:
            updates.append("allow_anonymous = ?")
            params.append(1 if allow_anonymous else 0)
        if not updates:
            return
        params.append(group_id)
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE groups SET {', '.join(updates)} WHERE id = ?", params)

    @staticmethod
    def delete(group_id: int) -> bool:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM groups WHERE id = ?", (group_id,))
            return cursor.rowcount > 0


class PostModel:
    @staticmethod
    def get_all() -> List[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM posts ORDER BY id DESC")
            rows = cursor.fetchall()
            posts = []
            for row in rows:
                p = dict(row)
                try:
                    p["image_paths"] = json.loads(p.get("image_paths_json") or "[]")
                except Exception:
                    p["image_paths"] = []
                posts.append(p)
            return posts

    @staticmethod
    def get_by_id(post_id: int) -> Optional[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM posts WHERE id = ?", (post_id,))
            row = cursor.fetchone()
            if not row:
                return None
            p = dict(row)
            try:
                p["image_paths"] = json.loads(p.get("image_paths_json") or "[]")
            except Exception:
                p["image_paths"] = []
            return p

    @staticmethod
    def save(title: str, content_spintax: str, image_paths: List[str] = None, use_anonymous: bool = False, category: str = "Chung", post_id: int = None) -> int:
        images_json = json.dumps(image_paths or [])
        with get_db() as conn:
            cursor = conn.cursor()
            if post_id:
                cursor.execute("""
                    UPDATE posts
                    SET title = ?, content_spintax = ?, image_paths_json = ?, use_anonymous = ?, category = ?
                    WHERE id = ?
                """, (title, content_spintax, images_json, 1 if use_anonymous else 0, category, post_id))
                return post_id
            else:
                cursor.execute("""
                    INSERT INTO posts (title, content_spintax, image_paths_json, use_anonymous, category)
                    VALUES (?, ?, ?, ?, ?)
                """, (title, content_spintax, images_json, 1 if use_anonymous else 0, category))
                return cursor.lastrowid

    @staticmethod
    def delete(post_id: int) -> bool:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM posts WHERE id = ?", (post_id,))
            return cursor.rowcount > 0


class HistoryModel:
    @staticmethod
    def add(account_id: Optional[int], group_id: Optional[int], post_id: Optional[int], status: str, error_message: str = None, post_url: str = None) -> int:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO posting_history (account_id, group_id, post_id, status, error_message, post_url)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (account_id, group_id, post_id, status, error_message, post_url))
            return cursor.lastrowid

    @staticmethod
    def get_recent(limit: int = 100) -> List[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT h.*, 
                       COALESCE(a.name, a.uid, 'N/A') as account_name,
                       COALESCE(g.name, g.url, 'N/A') as group_name,
                       g.url as group_url,
                       COALESCE(p.title, 'N/A') as post_title
                FROM posting_history h
                LEFT JOIN accounts a ON h.account_id = a.id
                LEFT JOIN groups g ON h.group_id = g.id
                LEFT JOIN posts p ON h.post_id = p.id
                ORDER BY h.posted_at DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def has_recent_post_in_group(group_id: int, hours: int = 24) -> Optional[Dict[str, Any]]:
        """Checks if any account successfully posted or has a pending post in this group within `hours`."""
        if not group_id or int(hours) <= 0:
            return None
        modifier = f"-{int(hours)} hours"
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT h.id, h.account_id, h.group_id, h.status, h.posted_at,
                       COALESCE(a.name, a.uid, 'N/A') as account_name
                FROM posting_history h
                LEFT JOIN accounts a ON h.account_id = a.id
                WHERE h.group_id = ?
                  AND h.status IN ('Success', 'Pending_Approval')
                  AND h.posted_at >= datetime('now', ?)
                ORDER BY h.posted_at DESC
                LIMIT 1
            """, (group_id, modifier))
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def get_statistics() -> Dict[str, Any]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as total_accounts, SUM(CASE WHEN status = 'Live' THEN 1 ELSE 0 END) as live_accounts FROM accounts")
            acc_stats = cursor.fetchone()
            
            cursor.execute("SELECT COUNT(*) as total_groups FROM groups")
            grp_stats = cursor.fetchone()

            cursor.execute("SELECT COUNT(*) as total_posts FROM posts")
            post_stats = cursor.fetchone()

            cursor.execute("""
                SELECT 
                    COUNT(*) as total_history,
                    SUM(CASE WHEN status = 'Success' THEN 1 ELSE 0 END) as total_success,
                    SUM(CASE WHEN status = 'Pending_Approval' THEN 1 ELSE 0 END) as total_pending,
                    SUM(CASE WHEN status = 'Failed' THEN 1 ELSE 0 END) as total_failed
                FROM posting_history
            """)
            hist_stats = cursor.fetchone()

            return {
                "total_accounts": acc_stats["total_accounts"] or 0,
                "live_accounts": acc_stats["live_accounts"] or 0,
                "total_groups": grp_stats["total_groups"] or 0,
                "total_posts": post_stats["total_posts"] or 0,
                "history_total": hist_stats["total_history"] or 0,
                "history_success": hist_stats["total_success"] or 0,
                "history_pending": hist_stats["total_pending"] or 0,
                "history_failed": hist_stats["total_failed"] or 0,
            }


class SettingsModel:
    @staticmethod
    def get(key: str, default: Any = None) -> Any:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                try:
                    return json.loads(row["value"])
                except Exception:
                    return row["value"]
            return default

    @staticmethod
    def set(key: str, value: Any) -> None:
        val_str = json.dumps(value) if not isinstance(value, str) else value
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO app_settings (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = CURRENT_TIMESTAMP;
            """, (key, val_str))
