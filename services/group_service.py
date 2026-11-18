"""
CappyAutoPost - Group Service
Manages group parsing, categorization, and URL extraction with group name support.
"""
import re
from typing import List, Dict, Any, Optional
from database.models import GroupModel

class GroupService:
    @staticmethod
    def extract_group_urls(text: str) -> List[str]:
        """
        Extracts clean Facebook group URLs from arbitrary multi-line text or links.
        Normalizes domains (m., web., mbasic.) to https://www.facebook.com/groups/<gid>/
        """
        urls = set()
        lines = text.strip().splitlines()
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if it's already a full group URL
            match = re.search(r"https?://(?:www\.|m\.|web\.|mbasic\.)?facebook\.com/groups/([a-zA-Z0-9._\-]+)", line)
            if match:
                gid = match.group(1).rstrip("/")
                urls.add(f"https://www.facebook.com/groups/{gid}/")
                continue

            # Check if line is just a group path 'groups/123'
            match_path = re.search(r"groups/([a-zA-Z0-9._\-]+)", line)
            if match_path:
                gid = match_path.group(1)
                urls.add(f"https://www.facebook.com/groups/{gid}/")
                continue

            # Check if numeric group ID
            if line.isdigit() and len(line) >= 6:
                urls.add(f"https://www.facebook.com/groups/{line}/")

        return sorted(list(urls))

    @classmethod
    def parse_group_lines(cls, text: str, default_name: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Parses multi-line text into a list of dicts: {'url': str, 'name': str}.
        Supports:
        - Tên nhóm | https://facebook.com/groups/12345/
        - https://facebook.com/groups/12345/ | Tên nhóm
        - https://facebook.com/groups/12345/
        """
        results = []
        seen_urls = set()
        lines = text.strip().splitlines()

        for line in lines:
            line = line.strip()
            if not line:
                continue

            extracted_name = None
            raw_url_part = line

            if "|" in line:
                parts = [p.strip() for p in line.split("|") if p.strip()]
                if len(parts) >= 2:
                    p0_has_url = "facebook.com" in parts[0] or "groups/" in parts[0] or (parts[0].isdigit() and len(parts[0]) >= 6)
                    p1_has_url = "facebook.com" in parts[1] or "groups/" in parts[1] or (parts[1].isdigit() and len(parts[1]) >= 6)

                    if p0_has_url and not p1_has_url:
                        raw_url_part = parts[0]
                        extracted_name = parts[1]
                    elif p1_has_url and not p0_has_url:
                        raw_url_part = parts[1]
                        extracted_name = parts[0]
                    else:
                        extracted_name = parts[0]
                        raw_url_part = parts[1]

            extracted_urls = cls.extract_group_urls(raw_url_part)
            if not extracted_urls:
                continue

            clean_url = extracted_urls[0]
            if clean_url in seen_urls:
                continue
            seen_urls.add(clean_url)

            final_name = extracted_name or default_name
            if not final_name:
                match = re.search(r"/groups/([a-zA-Z0-9._\-]+)", clean_url)
                final_name = f"Nhóm {match.group(1)}" if match else clean_url

            results.append({
                "url": clean_url,
                "name": final_name
            })

        return results

    @classmethod
    def import_groups(cls, raw_text: str, category: str = "Chung", default_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Bulk imports group URLs and names into the database.
        """
        parsed_groups = cls.parse_group_lines(raw_text, default_name)
        added_count = 0
        for item in parsed_groups:
            try:
                GroupModel.add(url=item["url"], name=item["name"], category=category)
                added_count += 1
            except Exception:
                pass

        return {
            "total_found": len(parsed_groups),
            "added_count": added_count,
            "category": category
        }
