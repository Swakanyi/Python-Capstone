from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

#USERS
class User(UserMixin, db.Model):
    """System Users: admin, cashier, manager, supplier"""

    __tablename__='users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    #password
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
       #check if password matches stored hash
    def check_password(self, password): 
        return check_password_hash(self.password_hash, password) 

    def __repr__(self):
          return f"<User {self.username} ({self.role})>"
    

#PRODUCT CATEGORIES TABLE
class Category(db.Model):
    

    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Category {self.name}>"
    
#SUPPLIERS TABLE
class Supplier(db.Model):
    

    __tablename__ = 'suppliers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    contact_person = db.Column(db.String(100))
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    # Relationship to linked user account (if supplier can log in)
    user = db.relationship('User', backref='supplier_account', uselist=False)

    def __repr__(self):
        return f"<Supplier {self.name}>"
    

#PRODUCTS
class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    sku = db.Column(db.String(50), unique=True, nullable=False)  # Stock code
    description = db.Column(db.Text)
    cost_price = db.Column(db.Float, nullable=False)
    selling_price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, default=0)
    reorder_level = db.Column(db.Integer, default=10)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    
    # ADD THESE TWO NEW FIELDS:
    image_url = db.Column(db.String(500))  # For Cloudinary image URLs
    unit = db.Column(db.String(50), default='piece')  # piece, kg, liter, pack, box, etc.

    #Links to
    category = db.relationship('Category', backref='products')
    supplier = db.relationship('Supplier', backref='products')
    

    @property
    def is_low_stock(self):
        """Return True if stock is below or at reorder level."""
        return self.quantity <= self.reorder_level

    def __repr__(self):
        return f"<Product {self.name} (Stock: {self.quantity})>"
    

class SupplierProduct(db.Model):
    """Supplier's product catalog - separate from main inventory"""
    __tablename__ = 'supplier_products'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    sku = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)  # Supplier's price
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=False)
    image_url = db.Column(db.String(500))
    unit = db.Column(db.String(50), default='piece')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    category = db.relationship('Category', backref='supplier_products')
    supplier = db.relationship('Supplier', backref='supplier_products')

    def __repr__(self):
        return f"<SupplierProduct {self.name}>"    
    

#SALES TABLE
class Sale(db.Model):
    """Record of a sale transaction"""

    __tablename__ = 'sales'

    id = db.Column(db.Integer, primary_key=True)
    sale_number = db.Column(db.String(50), unique=True, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(20), default='cash')
    cashier_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    sale_date = db.Column(db.DateTime, default=datetime.utcnow)
    customer_name = db.Column(db.String(100))
    customer_phone = db.Column(db.String(20))

    # Links to
    cashier = db.relationship('User', backref='sales')

    def __repr__(self):
        return f"<Sale {self.sale_number} - KES {self.total_amount}>"


#SALE ITEMS TABLE
class SaleItem(db.Model):
    """Individual products in a sale"""

    __tablename__ = 'sale_items'

    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)

    #links to
    sale = db.relationship('Sale', backref='items')
    product = db.relationship('Product', backref='sale_items')

    def __repr__(self):
        return f"<SaleItem {self.product.name} x {self.quantity}>"
    

#PURCHASE ORDERS
class PurchaseOrder(db.Model):
    """Track orders made to suppliers"""

    __tablename__ = 'purchase_orders'

    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(50), unique=True, nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')
    total_amount = db.Column(db.Float, nullable=False)
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    expected_delivery = db.Column(db.DateTime)
    delivery_date = db.Column(db.DateTime)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    notes = db.Column(db.Text)

    #links to
    supplier = db.relationship('Supplier', backref='purchase_orders')
    creator = db.relationship('User', backref='purchase_orders')

    def __repr__(self):
        return f"<PurchaseOrder {self.order_number} - {self.status}>" 
    


#STOCK MOVEMENTS 
class StockMovement(db.Model):
    """Tracks all inventory changes (sales, purchases, manual adjustments)"""

    __tablename__ = 'stock_movements'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    movement_type = db.Column(db.String(20), nullable=False)  # 'in', 'out', 'adjustment'
    quantity = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(100))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reference_id = db.Column(db.Integer)  # related sale or purchase
    reference_type = db.Column(db.String(20))  # 'sale' or 'purchase_order'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    #links to
    product = db.relationship('Product', backref='stock_movements')
    user = db.relationship('User', backref='stock_movements')

    def __repr__(self):
        return f"<StockMovement {self.movement_type} - {self.product.name} ({self.quantity})>"  
    
#NOTIFICATIONS
   

class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)  # Primary key is properly defined
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50), default='info')
    is_read = db.Column(db.Boolean, default=False)
    related_type = db.Column(db.String(50))
    related_id = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='notifications')

    def __repr__(self):
        return f"<Notification {self.title} for {self.user.username}>"