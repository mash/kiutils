"""Functions for string manipulation

Author:
    (C) Marvin Mager - @mvnmgrx - 2022

License identifier:
    GPL-3.0

Major changes:
    28.02.2022 - created
"""

def dequote(input: str) -> str:
    """Escapes double-quotes in a string using a backslash

    Args:
        - input (str): String to replace double-quotes

    Returns:
        - str: String with replaced double-quotes
    """
    return str(input).replace("\"", "\\\"")


def remove_prefix(input: str, prefix: str) -> str:
    """Removes the given prefix from a string (to remove incompatibility of ``str.removeprefix()``
    for Python versions < 3.9)

    Args:
        - input (str): String to remove the prefix from
        - prefix (str): The prefix

    Returns:
        - str: String with removed prefix, or the ``input`` string as is, if the prefix was not found
    """
    return input[len(prefix):] if input.startswith(prefix) else input


def _fmt(v) -> str:
    """Format a numeric value for KiCad S-expression output.

    Rounds to 6 decimal places and strips trailing zeros so that
    integer-valued floats are rendered without a decimal point (e.g. ``10``
    instead of ``10.0``) and fractional values never carry unnecessary
    trailing zeros.

    Args:
        - v: Numeric value (int, float, or None)

    Returns:
        - str: Formatted number string suitable for S-expression output
    """
    if v is None:
        return "0"
    try:
        r = round(float(v), 6)
    except (ValueError, TypeError):
        return str(v)
    if r == int(r):
        return str(int(r))
    return f"{r:.6f}".rstrip('0').rstrip('.')