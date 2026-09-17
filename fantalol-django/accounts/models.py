"""Utenti FantaLoL: porting di `user/User`, `user/Role` e `user/UserProfile`."""
from __future__ import annotations

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class Role(models.TextChoices):
    USER = "USER", "USER"
    ADMIN = "ADMIN", "ADMIN"


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, username: str, email: str, password: str | None = None, **extra):
        if not username:
            raise ValueError("Lo username è obbligatorio")
        if not email:
            raise ValueError("L'email è obbligatoria")
        user = self.model(username=username, email=self.normalize_email(email), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username: str, email: str, password: str | None = None, **extra):
        extra.setdefault("role", Role.ADMIN)
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self.create_user(username, email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    """Utente registrato. `role` replica l'enum Java `Role` (USER/ADMIN)."""

    username = models.CharField(max_length=50, unique=True)
    email = models.EmailField(max_length=150, unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.USER)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    class Meta:
        db_table = "users"
        ordering = ["id"]

    def __str__(self) -> str:
        return self.username

    @property
    def is_global_admin(self) -> bool:
        return self.role == Role.ADMIN

    @property
    def is_active(self) -> bool:  # type: ignore[override]
        return self.enabled


class UserProfile(models.Model):
    """Profilo esteso opzionale (relazione OneToOne come in JPA)."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    nome_visualizzato = models.CharField(max_length=60, blank=True, null=True)
    bio = models.CharField(max_length=255, blank=True, null=True)
    avatar_url = models.CharField(max_length=255, blank=True, null=True)
    summoner_name = models.CharField(max_length=60, blank=True, null=True)

    class Meta:
        db_table = "user_profiles"

    def __str__(self) -> str:
        return f"Profilo di {self.user.username}"
