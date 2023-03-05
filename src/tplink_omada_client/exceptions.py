""" Exceptions that the library might throw. """


class OmadaClientException(Exception):
    """Base for all exceptions raised by the library."""


class RequestFailed(OmadaClientException):
    """Generic rejection of any command by the controller."""

    def __init__(self, error_code: int, msg: str):
        self._error_code = error_code
        self._msg = msg
        super().__init__(f"Omada controller responded '{msg}' ({error_code})")


class LoginFailed(RequestFailed):
    """Username/Password failure."""


class LoginSessionClosed(OmadaClientException):
    """
    The login token isn't valid any more.

    If this happens immediately after logging on, and you are using IP addresses to contact the controller
    then make sure you supply a ClientSession that has an unsafe CookieJar, or the login session cookies
    won't work.
    """


class UnsupportedControllerVersion(OmadaClientException):
    """
    Indicates the Omada controller has a software version that is not supported.

    Only controller versions 5.0 and later are supported.
    """

    def __init__(self, version):
        super().__init__(f"Unsupported Omada controller version {version} found.")


class SiteNotFound(OmadaClientException):
    """The specified site cannot be found on the Controller."""


class ConnectionFailed(OmadaClientException):
    """Connection to Omada controller failed at the network level."""


class BadControllerUrl(OmadaClientException):
    """URL of controller could not be resolved."""


class InvalidDevice(OmadaClientException):
    """Device type isn't valid for this operation."""
