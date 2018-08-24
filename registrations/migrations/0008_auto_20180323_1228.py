# -*- coding: utf-8 -*-
# Generated by Django 1.9.1 on 2018-03-23 12:28
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('registrations', '0007_thirdpartyregistrationerror'),
    ]

    operations = [
        migrations.AlterField(
            model_name='registration',
            name='stage',
            field=models.CharField(choices=[('prebirth', 'Mother is pregnant'), ('postbirth', 'Baby has been born'), ('loss', 'Baby loss'), ('public', 'Public')], max_length=30),
        ),
    ]
