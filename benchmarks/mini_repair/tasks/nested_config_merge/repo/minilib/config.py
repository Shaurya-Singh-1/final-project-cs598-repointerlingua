def merge_configs(default, overwrite):
    new_config = default.copy()
    for k, v in overwrite.items():
        if isinstance(v, dict):
            new_config[k] = merge_configs(default[k], v)
        else:
            new_config[k] = v
    return new_config
