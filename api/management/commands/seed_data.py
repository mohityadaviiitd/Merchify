from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from api.models import Category, Product, Cart

class Command(BaseCommand):
    help = 'Seed the database with sample users, categories, and products'

    def handle(self, *args, **options):
        self.stdout.write('Seeding database...')

        # Create admin user
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'AdminPass123')
            self.stdout.write('Created superuser: admin / AdminPass123')
        else:
            self.stdout.write('Superuser admin already exists')

        # Create regular users
        users = [
            {'username': 'alice', 'email': 'alice@example.com', 'password': 'Password123'},
            {'username': 'bob', 'email': 'bob@example.com', 'password': 'Password123'},
        ]
        for u in users:
            if not User.objects.filter(username=u['username']).exists():
                user = User.objects.create_user(u['username'], u['email'], u['password'])
                Cart.objects.get_or_create(user=user)
                self.stdout.write(f"Created user: {u['username']} / {u['password']}")
            else:
                self.stdout.write(f"User {u['username']} already exists")

        # Create categories
        categories = [
            {'name': 'T-Shirts', 'description': 'Graphic and logo t-shirts'},
            {'name': 'Hoodies', 'description': 'Warm hoodies and sweatshirts'},
            {'name': 'Accessories', 'description': 'Stickers, pins, and more'},
        ]
        for c in categories:
            cat, created = Category.objects.get_or_create(name=c['name'], defaults={'description': c['description']})
            if created:
                self.stdout.write(f"Created category: {cat.name}")
            else:
                self.stdout.write(f"Category {cat.name} already exists")

        # Create products
        products = [
            {'name': 'Logo Tee', 'description': '100% cotton logo tee', 'category': 'T-Shirts', 'price': 19.99, 'stock': 50},
            {'name': 'Tour Tee', 'description': 'Limited edition tour tee', 'category': 'T-Shirts', 'price': 29.99, 'stock': 30},
            {'name': 'Classic Hoodie', 'description': 'Cozy classic hoodie', 'category': 'Hoodies', 'price': 49.99, 'stock': 40},
            {'name': 'Zip Hoodie', 'description': 'Zipped hoodie with pockets', 'category': 'Hoodies', 'price': 59.99, 'stock': 20},
            {'name': 'Sticker Pack', 'description': 'Pack of 5 stickers', 'category': 'Accessories', 'price': 4.99, 'stock': 200},
            {'name': 'Enamel Pin', 'description': 'Collectible enamel pin', 'category': 'Accessories', 'price': 9.99, 'stock': 150},
        ]

        for p in products:
            cat = Category.objects.get(name=p['category'])
            prod, created = Product.objects.get_or_create(
                name=p['name'],
                defaults={
                    'description': p['description'],
                    'category': cat,
                    'price': p['price'],
                    'stock': p['stock'],
                    'is_active': True,
                }
            )
            if created:
                self.stdout.write(f"Created product: {prod.name}")
            else:
                # update price/stock in case data changed
                prod.price = p['price']
                prod.stock = p['stock']
                prod.category = cat
                prod.is_active = True
                prod.save()
                self.stdout.write(f"Updated product: {prod.name}")

        self.stdout.write('Seeding complete.')
