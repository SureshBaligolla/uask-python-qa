import re

def sanitize_text(s: str) -> str:
    if not s:
        return ""
    # remove non-printable chars
    s = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', s)
    # remove surrogate/emoji range heuristically
    s = re.sub(r'[\U00010000-\U0010ffff]', '', s)
    # collapse multiple spaces/newlines
    s = re.sub(r'\s{2,}', ' ', s).strip()
    return s
