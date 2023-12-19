def validate_name(name):
    if len(name) > 255:
        name = name[:255]
    return name