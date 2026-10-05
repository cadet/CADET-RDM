from urllib.parse import urlparse
from pathlib import Path


def ssh_url_to_http_url(url: str | Path) -> str:
    """
    Convert an SSH git URL to an HTTPS URL.

    HTTPS URLs and existing local paths are returned unchanged.

    Parameters
    ----------
    url : str | Path
        SSH URL, HTTPS URL or local path of a repository.

    Returns
    -------
    str
        HTTPS URL of the repository, or the unchanged input.
    """
    url = str(url)
    if "https" in url:
        return url
    if Path(url).exists():
        return url

    url = url.replace(":", "/").replace("git@", "https://").replace(".git", "")
    return url


def is_valid_url(string: str) -> bool:
    """
    Check whether a string is a URL with a scheme and a network location.

    Parameters
    ----------
    string : str
        String to check.

    Returns
    -------
    bool
        True if the string is a valid URL.
    """
    try:
        result = urlparse(string)
        return all([result.scheme, result.netloc])
    except Exception:
        return False
