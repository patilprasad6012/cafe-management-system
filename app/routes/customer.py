from flask import Blueprint, render_template, session, request, redirect, url_for, flash, jsonify
from app.models.models import MenuItem, Category, Order, OrderItem, OrderStatusHistory, Table
from app import db
from app.utils.decorators import login_required
from decimal import Decimal

customer_bp = Blueprint('customer', __name__)

@customer_bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('customer/dashboard.html')

@customer_bp.route('/menu')
def menu():
    # If the user scans a QR code, the table ID might be in the query params
    table_number = request.args.get('table')
    if table_number:
        session['table_number'] = table_number
        
    categories = Category.query.filter_by(is_active=True).all()
    # Only show items that are active and available
    items = MenuItem.query.filter_by(is_active=True, is_available=True).all()
    
    return render_template('customer/menu.html', categories=categories, items=items)

@customer_bp.route('/cart', methods=['GET', 'POST'])
@login_required
def cart():
    # Initialize cart in session if not exists
    if 'cart' not in session:
        session['cart'] = {}
        
    if request.method == 'POST':
        item_id = request.form.get('item_id')
        action = request.form.get('action') # 'add', 'remove', 'decrease'
        
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

    # Calculate totals
    subtotal = Decimal('0.00')
    cart_items = []
    
    for item_id, details in session.get('cart', {}).items():
        item_total = Decimal(details['price']) * details['quantity']
        subtotal += item_total
        details['id'] = item_id
        details['total'] = str(item_total)
        cart_items.append(details)
        
    tax = subtotal * Decimal('0.05') # 5% placeholder tax
    grand_total = subtotal + tax
    
    return render_template('customer/cart.html', 
                           cart_items=cart_items, 
                           subtotal=subtotal, 
                           tax=tax, 
                           grand_total=grand_total)

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
    
    # Recalculate everything from the DB to prevent frontend price manipulation
    for item_id, details in session['cart'].items():
        db_item = MenuItem.query.get(item_id)
        if not db_item or not db_item.is_active or not db_item.is_available:
            flash(f"Sorry, {details['name']} is no longer available.", 'error')
            return redirect(url_for('customer.cart'))
            
        quantity = details['quantity']
        price = db_item.price
        item_total = price * quantity
        subtotal += item_total
        
        order_items_to_add.append(OrderItem(
            menu_item_id=db_item.id,
            quantity=quantity,
            price_at_time=price
        ))
        
    tax = subtotal * Decimal('0.05')
    grand_total = subtotal + tax
    
    # Create Order
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
    db.session.flush() # Get order ID before committing
    
    # Attach items to order
    for oi in order_items_to_add:
        oi.order_id = new_order.id
        db.session.add(oi)
        
    # Log status history
    history = OrderStatusHistory(
        order_id=new_order.id,
        status='PENDING_ADMIN_REVIEW'
    )
    db.session.add(history)
    
    # Clear cart
    session['cart'] = {}
    session.modified = True
    
    db.session.commit()
    flash('Your order has been placed successfully and is pending review!', 'success')
    return render_template('customer/order_confirmation.html', order=new_order)

from app.services.ai_assistant import CafeAIAssistant

@customer_bp.route('/ai-assistant', methods=['GET', 'POST'])
@login_required
def ai_assistant():
    if request.method == 'POST':
        user_message = request.json.get('message')
        if not user_message:
            return jsonify({'error': 'Message is required'}), 400
            
        ai = CafeAIAssistant()
        response = ai.get_response(user_message)
        
        return jsonify({'response': response})
        
    return render_template('customer/ai_assistant.html')
