class BladWirtualki(Exception):
    """Anything the user did wrong, or any state we refuse to touch."""


class NotFound(BladWirtualki):
    pass


class AlreadyExists(BladWirtualki):
    pass


class Running(BladWirtualki):
    pass
