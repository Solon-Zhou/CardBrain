# routes/__init__.py — 共用 helper
"""CardBrain route helpers."""


def parse_ids(s: str) -> list[int]:
    """將逗號分隔的 ID 字串轉為 int list。"""
    if not s.strip():
        return []
    return [int(x) for x in s.split(",") if x.strip().isdigit()]
