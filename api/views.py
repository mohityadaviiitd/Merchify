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

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAdminUser()]

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
        quantity = request.data.get('quantity', 1)

        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )
        if not created:
            cart_item.quantity += int(quantity)
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
        quantity = request.data.get('quantity', 1)
        try:
            cart_item = CartItem.objects.get(id=cart_item_id)
            cart_item.quantity = quantity
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
            # Update product stock
            item.product.stock -= item.quantity
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

        frontend_base = getattr(settings, 'FRONTEND_BASE_URL', 'http://localhost:3000')
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
    total_revenue = Order.objects.filter(status='completed').aggregate(Sum('total_price'))['total_price__sum'] or 0

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
