import os
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import bcrypt
from fastapi import HTTPException
from pydantic import ValidationError

# Provide test database settings so backend modules can be imported
# without requiring local PostgreSQL credentials.
os.environ.setdefault("DATABASE_HOST", "localhost")
os.environ.setdefault("DATABASE_PORT", "5432")
os.environ.setdefault("DATABASE_NAME", "test_db")
os.environ.setdefault("DATABASE_USER", "test_user")
os.environ.setdefault("DATABASE_PASSWORD", "test_password")

from app.routes.auth import register_user
from app.schemas.auth import UserRegister


class TestAuthValidation(unittest.TestCase):

    def test_valid_registration_input(self):
        user = UserRegister(
            email="test@example.com",
            username="testuser",
            password="TestPassword123",
        )

        self.assertEqual(
            str(user.email),
            "test@example.com",
        )
        self.assertEqual(
            user.username,
            "testuser",
        )

    def test_invalid_email_rejected(self):
        with self.assertRaises(ValidationError):
            UserRegister(
                email="bad-email",
                username="testuser",
                password="TestPassword123",
            )

    def test_short_password_rejected(self):
        with self.assertRaises(ValidationError):
            UserRegister(
                email="test@example.com",
                username="testuser",
                password="123",
            )

    def test_short_username_rejected(self):
        with self.assertRaises(ValidationError):
            UserRegister(
                email="test@example.com",
                username="ab",
                password="TestPassword123",
            )

    def test_password_hashing(self):
        password = b"TestPassword123"

        password_hash = bcrypt.hashpw(
            password,
            bcrypt.gensalt(),
        )

        self.assertTrue(
            bcrypt.checkpw(
                password,
                password_hash,
            )
        )

        self.assertNotEqual(
            password,
            password_hash,
        )


class TestRegistrationEndpoint(unittest.TestCase):

    def test_duplicate_email_rejected(self):
        db = MagicMock()

        existing_result = MagicMock()
        existing_result.first.return_value = SimpleNamespace(
            id=1
        )

        db.execute.return_value = existing_result

        user = UserRegister(
            email="duplicate@example.com",
            password="TestPassword123",
        )

        with self.assertRaises(HTTPException) as context:
            register_user(
                user,
                db,
            )

        self.assertEqual(
            context.exception.status_code,
            409,
        )

        db.commit.assert_not_called()

    def test_registration_hashes_password_and_commits(self):
        db = MagicMock()

        email_check = MagicMock()
        email_check.first.return_value = None

        inserted_user = MagicMock()
        inserted_user.first.return_value = SimpleNamespace(
            id=1,
            email="newuser@example.com",
            username=None,
            display_name="New User",
            is_active=True,
            created_at=datetime.now(),
        )

        db.execute.side_effect = [
            email_check,
            inserted_user,
        ]

        user = UserRegister(
            email="newuser@example.com",
            display_name="New User",
            password="TestPassword123",
        )

        response = register_user(
            user,
            db,
        )

        self.assertEqual(
            str(response.email),
            "newuser@example.com",
        )

        self.assertEqual(
            response.display_name,
            "New User",
        )

        self.assertTrue(
            response.is_active
        )

        db.commit.assert_called_once()

        insert_parameters = (
            db.execute.call_args_list[1].args[1]
        )

        stored_hash = insert_parameters[
            "password_hash"
        ]

        self.assertNotEqual(
            stored_hash,
            "TestPassword123",
        )

        self.assertTrue(
            bcrypt.checkpw(
                b"TestPassword123",
                stored_hash.encode("utf-8"),
            )
        )


if __name__ == "__main__":
    unittest.main()