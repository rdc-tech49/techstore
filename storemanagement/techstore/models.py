from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class ProductCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Product(models.Model):
    category = models.ForeignKey(ProductCategory, on_delete=models.CASCADE)
    model = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField()
    purchased_date = models.DateField()
    reference_details = models.CharField(max_length=100)
    rv_details = models.CharField(max_length=100,blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    warranty_expiry_date = models.DateField(blank=True, null=True)
    vendor_details = models.TextField(blank=True, null=True)
    delivery_challan = models.FileField(upload_to='delivery_challans/', blank=True, null=True)


class SupplyOrder(models.Model):
    category = models.ForeignKey('ProductCategory', on_delete=models.CASCADE)
    model = models.ForeignKey('Product', on_delete=models.CASCADE)
    quantity_supplied = models.PositiveIntegerField()
    supplied_date = models.DateField()
    supplied_to = models.ForeignKey(User, on_delete=models.CASCADE)
    received_person_name = models.CharField(max_length=255)
    iv_number = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.model.model} to {self.supplied_to.username}"

class LoanRegister(models.Model):
    category = models.ForeignKey(ProductCategory, on_delete=models.CASCADE)
    model = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity_supplied_in_loan = models.PositiveIntegerField()
    date_supplied = models.DateField()
    supplied_to = models.ForeignKey(User, on_delete=models.CASCADE)
    received_person_name = models.CharField(max_length=100)

    def __str__(self):
        return f"Loan to {self.supplied_to.username} - {self.model.model}"