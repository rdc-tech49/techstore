# Generated by Django 5.1.7 on 2025-04-10 08:06

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('techstore', '0004_product_rv_details_alter_product_reference_details'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='LoanRegister',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity_supplied_in_loan', models.PositiveIntegerField()),
                ('date_supplied', models.DateField()),
                ('received_person_name', models.CharField(max_length=100)),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='techstore.productcategory')),
                ('model', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='techstore.product')),
                ('supplied_to', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
