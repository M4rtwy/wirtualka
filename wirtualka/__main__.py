import sys

from .cli import main
from .errors import BladWirtualki

try:
    sys.exit(main())
except BladWirtualki as error:
    print(f"blad: {error}", file=sys.stderr)
    sys.exit(1)
except KeyboardInterrupt:
    sys.exit(130)
