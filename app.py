from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from config import Config
from models import db, User, Product, Category, Supplier, Sale, SaleItem, PurchaseOrder, StockMovement, SupplierProduct, Notification
from datetime import datetime, date, timedelta
import cloudinary
import cloudinary.uploader
import cloudinary.api

#initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize Cloudinary
cloudinary.config(
    cloud_name=app.config['CLOUDINARY_CLOUD_NAME'],
    api_key=app.config['CLOUDINARY_API_KEY'],
    api_secret=app.config['CLOUDINARY_API_SECRET']
)

#initalize db
db.init_app(app)

#initiliza Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  
login_manager.login_message = 'Please log in to access this page.'

@login_manager.user_loader
def load_user(user_id):
   
    
    
    return User.query.get(int(user_id))


@app.route('/home')
def home():
    """Landing page - shows the marketing website"""
    return render_template('index.html')

@app.route('/')
def index():
    """Main entry point - redirect based on user role"""
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif current_user.role == 'cashier':
            return redirect(url_for('cashier_dashboard'))
        elif current_user.role == 'manager':
            return redirect(url_for('manager_dashboard'))
        elif current_user.role == 'supplier':
            return redirect(url_for('supplier_dashboard'))
    
   
    return redirect(url_for('home'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
      
        user = User.query.filter_by(username=username).first()
        
        
        if user and user.check_password(password):
            if user.is_active:
                login_user(user)
                # flash(f'Welcome back, {user.username}!', 'success')
                
                
                return redirect(url_for('index'))
            else:
                flash('Your account has been deactivated. Contact admin.', 'danger')
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('reglog.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User Registration Page"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        role = request.form.get('role')  
        
        
        if password != confirm_password:
            flash('Passwords do not match.', 'warning')
            return redirect(url_for('register'))
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return redirect(url_for('register'))
        
        # Create new user
        new_user = User(username=username, email=email, role=role, is_active=True)
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.flush()  
        
       
        if role == 'supplier':
            supplier = Supplier(
                name=f"{username}'s Company",
                contact_person=username,
                email=email,
                phone=None,
                address=None,
                user_id=new_user.id,  
                is_active=True
            )
            db.session.add(supplier)
            flash('Supplier account created successfully! You can now log in.', 'success')
        else:
            flash('Account created successfully! You can now log in.', 'success')
        
        db.session.commit()  
        
        return redirect(url_for('login'))
    
    return render_template('reglog.html')


@app.route('/logout')
@login_required
def logout():
    """Logout current user"""
    logout_user()
    # flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login'))


# ====================
# ADMIN ROUTES
# ====================

from functools import wraps
from flask import jsonify

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Access denied. Admin only.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    """Admin dashboard - user and system management"""
    
    total_users = User.query.count()
    admin_users_count = User.query.filter_by(role='admin').count()
    active_suppliers_count = Supplier.query.filter_by(is_active=True).count()
    inactive_users_count = User.query.filter_by(is_active=False).count()
    
    
    user_roles = {
        'admins': User.query.filter_by(role='admin').count(),
        'managers': User.query.filter_by(role='manager').count(),
        'cashiers': User.query.filter_by(role='cashier').count(),
        'suppliers': User.query.filter_by(role='supplier').count()
    }
    
    
    users = User.query.all()
    suppliers = Supplier.query.all()
    
    return render_template('admin/admin.html',
                         total_users=total_users,
                         admin_users_count=admin_users_count,
                         active_suppliers_count=active_suppliers_count,
                         inactive_users_count=inactive_users_count,
                         user_roles=user_roles,
                         users=users,
                         suppliers=suppliers)

# USER MANAGEMENT ROUTES
@app.route('/admin/users')
@login_required
@admin_required
def manage_users():
    """Manage users - admin only"""
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@app.route('/admin/users/add', methods=['POST'])
@login_required
@admin_required
def add_user():
    """Add new user - admin only"""
    try:
        username = request.form.get('username')
        email = request.form.get('email')
        role = request.form.get('role')
        password = request.form.get('password')
        
        
        if not all([username, email, role, password]):
            return jsonify({'success': False, 'message': 'All fields are required'})
        
        if User.query.filter_by(username=username).first():
            return jsonify({'success': False, 'message': 'Username already exists'})
        
        if User.query.filter_by(email=email).first():
            return jsonify({'success': False, 'message': 'Email already registered'})
        
        
        new_user = User(
            username=username,
            email=email,
            role=role,
            is_active=True
        )
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'User created successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Delete user - admin only"""
    try:
        user = User.query.get_or_404(user_id)
        
        
        if user.id == current_user.id:
            return jsonify({'success': False, 'message': 'Cannot delete your own account'})
        
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'User deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/admin/users/toggle/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def toggle_user(user_id):
    """Toggle user active status - admin only"""
    try:
        user = User.query.get_or_404(user_id)
        
        
        if user.id == current_user.id:
            return jsonify({'success': False, 'message': 'Cannot deactivate your own account'})
        
        user.is_active = not user.is_active
        db.session.commit()
        
        status = "activated" if user.is_active else "deactivated"
        return jsonify({'success': True, 'message': f'User {status} successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/admin/users/edit/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def edit_user(user_id):
    """Edit user - admin only"""
    try:
        user = User.query.get_or_404(user_id)
        username = request.form.get('username')
        email = request.form.get('email')
        role = request.form.get('role')
        
        
        existing_user = User.query.filter_by(username=username).first()
        if existing_user and existing_user.id != user_id:
            return jsonify({'success': False, 'message': 'Username already taken'})
        
       
        existing_email = User.query.filter_by(email=email).first()
        if existing_email and existing_email.id != user_id:
            return jsonify({'success': False, 'message': 'Email already registered'})
        
        user.username = username
        user.email = email
        user.role = role
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'User updated successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

# SUPPLIER MANAGEMENT ROUTES
@app.route('/admin/suppliers')
@login_required
@admin_required
def manage_suppliers():
    """Manage suppliers - admin only"""
    suppliers = Supplier.query.all()
    return render_template('admin/sup.html', suppliers=suppliers)

@app.route('/admin/suppliers/add', methods=['POST'])
@login_required
@admin_required
def add_supplier():
    """Add new supplier - admin only"""
    try:
        name = request.form.get('name')
        contact_person = request.form.get('contact_person')
        email = request.form.get('email')
        phone = request.form.get('phone')
        address = request.form.get('address')
        
       
        if not all([name, email]):
            return jsonify({'success': False, 'message': 'Name and email are required'})
        
        if Supplier.query.filter_by(email=email).first():
            return jsonify({'success': False, 'message': 'Supplier with this email already exists'})
        
        
        supplier = Supplier(
            name=name,
            contact_person=contact_person,
            email=email,
            phone=phone,
            address=address,
            is_active=True
        )
        
        db.session.add(supplier)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Supplier added successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/admin/suppliers/delete/<int:supplier_id>', methods=['POST'])
@login_required
@admin_required
def delete_supplier(supplier_id):
    """Delete supplier and all associated products - admin only"""
    try:
        supplier = Supplier.query.get_or_404(supplier_id)
        
        
        product_count = len(supplier.products)
        
        
        for product in supplier.products:
            
            sale_items = SaleItem.query.filter_by(product_id=product.id).all()
            for sale_item in sale_items:
                db.session.delete(sale_item)
            
           
            stock_movements = StockMovement.query.filter_by(product_id=product.id).all()
            for movement in stock_movements:
                db.session.delete(movement)
            
           
            db.session.delete(product)
        
        
        db.session.delete(supplier)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Supplier and {product_count} associated products deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/admin/suppliers/toggle/<int:supplier_id>', methods=['POST'])
@login_required
@admin_required
def toggle_supplier(supplier_id):
    """Toggle supplier active status - admin only"""
    try:
        supplier = Supplier.query.get_or_404(supplier_id)
        supplier.is_active = not supplier.is_active
        
        db.session.commit()
        
        status = "activated" if supplier.is_active else "deactivated"
        return jsonify({'success': True, 'message': f'Supplier {status} successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/admin/suppliers/edit/<int:supplier_id>', methods=['POST'])
@login_required
@admin_required
def edit_supplier(supplier_id):
    """Edit supplier - admin only"""
    try:
        supplier = Supplier.query.get_or_404(supplier_id)
        name = request.form.get('name')
        contact_person = request.form.get('contact_person')
        email = request.form.get('email')
        phone = request.form.get('phone')
        address = request.form.get('address')
        
        
        existing_supplier = Supplier.query.filter_by(email=email).first()
        if existing_supplier and existing_supplier.id != supplier_id:
            return jsonify({'success': False, 'message': 'Email already registered to another supplier'})
        
        supplier.name = name
        supplier.contact_person = contact_person
        supplier.email = email
        supplier.phone = phone
        supplier.address = address
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Supplier updated successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})


@app.route('/admin/suppliers/get/<int:supplier_id>')
@login_required
@admin_required
def get_supplier(supplier_id):
    """Get supplier data for editing - admin only"""
    try:
        supplier = Supplier.query.get_or_404(supplier_id)
        
        supplier_data = {
            'id': supplier.id,
            'name': supplier.name,
            'contact_person': supplier.contact_person,
            'email': supplier.email,
            'phone': supplier.phone,
            'address': supplier.address,
            'is_active': supplier.is_active,
            'products_count': len(supplier.products)  # Add this line
        }
        
        return jsonify({'success': True, 'supplier': supplier_data})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/admin/suppliers/update', methods=['POST'])
@login_required
@admin_required
def update_supplier_route():
    """Update supplier - admin only"""
    try:
        supplier_id = request.form.get('supplier_id')
        name = request.form.get('name')
        contact_person = request.form.get('contact_person')
        email = request.form.get('email')
        phone = request.form.get('phone')
        address = request.form.get('address')
        is_active = request.form.get('is_active') == 'on'
        
        supplier = Supplier.query.get_or_404(supplier_id)
        
        
        existing_supplier = Supplier.query.filter_by(email=email).first()
        if existing_supplier and existing_supplier.id != supplier.id:
            return jsonify({'success': False, 'message': 'Email already registered to another supplier'})
        
        # Update supplier
        supplier.name = name
        supplier.contact_person = contact_person
        supplier.email = email
        supplier.phone = phone
        supplier.address = address
        supplier.is_active = is_active
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Supplier updated successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})
    
    
# Admin reports routes
@app.route('/admin/reports')
@login_required
@admin_required
def admin_reports():
    """Dedicated reports page"""
    
    today_sales = Sale.query.filter(db.func.date(Sale.sale_date) == date.today()).all()
    total_revenue = sum(sale.total_amount for sale in today_sales)
    
   
    low_stock_products = Product.query.filter(Product.quantity <= Product.reorder_level).all()
    
    
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    top_products = db.session.query(
        Product.name,
        db.func.sum(SaleItem.quantity).label('total_sold')
    ).join(SaleItem).join(Sale).filter(
        Sale.sale_date >= thirty_days_ago
    ).group_by(Product.id).order_by(db.desc('total_sold')).limit(10).all()
    
    return render_template('admin/reports.html',
                         total_revenue=total_revenue,
                         low_stock_count=len(low_stock_products),
                         top_products=top_products,
                         sales_count=len(today_sales))


@app.route('/admin/reports/data')
@login_required
@admin_required
def get_reports_data():
    """Get reports data for the modal"""
    try:
        from datetime import datetime, timedelta, date
        
        # Today's sales
        today_sales = Sale.query.filter(db.func.date(Sale.sale_date) == date.today()).all()
        today_revenue = sum(sale.total_amount for sale in today_sales)
        
        
        sales_trend = []
        labels = []
        for i in range(6, -1, -1):
            day = date.today() - timedelta(days=i)
            day_sales = Sale.query.filter(db.func.date(Sale.sale_date) == day).all()
            day_revenue = sum(sale.total_amount for sale in day_sales)
            sales_trend.append(float(day_revenue))
            labels.append(day.strftime('%a'))
        
        
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        top_products = db.session.query(
            Product.name,
            db.func.sum(SaleItem.quantity).label('quantity_sold')
        ).join(SaleItem).join(Sale).filter(
            Sale.sale_date >= thirty_days_ago
        ).group_by(Product.id).order_by(db.desc('quantity_sold')).limit(5).all()
        
       
        low_stock_items = Product.query.filter(Product.quantity <= Product.reorder_level).all()
        
        
        products = Product.query.all()
        total_inventory_value = sum(product.cost_price * product.quantity for product in products)
        
        
        active_users = User.query.filter_by(is_active=True).count()
        
        
        gross_revenue = Sale.query.with_entities(db.func.sum(Sale.total_amount)).scalar() or 0
        net_profit = gross_revenue * 0.7  
        profit_margin = 70  
        
        return jsonify({
            'success': True,
            'data': {
                'today_revenue': today_revenue,
                'today_sales': len(today_sales),
                'low_stock_count': len(low_stock_items),
                'active_users': active_users,
                'sales_trend': {
                    'labels': labels,
                    'data': sales_trend
                },
                'top_products': [{
                    'name': product.name,
                    'quantity_sold': product.quantity_sold or 0
                } for product in top_products],
                'low_stock_items': [{
                    'name': product.name,
                    'quantity': product.quantity,
                    'reorder_level': product.reorder_level
                } for product in low_stock_items],
                'total_inventory_value': total_inventory_value,
                'gross_revenue': gross_revenue,
                'net_profit': net_profit,
                'profit_margin': profit_margin
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})


@app.route('/admin/settings')
@login_required
@admin_required
def admin_settings():
    """Admin settings - admin only"""
    return render_template('admin/settings.html')

@app.route('/admin/settings/update', methods=['POST'])
@login_required
@admin_required
def update_settings():
    """Update system settings - admin only"""
    try:
       
        allow_registration = request.form.get('allow_registration') == 'true'
        allow_admin_creation = request.form.get('allow_admin_creation') == 'true'
        
        
        return jsonify({'success': True, 'message': 'Settings updated successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/admin/audit-logs')
@login_required
@admin_required
def audit_logs():
    """Audit logs - admin only"""
    
    return render_template('admin/audit.html')

@app.route('/admin/backup')
@login_required
@admin_required
def backup_system():
    """Backup system - admin only"""
    return render_template('admin/backup.html')

@app.route('/admin/backup/create', methods=['POST'])
@login_required
@admin_required
def create_backup():
    """Create system backup - admin only"""
    try:
        
        backup_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        return jsonify({
            'success': True, 
            'message': f'Backup created successfully at {backup_time}'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})
    

# ====================
# CASHIER ROUTES
# ====================

@app.route('/cashier/dashboard')
@login_required
def cashier_dashboard():
    """Cashier dashboard with POS"""
    if current_user.role != 'cashier':
        flash('Access denied. Cashier only.', 'danger')
        return redirect(url_for('index'))
    
    
    today_sales = Sale.query.filter(
        Sale.cashier_id == current_user.id,
        db.func.date(Sale.sale_date) == date.today()
    ).all()
    
    total_today = sum(sale.total_amount for sale in today_sales)
    sales_count = len(today_sales)
    
    return render_template('cashier/cashier.html',
                         sales_count=sales_count,
                         total_today=total_today,
                         current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

@app.route('/cashier/search-products')
@login_required
def search_products():
    """Search products for POS"""
    if current_user.role != 'cashier':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify({'products': []})
    
    
    products = Product.query.filter(
        db.or_(
            Product.name.ilike(f'%{query}%'),
            Product.sku.ilike(f'%{query}%'),
            Product.description.ilike(f'%{query}%')
        ),
        Product.is_active == True
    ).limit(10).all()
    
    products_data = []
    for product in products:
        products_data.append({
            'id': product.id,
            'name': product.name,
            'sku': product.sku,
            'selling_price': float(product.selling_price),
            'quantity': product.quantity
        })
    
    return jsonify({'products': products_data})

@app.route('/cashier/process-sale', methods=['POST'])
@login_required
def process_sale():
    """Process a new sale"""
    if current_user.role != 'cashier':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        data = request.get_json()
        items = data.get('items', [])
        customer_name = data.get('customer_name')
        customer_phone = data.get('customer_phone')
        payment_method = data.get('payment_method', 'cash')
        
        if not items:
            return jsonify({'success': False, 'message': 'No items in cart'})
        
       
        total_amount = sum(item['price'] * item['quantity'] for item in items)
        
        
        sale_number = f"SALE-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        
        # Create sale
        sale = Sale(
            sale_number=sale_number,
            total_amount=total_amount,
            payment_method=payment_method,
            cashier_id=current_user.id,
            customer_name=customer_name,
            customer_phone=customer_phone
        )
        
        db.session.add(sale)
        db.session.flush()  
        
        
        for item_data in items:
            product = Product.query.get(item_data['id'])
            if not product:
                continue
            
            # Create sale item
            sale_item = SaleItem(
                sale_id=sale.id,
                product_id=product.id,
                quantity=item_data['quantity'],
                unit_price=item_data['price'],
                subtotal=item_data['price'] * item_data['quantity']
            )
            db.session.add(sale_item)
            
            # Update product stock
            if product.quantity >= item_data['quantity']:
                product.quantity -= item_data['quantity']
                
                # Record stock movement
                movement = StockMovement(
                    product_id=product.id,
                    movement_type='out',
                    quantity=item_data['quantity'],
                    reason='sale',
                    user_id=current_user.id,
                    reference_id=sale.id,
                    reference_type='sale'
                )
                db.session.add(movement)
            else:
                db.session.rollback()
                return jsonify({'success': False, 'message': f'Insufficient stock for {product.name}'})
        
        db.session.commit()
        
       
        sale_data = {
            'id': sale.id,
            'sale_number': sale.sale_number,
            'total_amount': float(sale.total_amount),
            'payment_method': sale.payment_method,
            'sale_date': sale.sale_date.isoformat(),
            'customer_name': sale.customer_name,
            'items': [{
                'product_name': item_data['name'],
                'quantity': item_data['quantity'],
                'unit_price': float(item_data['price'])
            } for item_data in items]
        }
        
        return jsonify({'success': True, 'sale': sale_data})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error processing sale: {str(e)}'})

@app.route('/cashier/sales-history')
@login_required
def sales_history():
    """Get sales history for cashier"""
    if current_user.role != 'cashier':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    filter_date = request.args.get('date')
    query = Sale.query.filter_by(cashier_id=current_user.id)
    
    if filter_date:
        try:
            filter_date = datetime.strptime(filter_date, '%Y-%m-%d').date()
            query = query.filter(db.func.date(Sale.sale_date) == filter_date)
        except ValueError:
            pass
    
    sales = query.order_by(Sale.sale_date.desc()).limit(50).all()
    
    sales_data = []
    for sale in sales:
        items_count = len(sale.items)
        sales_data.append({
            'id': sale.id,
            'sale_number': sale.sale_number,
            'sale_date': sale.sale_date.isoformat(),
            'customer_name': sale.customer_name,
            'items_count': items_count,
            'payment_method': sale.payment_method,
            'total_amount': float(sale.total_amount)
        })
    
    return jsonify({'sales': sales_data})

@app.route('/cashier/sale-receipt/<int:sale_id>')
@login_required
def sale_receipt(sale_id):
    """Get sale receipt data"""
    if current_user.role != 'cashier':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    sale = Sale.query.filter_by(id=sale_id, cashier_id=current_user.id).first()
    if not sale:
        return jsonify({'success': False, 'message': 'Sale not found'})
    
    sale_data = {
        'id': sale.id,
        'sale_number': sale.sale_number,
        'total_amount': float(sale.total_amount),
        'payment_method': sale.payment_method,
        'sale_date': sale.sale_date.isoformat(),
        'customer_name': sale.customer_name,
        'items': [{
            'product_name': item.product.name,
            'quantity': item.quantity,
            'unit_price': float(item.unit_price)
        } for item in sale.items]
    }
    
    return jsonify({'success': True, 'sale': sale_data})

@app.route('/cashier/products')
@login_required
def cashier_products():
    """Get all products for catalog"""
    if current_user.role != 'cashier':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    products = Product.query.filter_by(is_active=True).all()
    
    products_data = []
    for product in products:
        products_data.append({
            'id': product.id,
            'name': product.name,
            'sku': product.sku,
            'selling_price': float(product.selling_price),
            'quantity': product.quantity,
            'description': product.description
        })
    
    return jsonify({'products': products_data})


# ====================
# MANAGER ROUTES
# ====================

@app.route('/manager/dashboard')
@login_required
def manager_dashboard():
    """Store Manager dashboard - UPDATED WITH NOTIFICATIONS"""
    if current_user.role != 'manager':
        flash('Access denied. Manager only.', 'danger')
        return redirect(url_for('index'))
    
    # Get notifications for current manager
    notifications = Notification.query.filter_by(user_id=current_user.id)\
        .order_by(Notification.created_at.desc())\
        .limit(10).all()
    
    # Existing stats code...
    total_products = Product.query.count()
    total_categories = Category.query.count()
    total_suppliers = Supplier.query.count()
    
    # Stock alerts
    low_stock_products = Product.query.filter(
        Product.quantity <= Product.reorder_level
    ).all()
    out_of_stock_products = Product.query.filter(Product.quantity == 0).all()
    
    # Inventory value
    products = Product.query.all()
    total_stock_value = sum(product.cost_price * product.quantity for product in products)
    average_stock_level = sum(product.quantity for product in products) / len(products) if products else 0
    
    # Recent stock movements (last 10)
    recent_movements = StockMovement.query.order_by(StockMovement.timestamp.desc()).limit(10).all()
    
    # Today's sales
    from datetime import datetime, date
    today_sales = Sale.query.filter(db.func.date(Sale.sale_date) == date.today()).all()
    today_sales_total = sum(sale.total_amount for sale in today_sales)
    
    return render_template('manager/manager.html',
                         notifications=notifications,  # Add this line
                         total_products=total_products,
                         total_categories=total_categories,
                         total_suppliers=total_suppliers,
                         low_stock_products=low_stock_products,
                         low_stock_count=len(low_stock_products),
                         out_of_stock_count=len(out_of_stock_products),
                         total_stock_value=total_stock_value,
                         average_stock_level=round(average_stock_level, 1),
                         recent_movements=recent_movements,
                         today_sales_total=today_sales_total,
                         today_sales_count=len(today_sales))


#manager/products
@app.route('/manager/products')
@login_required
def manage_products():
    """Product management - manager only"""
    if current_user.role not in ['admin', 'manager']:
        flash('Access denied. Manager access required.', 'danger')
        return redirect(url_for('index'))
    
    products = Product.query.all()
    categories = Category.query.all()
    suppliers = Supplier.query.all()
    
    return render_template('manager/products.html',
                         products=products,
                         categories=categories,
                         suppliers=suppliers)

@app.route('/manager/products/add', methods=['POST'])
@login_required
def add_product():
    """Add new product - manager only"""
    if current_user.role not in ['admin', 'manager']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        
        name = request.form.get('name')
        sku = request.form.get('sku')
        description = request.form.get('description')
        cost_price = float(request.form.get('cost_price', 0))
        selling_price = float(request.form.get('selling_price', 0))
        quantity = int(request.form.get('quantity', 0))
        reorder_level = int(request.form.get('reorder_level', 10))
        category_id = int(request.form.get('category_id'))
        supplier_id = int(request.form.get('supplier_id'))
        
        
        if not all([name, sku]):
            return jsonify({'success': False, 'message': 'Name and SKU are required'})
        
        if Product.query.filter_by(sku=sku).first():
            return jsonify({'success': False, 'message': 'SKU already exists'})
        
        if selling_price < cost_price:
            return jsonify({'success': False, 'message': 'Selling price must be greater than cost price'})
        
        
        product = Product(
            name=name,
            sku=sku,
            description=description,
            cost_price=cost_price,
            selling_price=selling_price,
            quantity=quantity,
            reorder_level=reorder_level,
            category_id=category_id,
            supplier_id=supplier_id
        )
        
        db.session.add(product)
        db.session.commit()
        
        
        if quantity > 0:
            movement = StockMovement(
                product_id=product.id,
                movement_type='in',
                quantity=quantity,
                reason='initial_stock',
                user_id=current_user.id,
                reference_type='product_creation'
            )
            db.session.add(movement)
            db.session.commit()
        
        return jsonify({'success': True, 'message': 'Product added successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/manager/products/edit/<int:product_id>', methods=['POST'])
@login_required
def edit_product(product_id):
    """Edit product - manager only"""
    if current_user.role not in ['admin', 'manager']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        product = Product.query.get_or_404(product_id)
        
        # Get form data
        name = request.form.get('name')
        sku = request.form.get('sku')
        description = request.form.get('description')
        cost_price = float(request.form.get('cost_price', 0))
        selling_price = float(request.form.get('selling_price', 0))
        reorder_level = int(request.form.get('reorder_level', 10))
        category_id = int(request.form.get('category_id'))
        supplier_id = int(request.form.get('supplier_id'))
        
        # Check if SKU is taken by another product
        existing_product = Product.query.filter_by(sku=sku).first()
        if existing_product and existing_product.id != product_id:
            return jsonify({'success': False, 'message': 'SKU already taken by another product'})
        
        if selling_price < cost_price:
            return jsonify({'success': False, 'message': 'Selling price must be greater than cost price'})
        
        # Update product
        product.name = name
        product.sku = sku
        product.description = description
        product.cost_price = cost_price
        product.selling_price = selling_price
        product.reorder_level = reorder_level
        product.category_id = category_id
        product.supplier_id = supplier_id
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Product updated successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/manager/products/delete/<int:product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    """Delete product - manager only"""
    if current_user.role not in ['admin', 'manager']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        product = Product.query.get_or_404(product_id)
        
        # Check if product has sales history
        if product.sale_items:
            return jsonify({'success': False, 'message': 'Cannot delete product with sales history'})
        
        db.session.delete(product)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Product deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/manager/products/stock/<int:product_id>', methods=['POST'])
@login_required
def adjust_stock(product_id):
    """Adjust product stock - manager only"""
    if current_user.role not in ['admin', 'manager']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        product = Product.query.get_or_404(product_id)
        adjustment = int(request.form.get('adjustment', 0))
        adjustment_type = request.form.get('adjustment_type', 'add')  # Add this line
        reason = request.form.get('reason', 'stock_adjustment')
        
        if adjustment == 0:
            return jsonify({'success': False, 'message': 'No stock change specified'})
        
        # Handle different adjustment types
        if adjustment_type == 'add':
            new_quantity = product.quantity + adjustment
            movement_type = 'in'
        elif adjustment_type == 'remove':
            new_quantity = product.quantity - adjustment
            movement_type = 'out'
        elif adjustment_type == 'set':
            new_quantity = adjustment
            # Calculate the difference for movement tracking
            adjustment_amount = adjustment - product.quantity
            movement_type = 'in' if adjustment_amount > 0 else 'out'
            adjustment = abs(adjustment_amount)
        else:
            return jsonify({'success': False, 'message': 'Invalid adjustment type'})
        
        if new_quantity < 0:
            return jsonify({'success': False, 'message': 'Stock cannot be negative'})
        
        # Update stock
        product.quantity = new_quantity
        
        # Record stock movement
        movement = StockMovement(
            product_id=product_id,
            movement_type=movement_type,
            quantity=abs(adjustment),
            reason=reason,
            user_id=current_user.id,
            reference_type='manual_adjustment'
        )
        db.session.add(movement)
        db.session.commit()
        
        action = "updated"
        return jsonify({
            'success': True, 
            'message': f'Stock {action} successfully. New quantity: {new_quantity}'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})



# CATEGORIES ROUTE
@app.route('/manager/categories')
@login_required
def manage_categories():
    """Category management - manager only"""
    if current_user.role not in ['admin', 'manager']:
        flash('Access denied. Manager access required.', 'danger')
        return redirect(url_for('index'))
    
    categories = Category.query.all()
    return render_template('manager/categories.html', categories=categories)

#crud
@app.route('/manager/categories/add', methods=['POST'])
@login_required
def add_category():
    """Add new category - manager only"""
    if current_user.role not in ['admin', 'manager']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        name = request.form.get('name')
        description = request.form.get('description')
        
        # Validation
        if not name:
            return jsonify({'success': False, 'message': 'Category name is required'})
        
        if Category.query.filter_by(name=name).first():
            return jsonify({'success': False, 'message': 'Category name already exists'})
        
        # Create new category
        category = Category(name=name, description=description)
        db.session.add(category)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Category created successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/manager/categories/edit/<int:category_id>', methods=['POST'])
@login_required
def edit_category(category_id):
    """Edit category - manager only"""
    if current_user.role not in ['admin', 'manager']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        category = Category.query.get_or_404(category_id)
        name = request.form.get('name')
        description = request.form.get('description')
        
        # Check if name is taken by another category
        existing_category = Category.query.filter_by(name=name).first()
        if existing_category and existing_category.id != category_id:
            return jsonify({'success': False, 'message': 'Category name already taken'})
        
        category.name = name
        category.description = description
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Category updated successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/manager/categories/delete/<int:category_id>', methods=['POST'])
@login_required
def delete_category(category_id):
    """Delete category - manager only"""
    if current_user.role not in ['admin', 'manager']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        category = Category.query.get_or_404(category_id)
        
        # Check if category has products
        if category.products:
            return jsonify({
                'success': False, 
                'message': f'Cannot delete category with {len(category.products)} products. Move products first.'
            })
        
        db.session.delete(category)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Category deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

# INVENTORY ROUTE  
@app.route('/manager/inventory')
@login_required
def manage_inventory():
    if current_user.role not in ['admin', 'manager']:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    products = Product.query.all()
    stock_movements = StockMovement.query.order_by(StockMovement.timestamp.desc()).limit(50).all()
    total_stock_value = sum(p.cost_price * p.quantity for p in products)
    low_stock_count = len([p for p in products if p.quantity <= p.reorder_level])
    
    return render_template('manager/inventory.html',
                         products=products,
                         stock_movements=stock_movements,
                         total_stock_value=total_stock_value,
                         low_stock_count=low_stock_count)

#Purchase order
@app.route('/manager/purchase-orders')
@login_required
def manage_purchase_orders():
    """Purchase orders management - manager only"""
    if current_user.role not in ['admin', 'manager']:
        flash('Access denied. Manager access required.', 'danger')
        return redirect(url_for('index'))
    
    purchase_orders = PurchaseOrder.query.order_by(PurchaseOrder.order_date.desc()).all()
    suppliers = Supplier.query.filter_by(is_active=True).all()
    products = Product.query.all()
    
    return render_template('manager/purchaseorders.html',
                         purchase_orders=purchase_orders,
                         suppliers=suppliers,
                         products=products)

@app.route('/manager/purchase-orders/add', methods=['POST'])
@login_required
def add_purchase_order():
    """Add new purchase order - manager only"""
    if current_user.role not in ['admin', 'manager']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        supplier_id = int(request.form.get('supplier_id'))
        expected_delivery = request.form.get('expected_delivery')
        notes = request.form.get('notes')
        product_id = request.form.get('product_id')
        quantity = int(request.form.get('quantity', 1))
        unit_price = float(request.form.get('unit_price', 0))
        
        # Generate order number
        from datetime import datetime
        order_number = f"PO-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        
        # Calculate total amount
        total_amount = quantity * unit_price
        
        # Get supplier information
        supplier = Supplier.query.get(supplier_id)
        if not supplier:
            return jsonify({'success': False, 'message': 'Supplier not found'})
        
        # Create purchase order
        purchase_order = PurchaseOrder(
            order_number=order_number,
            supplier_id=supplier_id,
            status='pending',
            total_amount=total_amount,
            expected_delivery=datetime.strptime(expected_delivery, '%Y-%m-%d') if expected_delivery else None,
            notes=notes,
            created_by=current_user.id
        )
        
        db.session.add(purchase_order)
        
        # Create notification for supplier if they have a user account
        if supplier.user_id:
            notification = Notification(
                user_id=supplier.user_id,
                title='New Purchase Order',
                message=f'New purchase order #{order_number} has been created for you. Total: KES {total_amount:,.2f}',
                type='info',
                related_type='purchase_order',
                related_id=purchase_order.id
            )
            db.session.add(notification)
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Purchase order created successfully',
            'order_id': purchase_order.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/manager/purchase-orders/update-status/<int:order_id>', methods=['POST'])
@login_required
def update_po_status(order_id):
    """Update purchase order status - manager only"""
    if current_user.role not in ['admin', 'manager']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        purchase_order = PurchaseOrder.query.get_or_404(order_id)
        new_status = request.form.get('status')
        
        valid_statuses = ['pending', 'approved', 'ordered', 'delivered', 'cancelled']
        if new_status not in valid_statuses:
            return jsonify({'success': False, 'message': 'Invalid status'})
        
        purchase_order.status = new_status
        
        # If delivered, update delivery date
        if new_status == 'delivered':
            purchase_order.delivery_date = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'Order status updated to {new_status}'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})
    

@app.route('/manager/orders/<int:order_id>/details')
@login_required
def manager_get_order_details(order_id):
    """Manager views purchase order details"""
    if current_user.role not in ['admin', 'manager']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    order = PurchaseOrder.query.get_or_404(order_id)
    
    html = f"""
        <div class="space-y-4">
            <div class="grid grid-cols-2 gap-4">
                <div><strong>Order Number:</strong> {order.order_number}</div>
                <div><strong>Status:</strong> <span class="px-2 py-1 bg-blue-100 rounded">{order.status}</span></div>
            </div>
            
            <div class="grid grid-cols-2 gap-4">
                <div><strong>Supplier:</strong> {order.supplier.name}</div>
                <div><strong>Contact:</strong> {order.supplier.email}</div>
            </div>
            
            <div class="grid grid-cols-2 gap-4">
                <div><strong>Order Date:</strong> {order.order_date.strftime('%b %d, %Y')}</div>
                <div><strong>Expected Delivery:</strong> {order.expected_delivery.strftime('%b %d, %Y') if order.expected_delivery else 'Not set'}</div>
            </div>
            
            <div><strong>Total Amount:</strong> <span class="text-green-600 font-bold">KES {order.total_amount:,.2f}</span></div>
            
            <div><strong>Notes:</strong><br>{order.notes or 'No notes'}</div>
        </div>
    """
    
    return jsonify({'success': True, 'html': html}) 

@app.route('/manager/orders/<int:order_id>/edit-data')
@login_required
def get_order_edit_data(order_id):
    """Get order data for editing"""
    if current_user.role not in ['admin', 'manager']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    order = PurchaseOrder.query.get_or_404(order_id)
    
    return jsonify({
        'success': True,
        'data': {
            'id': order.id,
            'supplier_id': order.supplier_id,
            'expected_delivery': order.expected_delivery.strftime('%Y-%m-%d') if order.expected_delivery else '',
            'notes': order.notes or '',
            'total_amount': float(order.total_amount)
        }
    })  

@app.route('/manager/purchase-orders/update/<int:order_id>', methods=['POST'])
@login_required
def update_purchase_order(order_id):
    """Update purchase order"""
    if current_user.role not in ['admin', 'manager']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        order = PurchaseOrder.query.get_or_404(order_id)
        
        supplier_id = request.form.get('supplier_id')
        expected_delivery = request.form.get('expected_delivery')
        notes = request.form.get('notes')
        
        # Update order
        order.supplier_id = int(supplier_id)
        order.expected_delivery = datetime.strptime(expected_delivery, '%Y-%m-%d') if expected_delivery else None
        order.notes = notes
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Purchase order updated successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}) 
    

@app.route('/manager/suppliers')
@login_required
def manage_sup():
    """Supplier management - manager only"""
    if current_user.role not in ['admin', 'manager']:
        flash('Access denied. Manager access required.', 'danger')
        return redirect(url_for('index'))
    
    return render_template('manager/sup.html')

#reports
@app.route('/manager/reports')
@login_required
def manage_reports():
    """Enhanced Reports - manager only"""
    if current_user.role not in ['admin', 'manager']:
        flash('Access denied. Manager access required.', 'danger')
        return redirect(url_for('index'))
    
    # Basic inventory stats
    total_products = Product.query.count()
    total_categories = Category.query.count()
    low_stock_count = Product.query.filter(Product.quantity <= Product.reorder_level).count()
    out_of_stock_count = Product.query.filter(Product.quantity == 0).count()
    
    # SALES ANALYTICS
    from datetime import datetime, timedelta, date
    
    # Today's sales
    today_sales = Sale.query.filter(db.func.date(Sale.sale_date) == date.today()).all()
    today_total = sum(sale.total_amount for sale in today_sales)
    today_count = len(today_sales)
    
    # Yesterday's sales for comparison
    yesterday = date.today() - timedelta(days=1)
    yesterday_sales = Sale.query.filter(db.func.date(Sale.sale_date) == yesterday).all()
    yesterday_total = sum(sale.total_amount for sale in yesterday_sales) if yesterday_sales else 0
    
    # Weekly sales (last 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)
    weekly_sales = Sale.query.filter(Sale.sale_date >= week_ago).all()
    weekly_total = sum(sale.total_amount for sale in weekly_sales)
    
    # Monthly sales (current month)
    start_of_month = date.today().replace(day=1)
    monthly_sales = Sale.query.filter(Sale.sale_date >= start_of_month).all()
    monthly_total = sum(sale.total_amount for sale in monthly_sales)
    
    # Top selling products (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    top_products = db.session.query(
        Product.name,
        db.func.sum(SaleItem.quantity).label('total_sold'),
        db.func.sum(SaleItem.subtotal).label('total_revenue')
    ).join(SaleItem, Product.id == SaleItem.product_id)\
     .join(Sale, SaleItem.sale_id == Sale.id)\
     .filter(Sale.sale_date >= thirty_days_ago)\
     .group_by(Product.id)\
     .order_by(db.desc('total_sold'))\
     .limit(10).all()
    
    # Sales by payment method
    payment_methods = db.session.query(
        Sale.payment_method,
        db.func.count(Sale.id).label('count'),
        db.func.sum(Sale.total_amount).label('total')
    ).group_by(Sale.payment_method).all()
    
    # Daily sales for the last 14 days (for charts)
    daily_sales_data = {}
    for i in range(14):
        day = date.today() - timedelta(days=i)
        day_sales = Sale.query.filter(db.func.date(Sale.sale_date) == day).all()
        daily_sales_data[day.strftime('%Y-%m-%d')] = sum(sale.total_amount for sale in day_sales)
    
    # Sales growth calculation
    sales_growth = 0
    if yesterday_total > 0:
        sales_growth = ((today_total - yesterday_total) / yesterday_total) * 100
    
    return render_template('manager/reports.html',
                         total_products=total_products,
                         total_categories=total_categories,
                         low_stock_count=low_stock_count,
                         out_of_stock_count=out_of_stock_count,
                         
                         # Sales data
                         today_total=today_total,
                         today_count=today_count,
                         yesterday_total=yesterday_total,
                         weekly_total=weekly_total,
                         monthly_total=monthly_total,
                         sales_growth=sales_growth,
                         top_products=top_products,
                         payment_methods=payment_methods,
                         daily_sales_data=daily_sales_data)


# ====================
# SUPPLIER ROUTES
# ====================

@app.route('/supplier/dashboard')
@login_required
def supplier_dashboard():
    """Supplier dashboard - shows their product catalog WITH NOTIFICATIONS"""
    if current_user.role != 'supplier':
        flash('Access denied. Supplier only.', 'danger')
        return redirect(url_for('index'))
    
    # Get supplier info
    supplier = Supplier.query.filter_by(user_id=current_user.id).first()
    
    if not supplier:
        flash('Supplier profile not found.', 'warning')
        return render_template('supplier/supplier.html', supplier=None)
    
    # Get supplier's product catalog
    supplier_products = SupplierProduct.query.filter_by(supplier_id=supplier.id).all()
    
    # Get purchase orders for this supplier
    purchase_orders = PurchaseOrder.query.filter_by(supplier_id=supplier.id).order_by(PurchaseOrder.order_date.desc()).all()
    
    # Get categories for product form
    categories = Category.query.all()
    
    # Get notifications for current supplier
    notifications = Notification.query.filter_by(user_id=current_user.id)\
        .order_by(Notification.created_at.desc())\
        .limit(10).all()
    
    # Calculate stats
    total_orders = len(purchase_orders)
    pending_orders = len([po for po in purchase_orders if po.status == 'pending'])
    delivered_orders = len([po for po in purchase_orders if po.status == 'delivered'])
    total_products = len(supplier_products)
    
    return render_template('supplier/supplier.html',
                         supplier=supplier,
                         purchase_orders=purchase_orders,
                         products=supplier_products,
                         categories=categories,
                         total_orders=total_orders,
                         pending_orders=pending_orders,
                         delivered_orders=delivered_orders,
                         total_products=total_products,
                         notifications=notifications)  


@app.route('/supplier/orders/<int:order_id>/confirm', methods=['POST'])
@login_required
def supplier_confirm_order(order_id):
    """Supplier confirms they can fulfill the order - FIXED VERSION"""
    if current_user.role != 'supplier':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        supplier = Supplier.query.filter_by(user_id=current_user.id).first()
        if not supplier:
            return jsonify({'success': False, 'message': 'Supplier profile not found'})
        
        order = PurchaseOrder.query.filter_by(id=order_id, supplier_id=supplier.id).first()
        if not order:
            return jsonify({'success': False, 'message': 'Order not found'})
        
        # FIXED: Check if order is pending (not approved)
        if order.status != 'pending':
            return jsonify({'success': False, 'message': 'Order is not in pending status'})
        
        # Update order status to approved (supplier accepts)
        order.status = 'approved'
        
        # Create notification for manager
        notification = Notification(
            user_id=order.created_by,  # Notify the manager who created the order
            title='Order Accepted by Supplier',
            message=f'Supplier {supplier.name} has accepted purchase order #{order.order_number}',
            type='success',
            related_type='purchase_order',
            related_id=order.id
        )
        db.session.add(notification)
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Order confirmed successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

# @app.route('/supplier/orders/<int:order_id>/decline', methods=['POST'])
# @login_required
# def supplier_decline_order(order_id):
#     """Supplier declines the order - FIXED VERSION"""
#     if current_user.role != 'supplier':
#         return jsonify({'success': False, 'message': 'Access denied'}), 403
    
#     try:
#         supplier = Supplier.query.filter_by(user_id=current_user.id).first()
#         if not supplier:
#             return jsonify({'success': False, 'message': 'Supplier profile not found'})
        
#         order = PurchaseOrder.query.filter_by(id=order_id, supplier_id=supplier.id).first()
#         if not order:
#             return jsonify({'success': False, 'message': 'Order not found'})
        
#         data = request.get_json()
#         reason = data.get('reason', 'No reason provided')
        
#         # Update order status to cancelled
#         order.status = 'cancelled'
        
#         # Create notification for manager
#         notification = Notification(
#             user_id=order.created_by,
#             title='Order Declined by Supplier',
#             message=f'Supplier {supplier.name} declined order {order.order_number}. Reason: {reason}',
#             type='error',
#             related_type='purchase_order',
#             related_id=order.id
#         )
#         db.session.add(notification)
        
#         db.session.commit()
        
#         return jsonify({'success': True, 'message': 'Order declined successfully'})
        
#     except Exception as e:
#         db.session.rollback()
#         return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/supplier/orders/<int:order_id>/update-status', methods=['POST'])
@login_required
def supplier_update_order_status(order_id):
    """Supplier updates order status for shipping/delivery"""
    if current_user.role != 'supplier':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        supplier = Supplier.query.filter_by(user_id=current_user.id).first()
        if not supplier:
            return jsonify({'success': False, 'message': 'Supplier profile not found'})
        
        order = PurchaseOrder.query.filter_by(id=order_id, supplier_id=supplier.id).first()
        if not order:
            return jsonify({'success': False, 'message': 'Order not found'})
        
        data = request.get_json()
        new_status = data.get('status')
        
        # Validate status
        valid_statuses = ['ordered', 'delivered']
        if new_status not in valid_statuses:
            return jsonify({'success': False, 'message': 'Invalid status'})
        
        # Update order status
        old_status = order.status
        order.status = new_status
        
        # If delivered, update delivery date
        if new_status == 'delivered':
            order.delivery_date = datetime.utcnow()
            
        # Create notification for manager
        status_messages = {
            'ordered': f'Supplier {supplier.name} has shipped order {order.order_number}',
            'delivered': f'Supplier {supplier.name} has delivered order {order.order_number}'
        }
        
        notification = Notification(
            user_id=order.created_by,
            title=f'Order {new_status.title()} by Supplier',
            message=status_messages.get(new_status, f'Order status updated to {new_status}'),
            type='info',
            related_type='purchase_order',
            related_id=order.id
        )
        db.session.add(notification)
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'Order status updated to {new_status}'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/supplier/orders/<int:order_id>/details')
@login_required
def get_order_details(order_id):
    """Get order details for supplier"""
    if current_user.role != 'supplier':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    order = PurchaseOrder.query.get_or_404(order_id)
    
    html = f"""
    <div class="space-y-4">
        <div class="grid grid-cols-2 gap-4">
            <div><strong>Order Number:</strong> {order.order_number}</div>
            <div><strong>Status:</strong> <span class="px-2 py-1 bg-blue-100 rounded">{order.status}</span></div>
        </div>
        
        <div class="grid grid-cols-2 gap-4">
            <div><strong>Supplier:</strong> {order.supplier.name}</div>
            <div><strong>Contact:</strong> {order.supplier.email}</div>
        </div>
        
        <div class="grid grid-cols-2 gap-4">
            <div><strong>Order Date:</strong> {order.order_date.strftime('%b %d, %Y')}</div>
            <div><strong>Expected Delivery:</strong> {order.expected_delivery.strftime('%b %d, %Y') if order.expected_delivery else 'Not set'}</div>
        </div>
        
        <div class="grid grid-cols-2 gap-4">
            <div><strong>Created By:</strong> {order.creator.username}</div>
            <div><strong>Total Amount:</strong> <span class="text-green-600 font-bold">KES {order.total_amount:,.2f}</span></div>
        </div>
        
        <div><strong>Notes:</strong><br>{order.notes or 'No special instructions'}</div>
        
        {f'<div><strong>Delivered On:</strong> {order.delivery_date.strftime("%b %d, %Y")}</div>' if order.delivery_date else ''}
    </div>
"""
    
    return jsonify({'success': True, 'html': html})

# @app.route('/supplier/orders/<int:order_id>/update-status', methods=['POST'])
# @login_required
# def supplier_update_order_status(order_id):
#     """Supplier updates order status"""
#     if current_user.role != 'supplier':
#         return jsonify({'success': False, 'message': 'Access denied'}), 403
    
#     try:
#         order = PurchaseOrder.query.get_or_404(order_id)
#         data = request.get_json()
#         new_status = data.get('status')
        
#         order.status = new_status
#         db.session.commit()
        
#         return jsonify({'success': True, 'message': 'Status updated'})
#     except Exception as e:
#         db.session.rollback()
#         return jsonify({'success': False, 'message': str(e)})

# ====================
# SUPPLIER PRODUCT ROUTES
# ====================

@app.route('/supplier/products/add', methods=['POST'])
@login_required
def add_supplier_product():
    """Add product to supplier's catalog"""
    if current_user.role != 'supplier':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        supplier = Supplier.query.filter_by(user_id=current_user.id).first()
        if not supplier:
            return jsonify({'success': False, 'message': 'Supplier profile not found'})
        
        data = request.get_json()
        
        # Validation
        if not data.get('name'):
            return jsonify({'success': False, 'message': 'Product name is required'})
        
        if not data.get('sku'):
            return jsonify({'success': False, 'message': 'SKU is required'})
        
        if not data.get('price'):
            return jsonify({'success': False, 'message': 'Price is required'})
        
        if not data.get('category_id'):
            return jsonify({'success': False, 'message': 'Category is required'})
        
        # Create supplier product (separate from main inventory)
        supplier_product = SupplierProduct(
            name=data['name'],
            sku=data['sku'],
            description=data.get('description', ''),
            price=float(data['price']),
            category_id=int(data['category_id']),
            supplier_id=supplier.id,
            image_url=data.get('image_url'),
            unit=data.get('unit', 'piece')
        )
        
        db.session.add(supplier_product)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Product added to your catalog!',
            'product': {
                'id': supplier_product.id,
                'name': supplier_product.name,
                'price': supplier_product.price
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})
    

@app.route('/supplier/products/<int:product_id>/edit', methods=['POST'])
@login_required
def edit_supplier_product(product_id):
    """Edit supplier product"""
    if current_user.role != 'supplier':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        # Get supplier profile
        supplier = Supplier.query.filter_by(user_id=current_user.id).first()
        if not supplier:
            return jsonify({'success': False, 'message': 'Supplier profile not found'})
        
        product = SupplierProduct.query.filter_by(id=product_id, supplier_id=supplier.id).first()
        if not product:
            return jsonify({'success': False, 'message': 'Product not found'})
        
        data = request.get_json()
        
        # Update product fields
        if 'name' in data:
            product.name = data['name']
        if 'sku' in data:
            # Check if SKU is taken by another supplier product
            existing_product = SupplierProduct.query.filter_by(sku=data['sku']).first()
            if existing_product and existing_product.id != product_id:
                return jsonify({'success': False, 'message': 'SKU already taken'})
            product.sku = data['sku']
        if 'description' in data:
            product.description = data['description']
        if 'price' in data:
            product.price = float(data['price'])
        if 'category_id' in data:
            product.category_id = int(data['category_id'])
        if 'unit' in data:
            product.unit = data['unit']
        if 'image_url' in data:
            product.image_url = data['image_url']
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Product updated successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})
    

@app.route('/supplier/products', methods=['GET'])
@login_required
def get_supplier_products():
    """Get all products for current supplier"""
    if current_user.role != 'supplier':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        supplier = Supplier.query.filter_by(user_id=current_user.id).first()
        if not supplier:
            return jsonify({'products': []})
        
        products = SupplierProduct.query.filter_by(supplier_id=supplier.id).all()
        
        products_data = []
        for product in products:
            products_data.append({
                'id': product.id,
                'name': product.name,
                'sku': product.sku,
                'description': product.description,
                'price': float(product.price),
                'category_id': product.category_id,
                'category': product.category.name if product.category else 'General',
                'image_url': product.image_url,
                'unit': product.unit
            })
        
        return jsonify({'success': True, 'products': products_data})
    
    except Exception as e:
        print(f"Error fetching products: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})
    

@app.route('/supplier/products/<int:product_id>/delete', methods=['POST'])
@login_required
def delete_supplier_product(product_id):
    """Delete supplier product"""
    if current_user.role != 'supplier':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        supplier = Supplier.query.filter_by(user_id=current_user.id).first()
        if not supplier:
            return jsonify({'success': False, 'message': 'Supplier profile not found'})
        
        product = SupplierProduct.query.filter_by(id=product_id, supplier_id=supplier.id).first()
        if not product:
            return jsonify({'success': False, 'message': 'Product not found'})
        
        db.session.delete(product)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Product deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})
    

@app.route('/supplier/products/<int:product_id>')
@login_required
def get_supplier_product(product_id):
    """Get single supplier product for editing"""
    if current_user.role != 'supplier':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        supplier = Supplier.query.filter_by(user_id=current_user.id).first()
        if not supplier:
            return jsonify({'success': False, 'message': 'Supplier profile not found'})
        
        product = SupplierProduct.query.filter_by(id=product_id, supplier_id=supplier.id).first()
        if not product:
            return jsonify({'success': False, 'message': 'Product not found'})
        
        product_data = {
            'id': product.id,
            'name': product.name,
            'sku': product.sku,
            'description': product.description,
            'price': float(product.price),
            'category_id': product.category_id,
            'image_url': product.image_url,
            'unit': product.unit
        }
        
        return jsonify({'success': True, 'product': product_data})
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})   


# @app.route('/supplier/orders/<int:order_id>/confirm', methods=['POST'])
# @login_required
# def supplier_confirm_order(order_id):
#     """Supplier confirms they can fulfill the order"""
#     if current_user.role != 'supplier':
#         return jsonify({'success': False, 'message': 'Access denied'}), 403
    
#     try:
#         supplier = Supplier.query.filter_by(user_id=current_user.id).first()
#         if not supplier:
#             return jsonify({'success': False, 'message': 'Supplier profile not found'})
        
#         order = PurchaseOrder.query.filter_by(id=order_id, supplier_id=supplier.id).first()
#         if not order:
#             return jsonify({'success': False, 'message': 'Order not found'})
        
#         if order.status != 'approved':
#             return jsonify({'success': False, 'message': 'Order must be approved first'})
        
#         # Update order status
#         order.status = 'confirmed'
        
#         # Create notification for manager
#         notification = Notification(
#             user_id=order.created_by,  # Notify the manager who created the order
#             title='Order Confirmed by Supplier',
#             message=f'Supplier {supplier.name} has confirmed order {order.order_number}',
#             type='success',
#             related_type='purchase_order',
#             related_id=order.id
#         )
#         db.session.add(notification)
        
#         db.session.commit()
        
#         return jsonify({'success': True, 'message': 'Order confirmed successfully'})
        
#     except Exception as e:
#         db.session.rollback()
#         return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/supplier/orders/<int:order_id>/decline', methods=['POST'])
@login_required
def supplier_decline_order(order_id):
    """Supplier declines the order"""
    if current_user.role != 'supplier':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        supplier = Supplier.query.filter_by(user_id=current_user.id).first()
        if not supplier:
            return jsonify({'success': False, 'message': 'Supplier profile not found'})
        
        order = PurchaseOrder.query.filter_by(id=order_id, supplier_id=supplier.id).first()
        if not order:
            return jsonify({'success': False, 'message': 'Order not found'})
        
        data = request.get_json()
        reason = data.get('reason', 'No reason provided')
        
        # Update order status
        order.status = 'cancelled'
        
        # Create notification for manager
        notification = Notification(
            user_id=order.created_by,
            title='Order Declined by Supplier',
            message=f'Supplier {supplier.name} declined order {order.order_number}. Reason: {reason}',
            type='error',
            related_type='purchase_order',
            related_id=order.id
        )
        db.session.add(notification)
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Order declined successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})     

@app.route('/api/categories')
@login_required
def get_categories():
    """Get all categories for product forms"""
    categories = Category.query.all()
    return jsonify({
        'categories': [{'id': c.id, 'name': c.name} for c in categories]
    })
    

@app.route('/manager/suppliers/json')
@login_required
def manager_suppliers_data():
    """Get suppliers data for manager - includes supplier products"""
    if current_user.role not in ['admin', 'manager']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        suppliers = Supplier.query.all()
        
        suppliers_data = []
        for supplier in suppliers:
            # Get supplier's product catalog
            supplier_products = SupplierProduct.query.filter_by(supplier_id=supplier.id).all()
            
            suppliers_data.append({
                'id': supplier.id,
                'name': supplier.name,
                'contact_person': supplier.contact_person,
                'email': supplier.email,
                'phone': supplier.phone,
                'address': supplier.address,
                'is_active': supplier.is_active,
                'products': [{
                    'id': product.id,
                    'name': product.name,
                    'sku': product.sku,
                    'selling_price': float(product.price),  # ← Map price to selling_price
                    'price': float(product.price),          # ← Keep original for compatibility
                    'quantity': 0,                          # ← Supplier products don't have stock
                    'reorder_level': 0,                     # ← Default value
                    'description': product.description,
                    'image_url': product.image_url,
                    'unit': product.unit,
                    'category': product.category.name if product.category else 'General'
                } for product in supplier_products],
                'products_count': len(supplier_products),
                'last_product_added': max([p.created_at for p in supplier_products]).strftime('%Y-%m-%d') if supplier_products else None
            })
        
        return jsonify({'success': True, 'suppliers': suppliers_data})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})
    

@app.route('/manager/suppliers/<int:supplier_id>/products')
@login_required
def get_supplier_catalog_products(supplier_id):
    """Get products for a specific supplier"""
    if current_user.role not in ['admin', 'manager']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        supplier = Supplier.query.get_or_404(supplier_id)
        
        # Get supplier's catalog products
        supplier_products = SupplierProduct.query.filter_by(supplier_id=supplier_id).all()
        
        products_data = []
        for product in supplier_products:
            products_data.append({
                'id': product.id,
                'name': product.name,
                'sku': product.sku,
                'price': float(product.price),
                'unit': product.unit,
                'description': product.description,
                'category': product.category.name if product.category else 'General'
            })
        
        return jsonify({
            'success': True, 
            'products': products_data,
            'supplier_name': supplier.name
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})    

@app.route('/fix-supplier-profiles')
@login_required
def fix_supplier_profiles():
    """Fix supplier profiles for existing users"""
    if current_user.role != 'admin':
        flash('Access denied. Admin only.', 'danger')
        return redirect(url_for('index'))
    
    # Get all supplier users
    supplier_users = User.query.filter_by(role='supplier').all()
    fixed_count = 0
    
    for user in supplier_users:
        # Check if supplier profile exists
        supplier = Supplier.query.filter_by(user_id=user.id).first()
        if not supplier:
            # Create missing supplier profile
            supplier = Supplier(
                name=f"{user.username}'s Company",
                contact_person=user.username,
                email=user.email,
                phone=None,
                address=None,
                user_id=user.id,
                is_active=True
            )
            db.session.add(supplier)
            fixed_count += 1
            print(f"Created supplier profile for: {user.username}")
    
    db.session.commit()
    flash(f'Fixed {fixed_count} supplier profiles.', 'success')
    return redirect(url_for('admin_dashboard'))


# ====================
# DATABASE INITIALIZATION
# ====================

def init_db():
    """Initialize database with tables and sample data"""
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Check if admin user exists
        if not User.query.filter_by(username='admin').first():
            # Create default admin user
            admin = User(
                username='admin',
                email='admin@inventory.com',
                role='admin',
                is_active=True
            )
            admin.set_password('admin123')  # Change this password!
            db.session.add(admin)
            
            # Create sample cashier
            cashier = User(
                username='cashier',
                email='cashier@inventory.com',
                role='cashier',
                is_active=True
            )
            cashier.set_password('cashier123')
            db.session.add(cashier)
            
            # Create sample manager
            manager = User(
                username='manager',
                email='manager@inventory.com',
                role='manager',
                is_active=True
            )
            manager.set_password('manager123')
            db.session.add(manager)
            
            # Create sample categories
            electronics = Category(name='Home & Kitchen', description='Utensils, cookware, storage containers')
            food = Category(name='Food & Beverages', description='Food items and drinks')
            clothing = Category(name='Clothing', description='Apparel and fashion items')
            
            db.session.add_all([electronics, food, clothing])
            
            # Create sample supplier
            supplier_company = Supplier(
                name='Tech Suppliers Ltd',
                contact_person='John Doe',
                email='supplier@techsuppliers.com',
                phone='+254700000000',
                address='Nairobi, Kenya'
            )
            db.session.add(supplier_company)
            
            # Commit all changes
            db.session.commit()
            
            print("Database initialized with sample data!")
            print("\nDefault login credentials:")
            print("Admin - username: admin, password: admin123")
            print("Cashier - username: cashier, password: cashier123")
            print("Manager - username: manager, password: manager123")


# Add these routes to your app.py

@app.route('/notifications')
@login_required
def get_notifications():
    """Get notifications for current user"""
    notifications = Notification.query.filter_by(user_id=current_user.id)\
        .order_by(Notification.created_at.desc())\
        .limit(50).all()
    
    notifications_data = []
    for notification in notifications:
        notifications_data.append({
            'id': notification.id,
            'title': notification.title,
            'message': notification.message,
            'type': notification.type,
            'is_read': notification.is_read,
            'created_at': notification.created_at.isoformat(),
            'related_type': notification.related_type,
            'related_id': notification.related_id
        })
    
    return jsonify({'success': True, 'notifications': notifications_data})

@app.route('/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """Mark notification as read"""
    try:
        notification = Notification.query.filter_by(
            id=notification_id, 
            user_id=current_user.id
        ).first()
        
        if notification:
            notification.is_read = True
            db.session.commit()
            return jsonify({'success': True, 'message': 'Notification marked as read'})
        else:
            return jsonify({'success': False, 'message': 'Notification not found'})
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/notifications/read-all', methods=['POST'])
@login_required
def mark_all_notifications_read():
    """Mark all notifications as read"""
    try:
        Notification.query.filter_by(user_id=current_user.id, is_read=False)\
            .update({'is_read': True})
        db.session.commit()
        return jsonify({'success': True, 'message': 'All notifications marked as read'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})            


@app.route('/fix-suppliers')
def fix_suppliers():
    """Fix existing supplier users who don't have profiles"""
    supplier_users = User.query.filter_by(role='supplier').all()
    
    for user in supplier_users:
        # Check if supplier profile exists
        existing_supplier = Supplier.query.filter_by(user_id=user.id).first()
        if not existing_supplier:
            # Create missing supplier profile
            supplier = Supplier(
                name=f"{user.username}'s Company",
                contact_person=user.username,
                email=user.email,
                phone=None,
                address=None,
                user_id=user.id,
                is_active=True
            )
            db.session.add(supplier)
            print(f"Created supplier profile for: {user.username}")
    
    db.session.commit()
    return "Supplier profiles fixed!"

def update_database_schema():
    """Update database schema to fix issues"""
    with app.app_context():
        try:
            # This will handle the duplicate status field issue
            db.create_all()
            print("Database schema updated successfully!")
            
            # Check if we need to fix any existing purchase orders
            orders_with_wrong_status = PurchaseOrder.query.filter(PurchaseOrder.status == 'confirmed').all()
            for order in orders_with_wrong_status:
                order.status = 'approved'  # Change to correct status
            db.session.commit()
            
            print(f"Fixed {len(orders_with_wrong_status)} orders with incorrect status")
            
        except Exception as e:
            print(f"Error updating schema: {str(e)}")
            db.session.rollback()

# Run this once
if __name__ == '__main__':
    update_database_schema()
    app.run(debug=True)