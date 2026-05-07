from django.db import migrations


class Migration(migrations.Migration):
    """
    Product.stock was removed from the DB outside of Django migrations.
    This migration updates the migration state to match the DB.
    """

    dependencies = [
        ('core', '0003_remove_product_stock_productbatch_max_order_qty_and_more'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RemoveField(
                    model_name='product',
                    name='stock',
                ),
            ],
        ),
    ]
