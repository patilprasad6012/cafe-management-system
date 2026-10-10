from flask import Blueprint, render_template, session, request, redirect, url_for, flash, jsonify
from app.models.models import MenuItem, Category, Order, OrderItem, OrderStatusHistory, Table
from app import db
from app.utils.decorators import login_required
from decimal import Decimal
from app.services.ai_assistant import CafeAIAssistant


customer_bp = Blueprint('customer', __name__)


# Customer Dashboard
@customer_bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('customer/dashboard.html')


# Digital Menu
@customer_bp.route('/menu')
def menu():
    table_number = request.args.get('table')

    if table_number:
        session['table_number'] = table_number

    categories = Category.query.filter_by(is_active=True).all()
    items = MenuItem.query.filter_by(
        is_active=True,
        is_available=True
    ).all()

    return render_template(
        'customer/menu.html',
        categories=categories,
        items=items
    )


# Shopping Cart
@customer_bp.route('/cart', methods=['GET', 'POST'])
@login_required
def cart():
    if 'cart' not in session:
        session['cart'] = {}

    if request.method == 'POST':
        item_id = request.form.get('item_id')
        action = request.form.get('action')

        item = MenuItem.query.get(item_id)

        if not item or not item.is_available or not item.is_active:
            flash('This item is currently unavailable.', 'error')
            return redirect(url_for('customer.menu'))

        str_item_id = str(item_id)

        if action == 'add':
            if str_item_id in session['cart']:
                session['cart'][str_item_id]['quantity'] += 1
            else:
                session['cart'][str_item_id] = {
                    'name': item.name,
                    'price': str(item.price),
                    'quantity': 1,
                    'image': item.image_path
                }

            flash(f'{item.name} added to cart!', 'success')

        elif action == 'decrease' and str_item_id in session['cart']:
            session['cart'][str_item_id]['quantity'] -= 1

            if session['cart'][str_item_id]['quantity'] <= 0:
                session['cart'].pop(str_item_id)

        elif action == 'remove' and str_item_id in session['cart']:
            session['cart'].pop(str_item_id)
            flash(f'{item.name} removed from cart.', 'info')

        session.modified = True
        return redirect(url_for('customer.cart'))

    subtotal = Decimal('0.00')
    cart_items = []

    for item_id, details in session.get('cart', {}).items():
        item_total = Decimal(details['price']) * details['quantity']
        subtotal += item_total

        details['id'] = item_id
        details['total'] = str(item_total)
        cart_items.append(details)

    tax = subtotal * Decimal('0.05')
    grand_total = subtotal + tax

    return render_template(
        'customer/cart.html',
        cart_items=cart_items,
        subtotal=subtotal,
        tax=tax,
        grand_total=grand_total
    )


# Checkout and Place Order
@customer_bp.route('/checkout', methods=['POST'])
@login_required
def checkout():
    if not session.get('cart'):
        flash('Your cart is empty!', 'error')
        return redirect(url_for('customer.menu'))

    table_number = session.get('table_number')

    if not table_number:
        flash('Please scan a table QR code before placing an order.', 'error')
        return redirect(url_for('customer.dashboard'))

    table = Table.query.filter_by(
        table_number=table_number,
        status='AVAILABLE'
    ).first()

    if not table:
        flash('Invalid or unavailable table. Please scan the QR again.', 'error')
        return redirect(url_for('customer.dashboard'))

    subtotal = Decimal('0.00')
    order_items_to_add = []

    # Recalculate item prices from the database
    for item_id, details in session['cart'].items():
        db_item = MenuItem.query.get(item_id)

        if not db_item or not db_item.is_active or not db_item.is_available:
            flash(
                f"Sorry, {details['name']} is no longer available.",
                'error'
            )
            return redirect(url_for('customer.cart'))

        quantity = details['quantity']
        price = db_item.price
        subtotal += price * quantity

        order_items_to_add.append(
            OrderItem(
                menu_item_id=db_item.id,
                quantity=quantity,
                price_at_time=price
            )
        )

    tax = subtotal * Decimal('0.05')
    grand_total = subtotal + tax

    new_order = Order(
        customer_id=session['user_id'],
        table_id=table.id,
        subtotal=subtotal,
        tax=tax,
        discount=Decimal('0.00'),
        grand_total=grand_total,
        status='PENDING_ADMIN_REVIEW'
    )

    db.session.add(new_order)
    db.session.flush()

    for order_item in order_items_to_add:
        order_item.order_id = new_order.id
        db.session.add(order_item)

    history = OrderStatusHistory(
        order_id=new_order.id,
        status='PENDING_ADMIN_REVIEW'
    )
    db.session.add(history)

    db.session.commit()

    session['cart'] = {}
    session.modified = True

    flash(
        'Your order has been placed successfully and is pending review!',
        'success'
    )

    return render_template(
        'customer/order_confirmation.html',
        order=new_order
    )


# Track Customer Orders
@customer_bp.route('/track-orders')
@login_required
def track_orders():
    active_statuses = [
        'PENDING_ADMIN_REVIEW',
        'ACCEPTED',
        'SENT_TO_CHEF',
        'PREPARING',
        'READY',
        'SERVED'
    ]

    orders = Order.query.filter(
        Order.customer_id == session['user_id'],
        Order.status.in_(active_statuses)
    ).order_by(Order.created_at.desc()).all()

    return render_template(
        'customer/track_orders.html',
        orders=orders
    )


# Customer Order History
@customer_bp.route('/order-history')
@login_required
def order_history():
    orders = Order.query.filter_by(
        customer_id=session['user_id']
    ).order_by(Order.created_at.desc()).all()

    return render_template(
        'customer/order_history.html',
        orders=orders
    )



@customer_bp.route('/ai-assistant', methods=['GET', 'POST'])
@login_required
def ai_assistant():
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        message = (data.get('message') or '').strip()

        if not message:
            return jsonify({'error': 'Message is required'}), 400

        text = message.lower()
        budget_match = __import__('re').search(
            r'(?:under|below|less than|within|budget of)\s*₹?\s*(\d+)',
            text
        )

        asks_menu = any(word in text for word in [
            'menu', 'show manu', 'show food', 'food items',
            'pizzas', 'coffee', 'vegetarian', 'veg food',
            'recommend food', 'suggest food'
        ])

        if asks_menu or budget_match:
            query = MenuItem.query.filter_by(
                is_active=True,
                is_available=True
            )

            if any(word in text for word in [
                'vegetarian', 'vegetarian food', 'veg food',
                'veg items', 'pure veg'
            ]):
                query = query.filter(MenuItem.veg_type == 'veg')

            if budget_match:
                budget = float(budget_match.group(1))
                query = query.filter(MenuItem.price <= budget)

            items = query.order_by(MenuItem.name.asc()).all()

            menu = [{
                'id': item.id,
                'name': item.name,
                'category': item.category.name if item.category else 'Other',
                'price': float(item.price),
                'description': item.description or '',
                'veg_type': item.veg_type or 'veg',
                'image_path': item.image_path or ''
            } for item in items]

            return jsonify({
                'type': 'menu',
                'response': (
                    f"Here are our available items under ₹{budget_match.group(1)}."
                    if budget_match else
                    "Welcome to King Cafe! Here is our current menu."
                ),
                'items': menu
            })

        ai = CafeAIAssistant()
        return jsonify({
            'type': 'text',
            'response': ai.get_response(message)
        })

    return render_template('customer/ai_assistant.html')
