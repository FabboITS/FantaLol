from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.TextChoices):
    USER = "USER", "Utente"
    ADMIN = "ADMIN", "Amministratore"


class User(AbstractUser):
    """Utente registrato. Il ruolo ``ADMIN`` corrisponde all'amministratore globale."""

    username = models.CharField(max_length=50, unique=True)
    email = models.EmailField(max_length=150, unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.USER)
    created_at = models.DateTimeField(auto_now_add=True)

    REQUIRED_FIELDS = ["email"]

    class Meta:
        db_table = "users"
        ordering = ["id"]

    @property
    def is_global_admin(self) -> bool:
        return self.role == Role.ADMIN

    def save(self, *args, **kwargs):
        # L'admin globale può usare anche l'admin Django.
        self.is_staff = self.role == Role.ADMIN or self.is_superuser
        super().save(*args, **kwargs)


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    nome_visualizzato = models.CharField(max_length=60, null=True, blank=True)
    bio = models.CharField(max_length=255, null=True, blank=True)
    avatar_url = models.CharField(max_length=255, null=True, blank=True)
    summoner_name = models.CharField(max_length=60, null=True, blank=True)

    class Meta:
        db_table = "user_profiles"
