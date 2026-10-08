from flask import Blueprint, render_template, redirect, url_for, flash
from app.utils.decorators import chef_required
from app.models.models import Order, OrderStatusHistory
from app import db

chef_bp = Blueprint('chef', __name__)

@chef_bp.route('/dashboard')
@chef_required
def dashboard():
    # Fetch orders that are ACCEPTED (New) or PREPARING
    orders = Order.query.filter(Order.status.in_(['ACCEPTED', 'PREPARING'])).order_by(
        # Prioritize PREPARING first, then ACCEPTED, then by time
        db.case(
            (Order.status == 'PREPARING', 1),
            (Order.status == 'ACCEPTED', 2),
            else_=3
        ),
        Order.created_at.asc()
    ).all()
    
    return render_template('chef/dashboard.html', orders=orders)

@chef_bp.route('/order/<int:order_id>/<action>', methods=['POST'])
@chef_required
def process_order(order_id, action):
    order = Order.query.get_or_404(order_id)
    
    if action == 'start' and order.status == 'ACCEPTED':
        order.status = 'PREPARING'
        flash(f'Started preparing Order #{order.id}', 'success')
    elif action == 'ready' and order.status == 'PREPARING':
        order.status = 'READY'
        # Notify Admin
        from app.models.models import Notification
        db.session.add(Notification(role_target='admin', message=f'Order #{order.id} on Table {order.table.table_number} is READY to serve!'))
        flash(f'Order #{order.id} is ready for service!', 'success')
        
    history = OrderStatusHistory(order_id=order.id, status=order.status)
    db.session.add(history)
    db.session.commit()
    
    return redirect(url_for('chef.dashboard'))
