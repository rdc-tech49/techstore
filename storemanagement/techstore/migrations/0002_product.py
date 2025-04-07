# Generated by Django 5.1.7 on 2025-04-07 11:20

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('techstore', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('model', models.CharField(max_length=100)),
                ('quantity', models.PositiveIntegerField()),
                ('purchased_date', models.DateField()),
                ('reference_details', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True, null=True)),
                ('warranty_expiry_date', models.DateField(blank=True, null=True)),
                ('vendor_details', models.TextField(blank=True, null=True)),
                ('delivery_challan', models.FileField(blank=True, null=True, upload_to='delivery_challans/')),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='techstore.productcategory')),
            ],
        ),
    ]
