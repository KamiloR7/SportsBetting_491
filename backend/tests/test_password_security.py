import bcrypt

from app.services.password_security import verify_password


def test_valid_password():
    password = "TestPassword123"

    stored_hash = bcrypt.hashpw(
        password.encode(),
        bcrypt.gensalt(),
    ).decode()

    assert verify_password(password, stored_hash)


def test_invalid_password():
    stored_hash = bcrypt.hashpw(
        b"TestPassword123",
        bcrypt.gensalt(),
    ).decode()

    assert not verify_password(
        "WrongPassword123",
        stored_hash,
    )


def test_corrupted_password_hash():
    assert not verify_password(
        "TestPassword123",
        "invalid-bcrypt-hash",
    )