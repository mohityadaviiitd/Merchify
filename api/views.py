from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from django.contrib.auth.models import User
from django.db.models import Count, Sum, Q
from datetime import datetime, timedelta
import stripe
from django.conf import settings
from django.core.cache import cache

# ...existing code...

# Stripe Webhook to update order status after payment
@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', None)
    event = None
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        return Response({'error': 'Invalid payload'}, status=400)
    except stripe.error.SignatureVerificationError as e:
        return Response({'error': 'Invalid signature'}, status=400)

    # Handle the checkout.session.completed event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        order_id = session.get('metadata', {}).get('order_id')
        if order_id:
            from .models import Order
            try:
                order = Order.objects.get(id=order_id)
                order.status = 'completed'
                order.payment_id = session.get('payment_intent')
                order.save()
            except Order.DoesNotExist:
                pass
    return Response({'status': 'success'})
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from django.contrib.auth.models import User
from django.db.models import Count, Sum, Q
from datetime import datetime, timedelta
import stripe
from django.conf import settings

# Configure stripe with secret key from settings
stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', None)
from .models import Category, Product, Order, OrderItem, Cart, CartItem
from .serializers import (
    UserSerializer,
    UserRegistrationSerializer,
    CategorySerializer,
    ProductSerializer,
    OrderSerializer,
    CartSerializer,
    CartItemSerializer,
)


# User Authentication Views
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'message': 'User registered successfully'
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    from django.contrib.auth import authenticate
    username = request.data.get('username')
    password = request.data.get('password')
    user = authenticate(username=username, password=password)
    if user:
        from rest_framework.authtoken.models import Token
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user': UserSerializer(user).data
        })
    return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user(request):
    return Response(UserSerializer(request.user).data)


# Category ViewSet
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAdminUser()]


# Product ViewSet
class ProductViewSet(viewsets.ModelViewSet):

    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    from rest_framework.parsers import MultiPartParser, FormParser
    parser_classes = (MultiPartParser, FormParser)

    def list(self, request, *args, **kwargs):
    # 1. Check if the method is actually being triggered
        print("DEBUG 1: Entering the custom list method!")
        
        cache_key = "products:all_list"
        cached_data = cache.get(cache_key)
        
        if cached_data is not None:
            print("DEBUG 2: Cache Hit! Returning data from Redis.")
            return Response(cached_data)
            
        print("DEBUG 3: Cache Miss! Fetching fresh data from Database.")
        response = super().list(request, *args, **kwargs)
        
        # 2. Inspect exactly what data Django is trying to save
        print(f"DEBUG 4: Data payload to save: {type(response.data)}")
        
        try:
            cache.set(cache_key, response.data, timeout=600)
            print("DEBUG 5: Successfully executed cache.set() without errors!")
        except Exception as cache_error:
            print(f"DEBUG 6: Redis write failed! Error: {cache_error}")
            
        return response
        
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAdminUser()]

    def create(self, request, *args, **kwargs):
        # Save image to local_images, then upload to S3, then store S3 URL in image field
        import os
        import boto3
        from django.conf import settings
        data = request.data.copy()
        if 'is_active' not in data or data['is_active'] in [None, '', False, 'false', 'False', 0, '0']:
            data['is_active'] = True
        image_file = request.FILES.get('image')
        s3_url = ''
        local_path = None
        if image_file:
            from urllib.parse import quote
            # Save to local_images
            local_dir = os.path.join(settings.BASE_DIR, 'local_images')
            os.makedirs(local_dir, exist_ok=True)
            local_path = os.path.join(local_dir, image_file.name)
            with open(local_path, 'wb+') as f:
                for chunk in image_file.chunks():
                    f.write(chunk)
            # Upload to S3
            s3 = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME
            )
            bucket = settings.AWS_STORAGE_BUCKET_NAME
            s3_key = f'product_images/{image_file.name}'
            s3_key_encoded = quote(s3_key)
            try:
                s3.upload_file(local_path, bucket, s3_key)
                s3_url = f'https://{bucket}.s3.amazonaws.com/{s3_key_encoded}'
                data['image'] = s3_url
            except Exception as e:
                import traceback
                print(f'Failed to upload image to S3: {e}')
                print(traceback.format_exc())
                return Response({'error': f'Failed to upload image to S3: {e}'}, status=400)
        # Ensure image is a valid S3 URL or empty string
        img_val = data.get('image', '')
        if img_val and not img_val.startswith('http'):
            from urllib.parse import quote
            bucket = settings.AWS_STORAGE_BUCKET_NAME
            img_val_encoded = quote(img_val.lstrip('/'))
            data['image'] = f"https://{bucket}.s3.amazonaws.com/{img_val_encoded}"
        if not data.get('image'):
            data['image'] = ''
        print('DEBUG: data["image"] =', data.get('image'))
        # Only validate if not empty and starts with https://
        from django.core.validators import URLValidator
        url_val = URLValidator(schemes=['http', 'https'])
        img_url = data.get('image', '')
        if img_url:
            if not (img_url.startswith('http://') or img_url.startswith('https://')):
                bucket = settings.AWS_STORAGE_BUCKET_NAME
                img_url = f"https://{bucket}.s3.amazonaws.com/{img_url.lstrip('/')}"
                data['image'] = img_url
            try:
                url_val(img_url)
            except Exception as e:
                import traceback
                print('DEBUG: image is not a valid URL, setting to empty string')
                print(traceback.format_exc())
                return Response({'error': f'Image URL is invalid: {e}'}, status=400)
        print('DEBUG: FINAL data["image"] =', data.get('image'))
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        cache.delete("products:all_list")
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=False, methods=['get'])
    def by_category(self, request):
        category_id = request.query_params.get('category_id')
        if category_id:
            products = self.queryset.filter(category_id=category_id)
            serializer = self.get_serializer(products, many=True)
            return Response(serializer.data)
        return Response({'error': 'category_id required'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def search(self, request):
        query = request.query_params.get('q', '')
        products = self.queryset.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)


# Cart ViewSet
class CartViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def my_cart(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        serializer = CartSerializer(cart)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def add_item(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        product_id = request.data.get('product_id')
        quantity = int(request.data.get('quantity', 1))

        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)

        # Mark product as inactive if stock is zero
        if product.stock == 0:
            product.is_active = False
            product.save()
            return Response({'error': 'Product is out of stock and has been marked inactive.'}, status=status.HTTP_410_GONE)

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': min(quantity, product.stock)}
        )
        if not created:
            new_qty = cart_item.quantity + quantity
            if new_qty > product.stock:
                cart_item.quantity = product.stock
            else:
                cart_item.quantity = new_qty
            cart_item.save()

        serializer = CartSerializer(cart)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def remove_item(self, request):
        cart_item_id = request.data.get('cart_item_id')
        CartItem.objects.filter(id=cart_item_id).delete()
        cart, _ = Cart.objects.get_or_create(user=request.user)
        serializer = CartSerializer(cart)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def update_item(self, request):
        cart_item_id = request.data.get('cart_item_id')
        quantity = int(request.data.get('quantity', 1))
        try:
            cart_item = CartItem.objects.get(id=cart_item_id)
            product = cart_item.product
            # Mark product as inactive if stock is zero
            if product.stock == 0:
                product.is_active = False
                product.save()
                cart_item.delete()
                return Response({'error': 'Product is out of stock and has been marked inactive.'}, status=status.HTTP_410_GONE)
            # Enforce max quantity as product stock
            cart_item.quantity = min(quantity, product.stock)
            cart_item.save()
        except CartItem.DoesNotExist:
            return Response({'error': 'Cart item not found'}, status=status.HTTP_404_NOT_FOUND)

        cart, _ = Cart.objects.get_or_create(user=request.user)
        serializer = CartSerializer(cart)
        return Response(serializer.data)


# Order ViewSet
class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Order.objects.all()
        return Order.objects.filter(user=self.request.user)

    def create(self, request):
        cart = Cart.objects.get(user=request.user)
        cart_items = cart.items.all()

        if not cart_items.exists():
            return Response({'error': 'Cart is empty'}, status=status.HTTP_400_BAD_REQUEST)

        total_price = sum(item.product.price * item.quantity for item in cart_items)

        order = Order.objects.create(
            user=request.user,
            total_price=total_price,
            status='pending'
        )

        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price
            )
            # Update product stock and mark inactive if stock is 0
            item.product.stock -= item.quantity
            if item.product.stock <= 0:
                item.product.stock = 0
                item.product.is_active = False
            item.product.save()

        cart_items.delete()

        serializer = self.get_serializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def checkout(self, request, pk=None):
        order = self.get_object()
        stripe_token = request.data.get('stripe_token')

        try:
            charge = stripe.Charge.create(
                amount=int(order.total_price * 100),  # Stripe expects paise for INR
                currency='inr',
                source=stripe_token,
                description=f'Order {order.id}'
            )
            order.payment_id = charge.id
            order.status = 'completed'
            order.save()

            return Response({
                'message': 'Payment successful',
                'order': OrderSerializer(order).data
            })
        except stripe.error.StripeError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def create_checkout_session(self, request, pk=None):
        """Create a Stripe Checkout Session and return the session URL for redirecting the browser."""
        order = self.get_object()
        # Build line items for Stripe Checkout
        line_items = []
        for item in order.items.all():
            line_items.append({
                'price_data': {
                    'currency': 'inr',
                    'product_data': {
                        'name': item.product.name,
                    },
                    'unit_amount': int(item.price * 100),  # paise for INR
                },
                'quantity': item.quantity,
            })

        frontend_base = getattr(settings, 'FRONTEND_BASE_URL')
        success_url = f"{frontend_base}/checkout-success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{frontend_base}/checkout-cancel"

        try:
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=line_items,
                mode='payment',
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={'order_id': str(order.id)}
            )
            return Response({'url': session.url})
        except stripe.error.StripeError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        order = self.get_object()
        if order.status == 'pending':
            order.status = 'cancelled'
            order.save()
            # Restore product stock
            for item in order.items.all():
                item.product.stock += item.quantity
                item.product.save()
            return Response(OrderSerializer(order).data)
        return Response({'error': 'Cannot cancel completed order'}, status=status.HTTP_400_BAD_REQUEST)


# Dashboard/Analytics Views
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    if not request.user.is_staff:
        return Response({'error': 'Only admin can access'}, status=status.HTTP_403_FORBIDDEN)

    # Total stats
    total_products = Product.objects.count()
    total_users = User.objects.count()
    total_orders = Order.objects.count()
    total_revenue = Order.objects.filter(status__in=['pending', 'completed']).aggregate(Sum('total_price'))['total_price__sum'] or 0

    # Order status breakdown
    order_status = Order.objects.values('status').annotate(count=Count('id'))

    # Category breakdown
    category_breakdown = Category.objects.annotate(
        product_count=Count('products'),
        total_sold=Sum('products__orderitem__quantity')
    ).values('name', 'product_count', 'total_sold')

    # Top selling products
    top_products = Product.objects.annotate(
        total_sold=Sum('orderitem__quantity')
    ).order_by('-total_sold')[:10].values('name', 'total_sold', 'price')

    # Revenue trend (last 7 days)
    last_7_days = []
    for i in range(7):
        date = (datetime.now() - timedelta(days=i)).date()
        revenue = Order.objects.filter(
            status='completed',
            created_at__date=date
        ).aggregate(Sum('total_price'))['total_price__sum'] or 0
        last_7_days.append({'date': date, 'revenue': float(revenue)})

    return Response({
        'total_products': total_products,
        'total_users': total_users,
        'total_orders': total_orders,
        'total_revenue': float(total_revenue),
        'order_status': list(order_status),
        'category_breakdown': list(category_breakdown),
        'top_products': list(top_products),
        'revenue_trend': last_7_days
    })
