# Generated manually for UUID migration - STEP 2
# Makes ChannelSet.editors M2M through model explicit
# Uses SeparateDatabaseAndState because the table already exists (auto-created by Django)
from django.conf import settings
from django.db import migrations
import django.db.models as models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("contentcuration", "0158_channelset_add_uuid_shadow"),
    ]

    operations = [
        # Use SeparateDatabaseAndState because the through table already exists
        # Django auto-created it when ChannelSet.editors was defined without explicit through
        migrations.SeparateDatabaseAndState(
            # State operations: Register the model in Django's migration state
            state_operations=[
                migrations.CreateModel(
                    name="ChannelSetEditors",
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
                            "channelset",
                            models.ForeignKey(
                                db_column="channelset_id",
                                on_delete=django.db.models.deletion.CASCADE,
                                to="contentcuration.channelset",
                            ),
                        ),
                        (
                            "user",
                            models.ForeignKey(
                                db_column="user_id",
                                on_delete=django.db.models.deletion.CASCADE,
                                to=settings.AUTH_USER_MODEL,
                            ),
                        ),
                    ],
                    options={
                        "db_table": "contentcuration_channelset_editors",
                    },
                ),
                migrations.AlterUniqueTogether(
                    name="channelseteditors",
                    unique_together={("channelset", "user")},
                ),
            ],
            # Database operations: None - the table already exists
            database_operations=[
                # No-op SQL to verify table exists
                migrations.RunSQL(
                    """
                    -- Verify the through table exists
                    SELECT 1 FROM contentcuration_channelset_editors LIMIT 0;
                    """,
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
        ),
        # Update the M2M field to use the explicit through model
        migrations.AlterField(
            model_name="channelset",
            name="editors",
            field=models.ManyToManyField(
                blank=True,
                help_text="Users with edit rights",
                related_name="channel_sets",
                through="contentcuration.ChannelSetEditors",
                to=settings.AUTH_USER_MODEL,
                verbose_name="editors",
            ),
        ),
    ]
