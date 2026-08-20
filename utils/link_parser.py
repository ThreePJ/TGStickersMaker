import re
from typing import List


def parse_single_link(raw_link: str) -> str:
    """
    Extract sticker set short_name from a link or string.
    Examples:
        https://t.me/addstickers/pepe_pack -> pepe_pack
        t.me/addstickers/pepe_pack -> pepe_pack
        tg://addstickers?set=pepe_pack -> pepe_pack
        telegram.me/addstickers/pepe_pack -> pepe_pack
        pepe_pack -> pepe_pack
    """
    text = raw_link.strip()
    if not text:
        return ""

    # Match tg://addstickers?set=<name>
    tg_match = re.search(r"tg://addstickers\?set=([a-zA-Z0-9_]+)", text, re.IGNORECASE)
    if tg_match:
        return tg_match.group(1)

    # Match t.me/addstickers/<name> or telegram.me/addstickers/<name>
    http_match = re.search(r"(?:t(?:elegram)?\.me)/addstickers/([a-zA-Z0-9_]+)", text, re.IGNORECASE)
    if http_match:
        return http_match.group(1)

    # If it's already a clean short_name (alphanumeric and underscores)
    clean_match = re.match(r"^([a-zA-Z0-9_]+)$", text)
    if clean_match:
        return clean_match.group(1)

    return ""


def parse_sticker_links(raw_text: str) -> List[str]:
    """
    Extract unique short_names from a multi-line or delimited text.
    Preserves order of first appearance.
    """
    if not raw_text:
        return []

    # Split by newlines, commas, semicolons, or whitespace
    tokens = re.split(r"[\r\n,;\s]+", raw_text)
    results: List[str] = []
    seen = set()

    for token in tokens:
        short_name = parse_single_link(token)
        if short_name and short_name.lower() not in seen:
            seen.add(short_name.lower())
            results.append(short_name)

    return results


# Alias for backward/convenience compatibility
extract_pack_names = parse_sticker_links

