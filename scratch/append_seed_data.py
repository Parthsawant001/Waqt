import re

with open('restaurants/management/commands/seed_waqt_data.py', 'r', encoding='utf-8') as f:
    content = f.read()

kitchen_seed_code = """
        # 9. Kitchen Orders (DEMO DATA)
        from restaurants.models import KitchenOrder, KitchenOrderItem
        import random
        for rest in saved_restaurants:
            menu_items = list(rest.menu_items.all())
            occupied_tables = list(rest.tables.filter(status='OCCUPIED'))
            for idx, table in enumerate(occupied_tables):
                status = 'PREPARING' if idx % 2 == 0 else 'NEW'
                ko = KitchenOrder.objects.create(
                    restaurant=rest,
                    table=table,
                    order_number=f"DEMO-{random.randint(1000, 9999)}",
                    status=status,
                    notes='DEMO DATA'
                )
                if menu_items:
                    m1 = random.choice(menu_items)
                    m2 = random.choice(menu_items)
                    KitchenOrderItem.objects.create(kitchen_order=ko, menu_item=m1, quantity=2, unit_price=m1.price)
                    KitchenOrderItem.objects.create(kitchen_order=ko, menu_item=m2, quantity=1, unit_price=m2.price)
"""

if '# 9. Kitchen Orders' not in content:
    content = content.replace('        self.stdout.write(self.style.SUCCESS("Successfully seeded Waqt coastal platform!"))', kitchen_seed_code + '\n        self.stdout.write(self.style.SUCCESS("Successfully seeded Waqt coastal platform!"))')
    with open('restaurants/management/commands/seed_waqt_data.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Added Kitchen Orders seed.")
else:
    print("Already seeded Kitchen Orders.")
