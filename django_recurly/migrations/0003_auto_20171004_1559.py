# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2017-10-04 15:59
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('django_recurly', '0002_auto_20171004_1535'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='cc_emails',
            field=models.TextField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='account',
            name='closed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='account',
            name='tax_exempt',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='account',
            name='updated_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='account',
            name='vat_number',
            field=models.CharField(blank=True, default='', max_length=50),
        ),
        migrations.AlterField(
            model_name='account',
            name='hosted_login_token',
            field=models.CharField(blank=True, default='', max_length=40),
        ),
    ]