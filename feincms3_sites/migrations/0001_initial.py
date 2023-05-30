# Generated by Django 2.0.4 on 2018-04-12 09:25

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Site",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "is_default",
                    models.BooleanField(default=False, verbose_name="is default"),
                ),
                ("host", models.CharField(max_length=200, verbose_name="host")),
                (
                    "host_re",
                    models.CharField(
                        blank=True,
                        max_length=200,
                        verbose_name="host regular expression",
                    ),
                ),
            ],
            options={"verbose_name": "site", "verbose_name_plural": "sites"},
        )
    ]
