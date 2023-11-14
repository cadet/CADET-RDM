def ssh_url_to_http_url(url):
    url = url.replace(":", "/").replace("git@", "https://").replace(".git", "")
    return url
