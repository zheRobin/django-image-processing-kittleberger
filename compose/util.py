def validate_name(name):
    if len(name) > 256:
        name = name[:256]
    return name