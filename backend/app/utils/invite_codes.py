import secrets

# Alphanumeric charset excluding ambiguous characters (O/0, I/1, L)
CHARSET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 8


def generate_invite_code() -> str:
    return "".join(secrets.choice(CHARSET) for _ in range(CODE_LENGTH))
