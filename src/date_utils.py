from datetime import datetime


UNKNOWN_DATE = "未知日期"


def parse_published_at(date_str: str):
    if not date_str:
        return None

    date_text = date_str.strip()
    if date_text in (UNKNOWN_DATE, ""):
        return None

    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(date_text, fmt).isoformat()
        except ValueError:
            continue
    return datetime.utcnow().isoformat() + "Z"
