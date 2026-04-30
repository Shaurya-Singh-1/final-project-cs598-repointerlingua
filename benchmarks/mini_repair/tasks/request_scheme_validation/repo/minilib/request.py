def validate_url(url):
    if ":" not in url:
        raise ValueError(f"Missing scheme in request url: {url}")
    return url
