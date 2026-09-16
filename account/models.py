from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import AbstractUser
import re

class Country(models.Model):
    
    country_name = models.CharField(max_length=100,null=True,blank=True)
    def __str__(self):
        return f"{self.country_name}"

class State(models.Model):
    country_id = models.ForeignKey(Country, on_delete=models.CASCADE,null=True,blank=True)
    state_name = models.CharField(max_length=100,null=True,blank=True)
    def __str__(self):
        return f"{self.state_name}"

class City(models.Model):
    state_id = models.ForeignKey(State, on_delete=models.CASCADE,null=True,blank=True)
    city_name = models.CharField(max_length=100,null=True,blank=True)
    def __str__(self):
        return f"{self.city_name}"


class User(AbstractUser):
    user_id = models.CharField(max_length=10,unique=True)
    email = models.EmailField(unique=True)
    mobile = models.CharField(max_length=15,null=True,blank=True)
    role = models.CharField(max_length=50,null=True,blank=True)
    is_active = models.BooleanField(default=True)
    profile_image = models.ImageField(upload_to='profile_pic',null=True,blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'mobile', 'email']

    class Meta:
        permissions = [
            ("toggle_user_status", "Can toggle user status"),
            ("activate_user", "Can activate user"),
            ("deactivate_user", "Can deactivate user"),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
    def generate_user_id(self):
        first_initial = (self.first_name[:1] if self.first_name else "X").upper()
        last_initial = (self.last_name[:1] if self.last_name else "X").upper()

        prefix = f"{first_initial}{last_initial}"

        last_user = (
            User.objects.exclude(user_id__isnull=True)
            .exclude(user_id="")
            .order_by("-id")
            .first()
        )

        next_number = 1

        if last_user:
            match = re.search(r"(\d+)$", last_user.user_id)
            if match:
                next_number = int(match.group(1)) + 1

        if next_number > 9999:
            raise ValueError("Maximum user ID limit reached.")

        return f"{prefix}{next_number:04d}"

    def save(self, *args, **kwargs):
        if not self.user_id:
            self.user_id = self.generate_user_id()

        super().save(*args, **kwargs)

class User_Profile(models.Model):
    user = models.OneToOneField(User,on_delete=models.CASCADE,related_name='user_profile')
    country = models.ForeignKey(Country,on_delete=models.CASCADE,related_name="country")
    state = models.ForeignKey(State,on_delete=models.CASCADE,related_name="state")
    city = models.ForeignKey(City,on_delete=models.CASCADE,related_name='city')
    address = models.TextField(null=True,blank=True)
    pin_code = models.PositiveIntegerField()
    created_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user}--{self.address}"


# /////// Model for the roles and permissions //////////////

class CustomRole(models.Model):
    name = models.CharField(max_length=100, unique=True)
    permissions = models.ManyToManyField('auth.Permission')
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    

# //////////////////////Custom Permission for Sample Page//////////////////

class TestModel(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        permissions = [
            ("view_sample_page1", "Can view Sample Page 1"),
        ]