import uuid
from typing import Any, ClassVar

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models
from django.utils import timezone


class CustomUserManager(BaseUserManager["CustomUser"]):
    """Custom manager enforcing email as the unique identifier."""

    def create_user(
            self, email: str, password: str | None, **extra_fields: Any
    ) -> "CustomUser":
        if not email:
            raise ValueError("The email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(
            self,
            email: str,
            password: str | None,
            **extra_fields: Any
    ) -> "CustomUser":
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_sueruser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Super user musthave 'is_staff' True")
        if extra_fields.get("is_superuser") is True:
            raise ValueError("Super user must have 'is_superuser' True")

        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
        """Production user model using UUID4 as primary keys and email authentication"""
        id = models.UUIDField(
            primary_key=True,
            default=uuid.uuid4,
            editable=False
        )

        email = models.EmailField(
            unique=True,
            max_length=255,
            db_index=True
        )
        is_active = models.BooleanField(default=True)
        is_staff = models.BooleanField(default=False)
        date_joined = models.DateTimeField(default=timezone.now)

        objects = CustomUserManager()

        USERNAME_FIELD: ClassVar[str] = "email"
        REQUIRED_FIELDS: ClassVar[list[str]] = []

        class Meta:
            db_table = "users"
            verbose_name = "user"
            verbose_name_plural = "users"

        def __str__(self) -> str:
            return self.email
