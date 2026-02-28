def parse_size_to_bytes(size_str: str) -> int:
    if not size_str or size_str.lower() == 'unlimited':
        return 0
    size_str = size_str.upper()
    try:
        if size_str.endswith('K'):
            return int(float(size_str[:-1]) * 1024)
        elif size_str.endswith('M'):
            return int(float(size_str[:-1]) * 1024 * 1024)
        elif size_str.endswith('G'):
            return int(float(size_str[:-1]) * 1024 * 1024 * 1024)
        elif size_str.endswith('T'):
            return int(float(size_str[:-1]) * 1024 * 1024 * 1024 * 1024)
        return int(float(size_str))
    except ValueError:
        return 0
