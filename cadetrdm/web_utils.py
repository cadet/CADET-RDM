from urllib.parse import urlparse


def ssh_url_to_http_url(url):
    if "https" in url:
        return url

    url = url.replace(":", "/").replace("git@", "https://").replace(".git", "")
    return url


def is_valid_url(string):
    try:
        result = urlparse(string)
        return all([result.scheme, result.netloc])
    except:
        return False
