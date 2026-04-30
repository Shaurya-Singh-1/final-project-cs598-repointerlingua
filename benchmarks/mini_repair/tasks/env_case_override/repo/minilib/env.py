def merge_env(defaults, overrides):
    merged = dict(defaults)
    for key, value in overrides.items():
        if key in merged:
            merged[key] = value
    return merged
