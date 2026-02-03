#!/usr/bin/env python
"""
Backend API Testing Script
Test all major endpoints to verify the backend is working correctly
"""

import requests
import json

BASE_URL = "http://localhost:8000/api"

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def print_result(status, message, data=None):
    status_emoji = "✓" if status else "✗"
    print(f"{status_emoji} {message}")
    if data and isinstance(data, dict):
        print(f"  Response: {json.dumps(data, indent=2)[:200]}...")

# Test 1: Check if API is accessible
print_section("TEST 1: API Connectivity")
try:
    response = requests.get(f"{BASE_URL}/products/", timeout=5)
    if response.status_code in [200, 401]:
        print_result(True, "✓ API is accessible")
    else:
        print_result(False, f"✗ Unexpected status code: {response.status_code}")
except Exception as e:
    print_result(False, f"✗ API connection failed: {str(e)}")

# Test 2: Register a new user
print_section("TEST 2: User Registration")
register_data = {
    "username": f"testuser_{hash('test')%10000}",
    "email": "testuser@example.com",
    "password": "TestPassword123",
    "password_confirm": "TestPassword123",
    "first_name": "Test",
    "last_name": "User"
}
try:
    response = requests.post(f"{BASE_URL}/auth/register/", json=register_data)
    if response.status_code == 201:
        print_result(True, "✓ User registration successful")
        user_data = response.json()
        print(f"  User ID: {user_data.get('id')}")
        print(f"  Username: {user_data.get('username')}")
    else:
        print_result(False, f"✗ Registration failed: {response.status_code}")
        print(f"  Error: {response.text[:200]}")
except Exception as e:
    print_result(False, f"✗ Registration request failed: {str(e)}")

# Test 3: User Login
print_section("TEST 3: User Login")
login_data = {
    "username": "testuser",
    "password": "TestPassword123"
}
auth_token = None
try:
    response = requests.post(f"{BASE_URL}/auth/login/", json=login_data)
    if response.status_code == 200:
        data = response.json()
        auth_token = data.get('token')
        print_result(True, "✓ User login successful")
        print(f"  Auth Token: {auth_token[:20]}...")
    else:
        print_result(False, f"✗ Login failed: {response.status_code}")
except Exception as e:
    print_result(False, f"✗ Login request failed: {str(e)}")

# Test 4: Get Products
print_section("TEST 4: Get Products")
try:
    response = requests.get(f"{BASE_URL}/products/")
    if response.status_code == 200:
        products = response.json()
        print_result(True, f"✓ Retrieved products successfully")
        print(f"  Total Products: {len(products.get('results', []))}")
    else:
        print_result(False, f"✗ Failed to get products: {response.status_code}")
except Exception as e:
    print_result(False, f"✗ Products request failed: {str(e)}")

# Test 5: Get Categories
print_section("TEST 5: Get Categories")
try:
    response = requests.get(f"{BASE_URL}/categories/")
    if response.status_code == 200:
        categories = response.json()
        print_result(True, f"✓ Retrieved categories successfully")
        print(f"  Total Categories: {len(categories.get('results', []))}")
    else:
        print_result(False, f"✗ Failed to get categories: {response.status_code}")
except Exception as e:
    print_result(False, f"✗ Categories request failed: {str(e)}")

# Test 6: Check Database
print_section("TEST 6: Database Connection")
try:
    import os
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'merchify_backend.settings')
    django.setup()
    
    from django.contrib.auth.models import User
    from api.models import Category, Product, Order, Cart
    
    user_count = User.objects.count()
    category_count = Category.objects.count()
    product_count = Product.objects.count()
    order_count = Order.objects.count()
    
    print_result(True, "✓ Database connection successful")
    print(f"  Users: {user_count}")
    print(f"  Categories: {category_count}")
    print(f"  Products: {product_count}")
    print(f"  Orders: {order_count}")
except Exception as e:
    print_result(False, f"✗ Database check failed: {str(e)}")

# Summary
print_section("SUMMARY")
print("\n✓ If all tests passed, your backend is working correctly!\n")
print("Next steps:")
print("1. ✓ Visit http://localhost:8000/admin/ to access Django admin")
print("2. ✓ Login with your superuser credentials")
print("3. ✓ Create some categories and products in the admin panel")
print("4. ✓ Test API endpoints using the commands below\n")

print("Sample API Test Commands (copy-paste in PowerShell):\n")
print("# Get all products:")
print('curl.exe http://localhost:8000/api/products/\n')

print("# Create a category (requires admin token):")
print('curl.exe -X POST http://localhost:8000/api/categories/ `')
print('  -H "Authorization: Token YOUR_TOKEN" `')
print('  -H "Content-Type: application/json" `')
print('  -d \'{{"name":"T-Shirts","description":"Merchandise t-shirts"}}\'\n')

print("# Register new user:")
print('curl.exe -X POST http://localhost:8000/api/auth/register/ `')
print('  -H "Content-Type: application/json" `')
print('  -d \'{{"username":"newuser","email":"user@test.com","password":"Pass123","password_confirm":"Pass123"}}\'\n')

print_section("Backend is Ready!")
