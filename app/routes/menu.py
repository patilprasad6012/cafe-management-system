import os
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from app.models.models import MenuItem, Category
from app import db
from app.utils.decorators import admin_required

menu_bp = Blueprint('menu', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@menu_bp.route('/')
@admin_required
def manage_menu():
    items = MenuItem.query.all()
    categories = Category.query.all()
    return render_template('admin/menu.html', items=items, categories=categories)

@menu_bp.route('/add', methods=['POST'])
@admin_required
def add_food():
    name = request.form.get('name')
    category_id = request.form.get('category_id')
    price = request.form.get('price')
    description = request.form.get('description')
    preparation_time = request.form.get('preparation_time')
    veg_type = request.form.get('veg_type')
    is_available = 'is_available' in request.form
    
    # Handle Image Upload
    image_path = None
    if 'image' in request.files:
        file = request.files['image']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'food_images')
            os.makedirs(upload_dir, exist_ok=True)
            filepath = os.path.join(upload_dir, filename)
            file.save(filepath)
            image_path = f"uploads/food_images/{filename}"

    new_item = MenuItem(
        name=name,
        category_id=category_id,
        price=price,
        description=description,
        preparation_time=preparation_time,
        veg_type=veg_type,
        is_available=is_available,
        image_path=image_path
    )
    
    db.session.add(new_item)
    db.session.commit()
    flash(f'Food item {name} added successfully!', 'success')
    return redirect(url_for('menu.manage_menu'))

@menu_bp.route('/toggle/<int:item_id>')
@admin_required
def toggle_availability(item_id):
    item = MenuItem.query.get_or_404(item_id)
    item.is_available = not item.is_available
    db.session.commit()
    status = "Available" if item.is_available else "Unavailable"
    flash(f'{item.name} is now {status}', 'info')
    return redirect(url_for('menu.manage_menu'))

@menu_bp.route('/archive/<int:item_id>')
@admin_required
def archive_food(item_id):
    item = MenuItem.query.get_or_404(item_id)
    item.is_active = False # Soft delete
    db.session.commit()
    flash(f'{item.name} has been archived.', 'warning')
    return redirect(url_for('menu.manage_menu'))

@menu_bp.route('/restore/<int:item_id>')
@admin_required
def restore_food(item_id):
    item = MenuItem.query.get_or_404(item_id)
    item.is_active = True
    db.session.commit()
    flash(f'{item.name} has been restored.', 'success')
    return redirect(url_for('menu.manage_menu'))

@menu_bp.route('/categories', methods=['GET', 'POST'])
@admin_required
def manage_categories():
    if request.method == 'POST':
        name = request.form.get('name')
        if Category.query.filter_by(name=name).first():
            flash('Category already exists!', 'error')
        else:
            new_cat = Category(name=name)
            db.session.add(new_cat)
            db.session.commit()
            flash(f'Category {name} added!', 'success')
            
    categories = Category.query.all()
    return render_template('admin/categories.html', categories=categories)

@menu_bp.route('/categories/delete/<int:category_id>', methods=['POST'])
@admin_required
def delete_category(category_id):
    category = Category.query.get_or_404(category_id)
    cat_name = category.name

    # Keep menu items and their order history; only remove their category link.
    for item in category.menu_items:
        item.category_id = None

    db.session.delete(category)
    db.session.commit()
    flash(f'Category "{cat_name}" was deleted successfully.', 'success')
    return redirect(url_for('menu.manage_categories'))
