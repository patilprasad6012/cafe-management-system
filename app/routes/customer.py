from flask import Blueprint, render_template, session, request, redirect, url_for, flash, jsonify
from app.models.models import User, MenuItem, Category, Order, OrderItem, OrderStatusHistory, Table
from app import db
from app.utils.decorators import login_required
from decimal import Decimal
from datetime import date
from app.models.models import ComboOffer
from sqlalchemy.exc import IntegrityError
from app.services.ai_assistant import CafeAIAssistant
import re


customer_bp = Blueprint('customer', __name__)


# Customer Dashboard
@customer_bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('customer/dashboard.html')


# Customer Profile
@customer_bp.route('/profile')
@login_required
def profile():
    user = User.query.filter_by(id=session['user_id'], role='customer').first_or_404()
    return render_template('customer/profile.html', profile_user=user)


# Edit Customer Profile
@customer_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    user = User.query.filter_by(id=session['user_id'], role='customer').first_or_404()

    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        email = (request.form.get('email') or '').strip().lower()
        mobile = (request.form.get('mobile') or '').strip()
        dob_text = (request.form.get('date_of_birth') or '').strip()

        if not name or not email or not mobile:
            flash('Name, email and mobile number are required.', 'error')
            return render_template('customer/edit_profile.html', profile_user=user, today=date.today().isoformat())

        if len(name) > 100:
            flash('Name must be 100 characters or fewer.', 'error')
            return render_template('customer/edit_profile.html', profile_user=user, today=date.today().isoformat())

        if not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', email) or len(email) > 100:
            flash('Please enter a valid email address.', 'error')
            return render_template('customer/edit_profile.html', profile_user=user, today=date.today().isoformat())

        if not re.fullmatch(r'[0-9+\-\s]{7,15}', mobile):
            flash('Please enter a valid mobile number (7–15 digits, with optional + or spaces).', 'error')
            return render_template('customer/edit_profile.html', profile_user=user, today=date.today().isoformat())

        dob = None
        if dob_text:
            try:
                dob = date.fromisoformat(dob_text)
            except ValueError:
                flash('Please enter a valid date of birth.', 'error')
                return render_template('customer/edit_profile.html', profile_user=user, today=date.today().isoformat())

            if dob > date.today():
                flash('Date of birth cannot be in the future.', 'error')
                return render_template('customer/edit_profile.html', profile_user=user, today=date.today().isoformat())

        duplicate_email = User.query.filter(User.email == email, User.id != user.id).first()
        if duplicate_email:
            flash('That email address is already registered to another account.', 'error')
            return render_template('customer/edit_profile.html', profile_user=user, today=date.today().isoformat())

        duplicate_mobile = User.query.filter(User.mobile == mobile, User.id != user.id).first()
        if duplicate_mobile:
            flash('That mobile number is already registered to another account.', 'error')
            return render_template('customer/edit_profile.html', profile_user=user, today=date.today().isoformat())

        user.name = name
        user.email = email
        user.mobile = mobile
        user.date_of_birth = dob

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash('Those details are already in use. Please check your email and mobile number.', 'error')
            return render_template('customer/edit_profile.html', profile_user=user, today=date.today().isoformat())

        # Keep session greeting in sync with the saved name.
        session['name'] = user.name
        session.modified = True
        flash('Your profile has been updated successfully.', 'success')
        return redirect(url_for('customer.profile'))

    return render_template('customer/edit_profile.html', profile_user=user, today=date.today().isoformat())


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

    # Fetch active and available combo offers
    combo_offers = ComboOffer.query.filter_by(
        is_active=True,
        is_available=True
    ).order_by(ComboOffer.created_at.desc()).all()

    return render_template(
        'customer/menu.html',
        categories=categories,
        items=items,
        combo_offers=combo_offers
    )
    return render_template('customer/menu.html', categories=categories, items=items)
    

# Shopping Cart: regular menu items + combo offers
@customer_bp.route('/cart', methods=['GET', 'POST'])
@login_required
def cart():
    if 'cart' not in session:
        session['cart'] = {}

    if request.method == 'POST':
        item_id = request.form.get('item_id', '').strip()
        action = request.form.get('action', 'add')
        item_type = request.form.get('item_type', 'menu')
        cart_key = f'combo_{item_id}' if item_type == 'combo' else str(item_id)

        if not item_id.isdigit() or item_type not in ('menu', 'combo'):
            flash('Invalid item.', 'error')
            return redirect(url_for('customer.cart'))

        details = session['cart'].get(cart_key)

        if action in ('decrease', 'remove'):
            if details:
                if action == 'remove':
                    session['cart'].pop(cart_key, None)
                else:
                    details['quantity'] -= 1
                    if details['quantity'] <= 0:
                        session['cart'].pop(cart_key, None)
                    else:
                        session['cart'][cart_key] = details
                session.modified = True
            return redirect(url_for('customer.cart'))

        if action != 'add':
            flash('Invalid cart action.', 'error')
            return redirect(url_for('customer.cart'))

        if item_type == 'combo':
            item = db.session.get(ComboOffer, int(item_id))
            if not item or not item.is_active or not item.is_available:
                flash('This combo is currently unavailable.', 'error')
                return redirect(url_for('customer.menu'))

            name = item.name
            price = item.offer_price
            image_path = item.image_path
        else:
            item = db.session.get(MenuItem, int(item_id))
            if not item or not item.is_active or not item.is_available:
                flash('This food item is currently unavailable.', 'error')
                return redirect(url_for('customer.menu'))

            name = item.name
            price = item.discount_price if item.discount_price is not None else item.price
            image_path = item.image_path

        if details:
            details['quantity'] += 1
        else:
            details = {
                'name': name,
                'price': str(price),
                'quantity': 1,
                'image': image_path,
                'type': item_type,
                'item_id': int(item_id)
            }

        session['cart'][cart_key] = details
        session.modified = True
        flash(f'{name} added to cart!', 'success')
        return redirect(url_for('customer.cart'))

    subtotal = Decimal('0.00')
    cart_items = []

    for cart_key, details in session.get('cart', {}).items():
        details = dict(details)
        details.setdefault('type', 'menu')
        details.setdefault('item_id', int(cart_key))
        details['id'] = details['item_id']
        details['cart_key'] = cart_key
        details['total'] = str(
            Decimal(str(details['price'])) * int(details['quantity'])
        )
        subtotal += Decimal(details['total'])
        cart_items.append(details)

    tax = (subtotal * Decimal('0.05')).quantize(Decimal('0.01'))
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

    table = Table.query.filter_by(table_number=table_number, status='AVAILABLE').first()
    if not table:
        flash('Invalid or unavailable table. Please scan the QR again.', 'error')
        return redirect(url_for('customer.dashboard'))

    subtotal = Decimal('0.00')
    order_items_to_add = []
    for item_id, details in session['cart'].items():
        db_item = db.session.get(MenuItem, item_id)
        if not db_item or not db_item.is_active or not db_item.is_available:
            flash(f"Sorry, {details['name']} is no longer available.", 'error')
            return redirect(url_for('customer.cart'))

        quantity = details['quantity']
        price = db_item.price
        subtotal += price * quantity
        order_items_to_add.append(OrderItem(menu_item_id=db_item.id,
                                            quantity=quantity,
                                            price_at_time=price))

    tax = subtotal * Decimal('0.05')
    grand_total = subtotal + tax
    new_order = Order(customer_id=session['user_id'], table_id=table.id,
                      subtotal=subtotal, tax=tax, discount=Decimal('0.00'),
                      grand_total=grand_total, status='PENDING_ADMIN_REVIEW')
    db.session.add(new_order)
    db.session.flush()

    for order_item in order_items_to_add:
        order_item.order_id = new_order.id
        db.session.add(order_item)

    db.session.add(OrderStatusHistory(order_id=new_order.id, status='PENDING_ADMIN_REVIEW'))
    db.session.commit()

    session['cart'] = {}
    session.modified = True
    flash('Your order has been placed successfully and is pending review!', 'success')
    return render_template('customer/order_confirmation.html', order=new_order)


# Track Customer Orders
@customer_bp.route('/track-orders')
@login_required
def track_orders():
    active_statuses = ['PENDING_ADMIN_REVIEW', 'ACCEPTED', 'SENT_TO_CHEF',
                       'PREPARING', 'READY', 'SERVED']
    orders = Order.query.filter(Order.customer_id == session['user_id'],
                                Order.status.in_(active_statuses))\
                        .order_by(Order.created_at.desc()).all()
    return render_template('customer/track_orders.html', orders=orders)


# Customer Order History
@customer_bp.route('/order-history')
@login_required
def order_history():
    orders = Order.query.filter_by(customer_id=session['user_id'])\
                         .order_by(Order.created_at.desc()).all()
    return render_template('customer/order_history.html', orders=orders)


# Cancel Customer Order
@customer_bp.route('/cancel-order/<int:order_id>', methods=['POST'])
@login_required
def cancel_order(order_id):
    order = Order.query.filter_by(id=order_id, customer_id=session['user_id']).first_or_404()
    if order.status != 'PENDING_ADMIN_REVIEW':
        flash('This order can no longer be cancelled online. Please contact cafe staff for assistance.', 'error')
        return redirect(url_for('customer.track_orders'))
    if order.payment_status == 'PAID':
        flash('This order has already been paid. Please contact cafe staff to cancel it and arrange any applicable refund.', 'error')
        return redirect(url_for('customer.track_orders'))

    order.status = 'CANCELLED'
    db.session.add(OrderStatusHistory(order_id=order.id, status='CANCELLED'))
    db.session.commit()
    flash(f'Order #{order.id} has been cancelled successfully.', 'success')
    return redirect(url_for('customer.track_orders'))


@customer_bp.route('/ai-assistant', methods=['GET', 'POST'])
@login_required
def ai_assistant():
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        message = (data.get('message') or '').strip()
        if not message:
            return jsonify({'error': 'Message is required'}), 400

        text = message.lower()
        budget_match = re.search(r'(?:under|below|less than|within|budget of)\s*₹?\s*(\d+)', text)
        asks_menu = any(word in text for word in [
            'menu', 'show manu', 'show food', 'food items', 'pizzas',
            'coffee', 'vegetarian', 'veg food', 'recommend food', 'suggest food'
        ])

        if asks_menu or budget_match:
            query = MenuItem.query.filter_by(is_active=True, is_available=True)
            if any(word in text for word in ['vegetarian', 'vegetarian food', 'veg food', 'veg items', 'pure veg']):
                query = query.filter(MenuItem.veg_type == 'veg')
            if budget_match:
                query = query.filter(MenuItem.price <= float(budget_match.group(1)))
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
                'response': f"Here are our available items under ₹{budget_match.group(1)}." if budget_match else "Welcome to King Cafe! Here is our current menu.",
                'items': menu
            })

        ai = CafeAIAssistant()
        return jsonify({'type': 'text', 'response': ai.get_response(message)})

    return render_template('customer/ai_assistant.html')
