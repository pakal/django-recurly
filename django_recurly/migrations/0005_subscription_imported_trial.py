# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2017-11-09 15:17
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('django_recurly', '0004_subscription_collection_method'),
    ]

    operations = [
        migrations.AddField(
            model_name='subscription',
            name='imported_trial',
            field=models.BooleanField(default=False),
        ),
    ]