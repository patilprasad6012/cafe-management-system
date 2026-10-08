import os
import qrcode
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from app.models.models import Table
from app import db
from app.utils.decorators import admin_required

table_bp = Blueprint('table', __name__)

@table_bp.route('/')
@admin_required
def manage_tables():
    tables = Table.query.all()
    return render_template('admin/tables.html', tables=tables)

@table_bp.route('/add', methods=['POST'])
@admin_required
def add_table():
    table_number = request.form.get('table_number')
    
    if Table.query.filter_by(table_number=table_number).first():
        flash('Table number already exists!', 'error')
        return redirect(url_for('table.manage_tables'))
        
    new_table = Table(table_number=table_number)
    db.session.add(new_table)
    db.session.commit()
    
    # Generate QR Code
    generate_qr(new_table)
    
    flash('Table added successfully!', 'success')
    return redirect(url_for('table.manage_tables'))

@table_bp.route('/toggle/<int:table_id>')
@admin_required
def toggle_status(table_id):
    table = Table.query.get_or_404(table_id)
    if table.status == 'AVAILABLE':
        table.status = 'DISABLED'
    else:
        table.status = 'AVAILABLE'
        
    db.session.commit()
    flash(f'Table {table.table_number} status updated to {table.status}', 'info')
    return redirect(url_for('table.manage_tables'))

def generate_qr(table):
    # Ensure directory exists
    qr_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'qrcodes')
    os.makedirs(qr_dir, exist_ok=True)
    
    # Generate URL (in production this would be the real domain)
    # Scanning this should take the user to the menu page with this table ID
    url = f"https://web-production-9dd7e.up.railway.app/customer/menu?table={table.table_number}"
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    filename = f"qr_table_{table.table_number}.png"
    filepath = os.path.join(qr_dir, filename)
    img.save(filepath)
    
    # Update table with QR path
    table.qr_code_url = f"uploads/qrcodes/{filename}"
    db.session.commit()

@table_bp.route('/regenerate_qr/<int:table_id>')
@admin_required
def regenerate_qr(table_id):
    table = Table.query.get_or_404(table_id)
    generate_qr(table)
    flash(f'QR Code regenerated for Table {table.table_number}', 'success')
    return redirect(url_for('table.manage_tables'))
