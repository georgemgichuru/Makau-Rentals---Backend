from django.db import models
from auth.models import User


# Property's model

# Building Table for the different types of buildings
class Building(models.Model):
    name = models.CharField(max_length=200)
    address = models.TextField()
    city = models.CharField(max_length=100)
    landlord = models.ForeignKey(User, on_delete=models.CASCADE)
    total_units = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        permissions = [
            ("can_approve_rentals", "Can approve rental applications"),
            ("can_edit_building", "Can edit building details"),
        ]
# A unit is a section of the building
class Unit(models.Model):
    building = models.ForeignKey(Building, on_delete=models.CASCADE)
    unit_number = models.CharField(max_length=10)
    kplc_account_number = models.CharField(max_length=50, blank=True)
    rent_amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_occupied = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['building', 'unit_number']
        permissions = [
            # Unit details include the unit rent amount, is occupied
            ("can_edit_unit", "can edit unit details"),
            ("can_view_unit", "can view unit details")
        ]