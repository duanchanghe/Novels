# Generated migration for field changes

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_add_sentence_model"),
    ]

    operations = [
        # Rename role to speaker in AudioSegment
        migrations.RenameField(
            model_name="audiosegment",
            old_name="role",
            new_name="speaker",
        ),
        # Change speed from CharField to FloatField
        migrations.AlterField(
            model_name="audiosegment",
            name="speed",
            field=models.FloatField(default=1.0, verbose_name="语速"),
        ),
        # Change pause_after from CharField to FloatField
        migrations.AlterField(
            model_name="audiosegment",
            name="pause_after",
            field=models.FloatField(default=0.3, verbose_name="段后停顿(秒)"),
        ),
    ]
