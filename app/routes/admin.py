from flask import Blueprint, render_template
from app.utils.decorators import admin_required

admin_bp = Blueprint('admin', __name__)

from sqlalchemy import func
from datetime import datetime, date
from app.models.models import Order, User, OrderStatusHistory, Notification

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    today = date.today()
    
    # Today's Orders (Count)
    today_orders = Order.query.filter(func.date(Order.created_at) == today).count()
    
    # Today's Sales (Sum of grand_total where payment is PAID)
    today_sales_query = db.session.query(func.sum(Order.grand_total)).filter(
        func.date(Order.created_at) == today,
        Order.payment_status == 'PAID'
    ).scalar()
    today_sales = float(today_sales_query) if today_sales_query else 0.0
    
    # Pending Orders
    pending_orders = Order.query.filter_by(status='PENDING_ADMIN_REVIEW').count()
    
    # Active Customers (Total customers registered)
    active_customers = User.query.filter_by(role='customer').count()
    
    stats = {
        'today_orders': today_orders,
        'today_sales': today_sales,
        'pending_orders': pending_orders,
        'active_customers': active_customers
    }
    
    # Recent 5 orders for the dashboard table
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html', stats=stats, recent_orders=recent_orders)
from app.models.models import Order, OrderStatusHistory, Notification
from app import db
from flask import request, redirect, url_for, flash, render_template

@admin_bp.route('/orders')
@admin_required
def manage_orders():
    # Fetch all pending orders for review
    pending_orders = Order.query.filter_by(status='PENDING_ADMIN_REVIEW').order_by(Order.created_at.desc()).all()
    # Fetch orders currently with chef or ready
    active_orders = Order.query.filter(Order.status.in_(['ACCEPTED', 'PREPARING', 'READY'])).order_by(Order.created_at.desc()).all()
    
    return render_template('admin/orders.html', pending_orders=pending_orders, active_orders=active_orders)

@admin_bp.route('/orders/<int:order_id>/<action>', methods=['POST'])
@admin_required
def process_order(order_id, action):
    order = Order.query.get_or_404(order_id)
    
    if action == 'accept':
        order.status = 'ACCEPTED'
        # Notify Customer
        db.session.add(Notification(user_id=order.customer_id, role_target='customer', message=f'Your Order #{order.id} has been accepted!'))
        flash(f'Order #{order.id} accepted and sent to kitchen.', 'success')
    elif action == 'reject':
        order.status = 'REJECTED'
        reason = request.form.get('reason', 'No reason provided')
        order.notes = f"Rejected: {reason}"
        # Notify Customer
        db.session.add(Notification(user_id=order.customer_id, role_target='customer', message=f'Your Order #{order.id} was rejected. Reason: {reason}'))
        flash(f'Order #{order.id} rejected.', 'warning')
    
    history = OrderStatusHistory(order_id=order.id, status=order.status)
    db.session.add(history)
    db.session.commit()
    
    return redirect(url_for('admin.manage_orders'))

@admin_bp.route('/bill/<int:order_id>')
@admin_required
def generate_bill(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template('admin/bill.html', order=order)

@admin_bp.route('/payment/<int:order_id>', methods=['POST'])
@admin_required
def update_payment(order_id):
    order = Order.query.get_or_404(order_id)
    payment_status = request.form.get('payment_status')
    
    if payment_status in ['PAID', 'PENDING', 'FAILED', 'REFUNDED']:
        order.payment_status = payment_status
        db.session.add(Notification(user_id=order.customer_id, role_target='customer', message=f'Payment for Order #{order.id} is now {payment_status}.'))
        
        # If paid and order is ready/served, we can mark order completed
        if payment_status == 'PAID' and order.status in ['READY', 'SERVED']:
            order.status = 'COMPLETED'
            db.session.add(OrderStatusHistory(order_id=order.id, status='COMPLETED'))
            
        db.session.commit()
        flash(f'Payment status updated to {payment_status} for Order #{order.id}', 'success')
    
    return redirect(url_for('admin.generate_bill', order_id=order.id))
    
@admin_bp.route('/order-history')
@admin_required
def order_history():
    orders = Order.query.order_by(
        Order.created_at.desc()
    ).all()

    return render_template(
        'admin/order_history.html',
        orders=orders
    )
