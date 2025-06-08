import secrets
import string

RANDOM_STRING_CHARS = string.ascii_letters + string.digits


def get_random_string(length, allowed_chars=RANDOM_STRING_CHARS):
    """
    Return a securely generated random string.

    The bit length of the returned value can be calculated with the formula:
        log_2(len(allowed_chars)^length)

    For example, with default `allowed_chars` (26+26+10), this gives:
      * length: 12, bit length =~ 71 bits
      * length: 22, bit length =~ 131 bits
    """
    return "".join(secrets.choice(allowed_chars) for _ in range(length))


def get_random_secret_key():
    """
    Return a random string usable as for Django's SECRET_KEY setting.

    This function is a modification of Django's get_random_secret_key function that doesn't use characters that can be
    problematic in `.env` files. This function doesn't use +, (, ), #, or $, or &.
    """
    chars = "abcdefghijklmnopqrstuvwxyz0123456789!@%^*-_="
    return get_random_string(50, chars)
