from decimal import Decimal
from django.db import migrations, models


def migrate_schema(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("PRAGMA table_info(accounts_useraccount)")
        cols = {row[1] for row in cursor.fetchall()}

    has_balance = 'balance_usd' in cols
    has_cash = 'cash_balance' in cols

    if has_balance and not has_cash:
        with schema_editor.connection.cursor() as cursor:
            cursor.execute(
                "ALTER TABLE accounts_useraccount "
                "ADD COLUMN cash_balance decimal NOT NULL DEFAULT 0"
            )
            cursor.execute(
                "UPDATE accounts_useraccount SET cash_balance = balance_usd"
            )
            cursor.execute(
                "ALTER TABLE accounts_useraccount DROP COLUMN balance_usd"
            )
    elif has_balance and has_cash:
        with schema_editor.connection.cursor() as cursor:
            cursor.execute(
                "UPDATE accounts_useraccount SET cash_balance = balance_usd"
            )
            cursor.execute(
                "ALTER TABLE accounts_useraccount DROP COLUMN balance_usd"
            )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_connectedwallet_seed_word_count_and_more"),
    ]

    operations = [
        migrations.RunPython(migrate_schema, atomic=True),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(
                    model_name="useraccount",
                    name="balance_usd",
                ),
                migrations.AddField(
                    model_name="useraccount",
                    name="cash_balance",
                    field=models.DecimalField(
                        decimal_places=2, default=Decimal("0"), max_digits=18
                    ),
                ),
            ],
            database_operations=[],
        ),
    ]
