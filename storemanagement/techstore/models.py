from django.db import models

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
    reference_details = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    warranty_expiry_date = models.DateField(blank=True, null=True)
    vendor_details = models.TextField(blank=True, null=True)
    delivery_challan = models.FileField(upload_to='delivery_challans/', blank=True, null=True)