import os
import uuid

from flask import (
    Blueprint, render_template, request, redirect, url_for, flash,
    current_app, send_from_directory, abort
)
from werkzeug.utils import secure_filename

from app.models.models import MenuItem, Category
from app import db
from app.utils.decorators import admin_required

menu_bp = Blueprint('menu', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}


def allowed_file(filename):
    return bool(filename) and '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def food_image_directory():
    # Railway volume is mounted at /app/persistent_uploads.
    return os.path.abspath(os.environ.get(
        'FOOD_IMAGE_UPLOAD_DIR',
        '/app/persistent_uploads/food_images'
    ))


def legacy_food_image_directory():
    # Fallback for images that still exist in the old static folder.
    return os.path.join(current_app.root_path, 'static', 'uploads', 'food_images')


def save_food_image(file):
    if not file or not file.filename or not allowed_file(file.filename):
        return None

    safe_original = secure_filename(file.filename)
    extension = safe_original.rsplit('.', 1)[1].lower()
    filename = f'{uuid.uuid4().hex}.{extension}'

    upload_dir = food_image_directory()
    os.makedirs(upload_dir, exist_ok=True)
    file.save(os.path.join(upload_dir, filename))

    # Keep the same relative path format in MySQL.
    return f'uploads/food_images/{filename}'


@menu_bp.route('/food-image/<path:filename>')
def uploaded_food_image(filename):
    # Serve a single safe filename, never a user-supplied directory path.
    safe_name = secure_filename(os.path.basename(filename))
    if not safe_name or safe_name != filename:
        abort(404)

    persistent_dir = food_image_directory()
    if os.path.isfile(os.path.join(persistent_dir, safe_name)):
        return send_from_directory(persistent_dir, safe_name)

    legacy_dir = legacy_food_image_directory()
    if os.path.isfile(os.path.join(legacy_dir, safe_name)):
        return send_from_directory(legacy_dir, safe_name)

    abort(404)


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

    image_path = None
    if 'image' in request.files:
        file = request.files['image']
        if file and file.filename:
            if not allowed_file(file.filename):
                flash('Please upload a PNG, JPG, JPEG, or WEBP image.', 'error')
                return redirect(url_for('menu.manage_menu'))
            image_path = save_food_image(file)

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


@menu_bp.route('/edit/<int:item_id>', methods=['GET', 'POST'])
@admin_required
def edit_food(item_id):
    item = MenuItem.query.get_or_404(item_id)
    categories = Category.query.all()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        category_id = request.form.get('category_id')
        price = request.form.get('price')
        description = request.form.get('description', '').strip()
        preparation_time = request.form.get('preparation_time')
        veg_type = request.form.get('veg_type')

        if not name or not price:
            flash('Food name and price are required.', 'error')
            return render_template('admin/edit_food.html', item=item, categories=categories)

        item.name = name
        item.category_id = int(category_id) if category_id else None
        item.price = price
        item.description = description
        item.preparation_time = int(preparation_time) if preparation_time else None
        item.veg_type = veg_type if veg_type in ('veg', 'non-veg') else 'veg'
        item.is_available = 'is_available' in request.form

        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                if not allowed_file(file.filename):
                    flash('Please upload a PNG, JPG, JPEG, or WEBP image.', 'error')
                    return render_template('admin/edit_food.html', item=item, categories=categories)

                new_image_path = save_food_image(file)
                if new_image_path:
                    # Keep the previous file as a recovery copy.
                    item.image_path = new_image_path

        db.session.commit()
        flash(f'{item.name} updated successfully!', 'success')
        return redirect(url_for('menu.manage_menu'))

    return render_template('admin/edit_food.html', item=item, categories=categories)


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
    item.is_active = False
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

    # Preserve order history; only remove the category link from its items.
    for item in category.menu_items:
        item.category_id = None

    db.session.delete(category)
    db.session.commit()
    flash(f'Category "{cat_name}" was deleted successfully.', 'success')
    return redirect(url_for('menu.manage_categories'))
