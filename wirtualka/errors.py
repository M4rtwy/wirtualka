# Anything the user got wrong, or any state we refuse to touch.
class BladWirtualki(Exception):
    pass


class NotFound(BladWirtualki):
    pass


class AlreadyExists(BladWirtualki):
    pass


class Running(BladWirtualki):
    pass
