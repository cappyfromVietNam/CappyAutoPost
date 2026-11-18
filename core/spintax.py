"""
CappyAutoPost - Spintax Engine & Dynamic Variable Substitutions
Supports:
- Nested Spintax: {Xin chào|Hello|{Chào bạn|Hi bạn}}
- Dynamic tokens: {time}, {date}, {datetime}, {rand_id}, {rand_num}
"""
import re
import random
import string
from datetime import datetime

class SpintaxEngine:
    SPINTAX_PATTERN = re.compile(r"\{([^{}]+)\}")

    @classmethod
    def resolve_spintax(cls, text: str) -> str:
        """
        Recursively resolves nested spintax expressions containing '|'.
        Leaves single-term tags like {time} or {date} intact for dynamic substitution.
        """
        if not text:
            return ""

        current = text
        # Match brackets that contain at least one pipe '|'
        pipe_bracket_pattern = re.compile(r"\{([^{}]*\|[^{}]*)\}")
        
        while True:
            match = pipe_bracket_pattern.search(current)
            if not match:
                break
            options = match.group(1).split("|")
            chosen = random.choice(options)
            current = current[:match.start()] + chosen + current[match.end():]

        return current

    @classmethod
    def resolve_dynamic_variables(cls, text: str) -> str:
        """
        Replaces dynamic tags like {time}, {date}, {rand_id}, etc.
        """
        if not text:
            return ""

        now = datetime.now()
        
        def replace_token(match: re.Match) -> str:
            token = match.group(1).lower()
            if token == "time":
                return now.strftime("%H:%M")
            elif token == "time_sec":
                return now.strftime("%H:%M:%S")
            elif token == "date":
                return now.strftime("%d/%m/%Y")
            elif token == "datetime":
                return now.strftime("%H:%M %d/%m/%Y")
            elif token in ("rand_id", "random_id"):
                chars = string.ascii_uppercase + string.digits
                return "#" + "".join(random.choices(chars, k=5))
            elif token in ("rand_num", "random_num"):
                return str(random.randint(1000, 9999))
            # If not a recognized token, leave unchanged
            return match.group(0)

        # Match single word tags: {time}, {date}, {rand_id}
        result = re.sub(r"\{([a-zA-Z0-9_]+)\}", replace_token, text)
        return result

    @classmethod
    def process(cls, template: str) -> str:
        """
        Complete processing: resolves spintax first, then dynamic variables.
        """
        if not template:
            return ""
        resolved = cls.resolve_spintax(template)
        return cls.resolve_dynamic_variables(resolved)
