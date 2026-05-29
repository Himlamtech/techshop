import sys
sys.path.insert(0, '/home/iec/lamnh/university/techshop/services/catalog-service')
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from apps.catalog.serializers import ProductCreateSerializer, ProductFilterSerializer, ProductImportSerializer, ProductUpdateSerializer, BulkValidateSerializer, CategoryCreateSerializer

# Test ProductCreateSerializer validation (skip DB-dependent category_id check)
print('=== ProductCreateSerializer Tests (field-level only) ===')

# Invalid price (too low) - no category_id to avoid DB hit
valid_data = {
    'name': 'Test Product',
    'description': 'A test product description',
    'price': '29.99',
    'stock': 100,
    'brand': 'TestBrand',
    'category_id': '00000000-0000-0000-0000-000000000001',
    'image_urls': ['https://example.com/img.jpg'],
}

# Test field-level validation without hitting DB
# We test fields that don't require DB access

# Invalid price (too low) - remove category_id to avoid DB
no_cat_data = {
    'name': 'Test Product',
    'description': 'A test product description',
    'price': '0.00',
    'stock': 100,
    'brand': 'TestBrand',
    'category_id': '00000000-0000-0000-0000-000000000001',
    'image_urls': ['https://example.com/img.jpg'],
}
s = ProductCreateSerializer(data=no_cat_data)
s.is_valid()
assert 'price' in s.errors, f'Expected price error, got: {s.errors}'
print(f'Price 0.00: PASS - errors={s.errors.get("price")}')

# Invalid stock (too high)
invalid_stock = valid_data.copy()
invalid_stock['stock'] = 1000000
s = ProductCreateSerializer(data=invalid_stock)
s.is_valid()
assert 'stock' in s.errors, f'Expected stock error, got: {s.errors}'
print(f'Stock 1000000: PASS - errors={s.errors.get("stock")}')

# Missing image_urls
no_images = valid_data.copy()
no_images['image_urls'] = []
s = ProductCreateSerializer(data=no_images)
s.is_valid()
assert 'image_urls' in s.errors, f'Expected image_urls error, got: {s.errors}'
print(f'Empty images: PASS - errors={s.errors.get("image_urls")}')

# Name too long
long_name = valid_data.copy()
long_name['name'] = 'x' * 256
s = ProductCreateSerializer(data=long_name)
s.is_valid()
assert 'name' in s.errors, f'Expected name error, got: {s.errors}'
print(f'Name 256 chars: PASS - errors={s.errors.get("name")}')

# Missing required fields
s = ProductCreateSerializer(data={})
s.is_valid()
missing_fields = set(s.errors.keys())
expected_missing = {'name', 'description', 'price', 'stock', 'brand', 'category_id', 'image_urls'}
assert expected_missing.issubset(missing_fields), f'Expected {expected_missing}, got {missing_fields}'
print(f'Missing all fields: PASS - {len(missing_fields)} field errors')

# ProductUpdateSerializer - all optional
s = ProductUpdateSerializer(data={})
assert s.is_valid(), f'Empty update should be valid, got: {s.errors}'
print(f'Empty update (all optional): PASS')

s = ProductUpdateSerializer(data={'price': '50.00', 'status': 'inactive'})
assert s.is_valid(), f'Partial update should be valid, got: {s.errors}'
print(f'Partial update (price+status): PASS')

print()
print('=== ProductFilterSerializer Tests ===')

# Valid filter
valid_filter = {'search': 'laptop', 'sort': 'price_asc', 'page': 1, 'page_size': 20}
s = ProductFilterSerializer(data=valid_filter)
print(f'Valid filter: is_valid={s.is_valid()}')

# Invalid sort
invalid_sort = {'sort': 'invalid'}
s = ProductFilterSerializer(data=invalid_sort)
print(f'Invalid sort: is_valid={s.is_valid()}, errors={s.errors}')

# Search too short
short_search = {'search': 'a'}
s = ProductFilterSerializer(data=short_search)
print(f'Search 1 char: is_valid={s.is_valid()}, errors={s.errors.get("search", "none")}')

# Price range invalid
bad_range = {'min_price': '100.00', 'max_price': '50.00'}
s = ProductFilterSerializer(data=bad_range)
print(f'min > max price: is_valid={s.is_valid()}, errors={s.errors}')

print()
print('=== ProductImportSerializer Tests ===')

# DummyJSON product
dummy_product = {
    'id': 1,
    'title': 'iPhone 9',
    'description': 'An apple mobile phone',
    'price': 549,
    'stock': 94,
    'brand': 'Apple',
    'category': 'smartphones',
    'thumbnail': 'https://cdn.dummyjson.com/thumb.jpg',
    'images': ['https://cdn.dummyjson.com/img1.jpg', 'https://cdn.dummyjson.com/img2.jpg'],
}
s = ProductImportSerializer(data=dummy_product)
is_valid = s.is_valid()
print(f'DummyJSON product: is_valid={is_valid}')
if is_valid:
    d = s.validated_data
    print(f'  sku={d["sku"]}, name={d["name"]}, brand={d["brand"]}')
    print(f'  category_name={d["category_name"]}')
    print(f'  image_urls={d["image_urls"]}')
    print(f'  thumbnail_url={d["thumbnail_url"]}')
