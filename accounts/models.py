from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

class UserManager(BaseUserManager):
    """Manager for user profiles"""
    
    def create_user(self, email, password=None, **extra_fields):
        """Create a new user model"""
        if not email:
            raise ValueError('Users must have an email address')

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)

        return user
    def create_admin(self, email, password=None, **extra_fields):
        """Create new superuser profile"""
        if not email:
            raise ValueError('Users must have an email address')

        user = self.create_user(email, password=password, **extra_fields)
        user.is_superuser = False
        user.is_staff = True
        user.save(using=self._db)

        return user
    def create_superuser(self, email, password=None, **extra_fields):
        """Create new superuser profile"""
        if not email:
            raise ValueError('Users must have an email address')

        user = self.create_user(email, password=password, **extra_fields)
        user.is_superuser = True
        user.is_staff = True
        user.save(using=self._db)

        return user
class User(AbstractBaseUser, PermissionsMixin):
    """Custom User Model that support using email instead of username"""
    email = models.EmailField(max_length=255, unique=True)
    username = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'email'


