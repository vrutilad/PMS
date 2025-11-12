import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash, g, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"

DATABASE = "database.db"

# ------------------ DB HELPERS ------------------ #
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def execute_db(query, args=()):
    db = get_db()
    cur = db.execute(query, args)
    db.commit()
    return cur.lastrowid

# ------------------ INIT & SEED ------------------ #
def init_db():
    """Initialize database from schema.sql"""
    db = get_db()
    try:
        with app.open_resource("schema.sql", mode="r") as f:
            db.executescript(f.read())
        db.commit()
        print("âœ… Database initialized with schema.sql")
    except FileNotFoundError:
        print("âŒ schema.sql file not found! Creating tables manually...")
        # Create tables manually if schema.sql doesn't exist
        db.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'customer',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS slots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                status TEXT DEFAULT 'free',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS parkings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_number TEXT NOT NULL,
                slot TEXT NOT NULL,
                entry_time TIMESTAMP NOT NULL,
                exit_time TIMESTAMP,
                paid INTEGER DEFAULT 0,
                paid_amount REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        db.commit()
        print("âœ… Tables created manually")

def seed_data():
    """Insert default admin and slots if not exist"""
    admin = query_db("SELECT * FROM users WHERE username='admin'", one=True)
    if not admin:
        # Fixed admin password to admin123
        execute_db(
            "INSERT INTO users (username, email, password_hash, role) VALUES (?,?,?,?)",
            ("admin", "admin@example.com", generate_password_hash("admin123"), "admin")
        )
        print("âœ… Admin created (username=admin, password=admin123)")

    slots_exist = query_db("SELECT COUNT(*) as c FROM slots", one=True)["c"]
    if slots_exist == 0:
        # ðŸ”¥ FIX: Actually insert slots into the DATABASE
        for i in range(1, 11):
            for sub in ["A", "B"]:
                slot_code = f"{i}{sub}"
                execute_db("INSERT INTO slots (code, status) VALUES (?, 'free')", (slot_code,))
        print("âœ… 20 slots created in database")
        
# ------------------ AUTH HELPERS ------------------ #
def current_user():
    if "user_id" in session:
        return query_db("SELECT * FROM users WHERE id=?", (session["user_id"],), one=True)
    return None

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first", "warning")
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            flash("Admin access required", "danger")
            return redirect(url_for("park"))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/customer_dashboard')
def customer_dashboard():
    slots = Slot.query.all()
    free_slots = len([s for s in slots if s.status == 'free'])
    occupied_slots = len([s for s in slots if s.status == 'occupied'])
    
    return render_template('customer_dashboard.html', 
                         free_slots=free_slots,
                         occupied_slots=occupied_slots,
                         total_slots=len(slots))
    

# ------------------ ROUTES ------------------ #
@app.route("/")
def index():
    print(f"Index route accessed. Session: {dict(session)}")
    if "user_id" in session:
        # Redirect based on role
        if session.get("role") == "admin":
            return redirect(url_for("dashboard"))
        else:
            return redirect(url_for("park"))
    return redirect(url_for("login"))

# --------- Register --------- #
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        email = request.form["email"].strip()
        password = request.form["password"]
        role = request.form["role"]

        if not username or not email or not password:
            flash("All fields required", "danger")
            return redirect(url_for("register"))

        # Check if username is 'admin' - force admin role and password
        if username.lower() == 'admin':
            if password != 'admin123':
                flash("Admin password must be 'admin123'", "danger")
                return redirect(url_for("register"))
            role = 'admin'

        hashed = generate_password_hash(password)
        try:
            execute_db("INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
                       (username, email, hashed, role))
            flash("Registered successfully. Please login.", "success")
            return redirect(url_for("login"))
        except Exception:
            flash("Username or email already exists", "danger")
    return render_template("register.html")

# --------- Login --------- #
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username").strip()
        password = request.form.get("password")
        role = request.form.get("role")  # Get role from form

        if not username or not password or not role:
            flash("All fields required", "danger")
            return redirect(url_for("login"))

        user = query_db("SELECT * FROM users WHERE username=? AND role=?", (username, role), one=True)

        if user is None:
            flash(f"User '{username}' with role '{role}' not found", "danger")
            return redirect(url_for("login"))

        # Special check for admin
        if username.lower() == 'admin' and role == 'admin':
            if password != 'admin123':
                flash("Invalid admin password", "danger")
                return redirect(url_for("login"))
        else:
            if not check_password_hash(user["password_hash"], password):
                flash("Invalid password", "danger")
                return redirect(url_for("login"))

        # Success - set session
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["role"] = user["role"]
        flash("Login successful!", "success")

        # Redirect based on role
        if user["role"] == "admin":
            return redirect(url_for("dashboard"))
        else:
            return redirect(url_for("park"))

    return render_template("login.html")

# --------- Logout --------- #
@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out", "info")
    return redirect(url_for("login"))

# --------- Dashboard (Admin only) --------- #
@app.route("/dashboard")
@admin_required
def dashboard():
    total_slots = query_db("SELECT COUNT(*) AS c FROM slots", one=True)["c"]
    
    # Count occupied slots from in-memory data (more accurate for current state)
    occupied = len([s for s in slots if s["status"] == "occupied"])
    available = total_slots - occupied
    
    # Get revenue from database + in-memory payments
    db_revenue = query_db("SELECT SUM(paid_amount) as total FROM parkings WHERE paid=1", one=True)["total"] or 0
    
    # Add in-memory payments that might not be in database yet
    memory_revenue = sum(s.get("paid_amount", 0) for s in slots if s.get("paid", False))
    
    total_revenue = db_revenue + memory_revenue
    
    # Get recent payments for display
    recent_payments = []
    for slot in slots:
        if slot.get("paid", False) and slot.get("paid_amount", 0) > 0:
            recent_payments.append({
                "slot": slot["code"],
                "vehicle": slot.get("vehicle", "N/A"),
                "amount": slot.get("paid_amount", 0),
                "time": datetime.now().strftime("%H:%M")
            })

    stats = {
        "total_slots": total_slots, 
        "occupied": occupied, 
        "available": available, 
        "revenue": total_revenue,
        "recent_payments": recent_payments[-5:]  # Show last 5 payments
    }
    return render_template("dashboard.html", stats=stats)

# --------- Park Vehicle --------- #
# Initialize slots as a list of dictionaries for halves
slots = []
for i in range(1, 11):
    slots.append({"code": f"{i}A", "status": "free", "paid": False})
    slots.append({"code": f"{i}B", "status": "free", "paid": False})

@app.route("/park", methods=["GET", "POST"])
@login_required
def park():
    if request.method == "POST":
        vehicle_number = request.form["vehicle_number"].strip().upper()
        selected_slot = request.form.get("slot_code")
        entry_time_str = request.form.get("entry_time")
        exit_time_str = request.form.get("exit_time")

        if not vehicle_number:
            flash("Vehicle number required", "danger")
            return redirect(url_for("park"))

        if not selected_slot:
            flash("Please select a slot", "danger")
            return redirect(url_for("park"))

        if not entry_time_str:
            flash("Entry time required", "danger")
            return redirect(url_for("park"))

        # Convert entry and exit times to datetime objects
        try:
            entry_time = datetime.strptime(entry_time_str, "%Y-%m-%dT%H:%M")
        except ValueError:
            flash("Invalid entry time format", "danger")
            return redirect(url_for("park"))

        exit_time = None
        if exit_time_str:
            try:
                exit_time = datetime.strptime(exit_time_str, "%Y-%m-%dT%H:%M")
            except ValueError:
                flash("Invalid exit time format", "danger")
                return redirect(url_for("park"))

        # Check if the selected slot is free
        slot_obj = next((s for s in slots if s["code"] == selected_slot), None)
        if not slot_obj:
            flash("Invalid slot selected", "danger")
            return redirect(url_for("park"))
        if slot_obj["status"] == "occupied":
            flash(f"Slot {selected_slot} is already occupied", "warning")
            return redirect(url_for("park"))

        # ðŸ”¥ Save to database with datetime as TEXT (ISO format)
        try:
            # Convert datetime to ISO string format
            entry_iso = entry_time.strftime("%Y-%m-%d %H:%M:%S")
            exit_iso = exit_time.strftime("%Y-%m-%d %H:%M:%S") if exit_time else None
            
            parking_id = execute_db(
                "INSERT INTO parkings (vehicle_number, slot, user_id, entry_time, exit_time, paid, paid_amount) VALUES (?, ?, ?, ?, ?, 0, 0)",
                (vehicle_number, selected_slot, session.get("user_id"), entry_iso, exit_iso)
            )
            # Store the parking_id in the slot object
            slot_obj["parking_id"] = parking_id
        except Exception as e:
            flash(f"Database error: {e}", "danger")
            print(f"Error: {e}")
            return redirect(url_for("park"))

        # Assign the slot in memory
        slot_obj["status"] = "occupied"
        slot_obj["vehicle"] = vehicle_number
        slot_obj["entry_time"] = entry_time
        slot_obj["exit_time"] = exit_time
        slot_obj["paid"] = False
        
        flash(f"Vehicle {vehicle_number} assigned to slot {selected_slot}", "success")
        return redirect(url_for("park"))

    # Prepare occupied list for template
    occupied = [s["code"] for s in slots if s["status"] == "occupied"]
    return render_template("park.html", slots=slots, occupied=occupied)

# --------- Receipt --------- #

# --------- Updated Receipt Function --------- #
# --------- Updated Receipt Function (Final) --------- #
@app.route("/receipt_by_slot/<slot_code>")
@login_required
def receipt_by_slot(slot_code):
    """Display the parking receipt and allow printing as PDF."""
    db = get_db()

    # Try to get live (in-memory) slot first
    slot_obj = next((s for s in slots if s["code"] == slot_code), None)
    if slot_obj and slot_obj.get("status") == "occupied":
        entry_time = slot_obj.get("entry_time")
        exit_time = slot_obj.get("exit_time") or datetime.now()
        vehicle = slot_obj.get("vehicle")
        paid = slot_obj.get("paid", False)

        # Calculate parking duration and amount
        if entry_time:
            hours = max(1, int((exit_time - entry_time).total_seconds() // 3600))
        else:
            hours = 1
        amount = hours * 50

        # Update database with latest exit time and amount
        parking_id = slot_obj.get("parking_id")
        if parking_id:
            try:
                db.execute(
                    "UPDATE parkings SET exit_time=?, paid_amount=? WHERE id=?",
                    (exit_time.strftime("%Y-%m-%d %H:%M:%S"), amount, parking_id),
                )
                db.commit()
            except Exception as e:
                print(f"⚠️ Error updating receipt data: {e}")
    else:
        # Load last record for this slot from DB
        parking = query_db(
            "SELECT * FROM parkings WHERE slot=? ORDER BY id DESC LIMIT 1",
            (slot_code,),
            one=True
        )
        if not parking:
            flash("No receipt found for this slot.", "warning")
            return redirect(url_for("park"))

        entry_time = datetime.strptime(parking["entry_time"], "%Y-%m-%d %H:%M:%S") if parking["entry_time"] else None
        exit_time = datetime.strptime(parking["exit_time"], "%Y-%m-%d %H:%M:%S") if parking["exit_time"] else datetime.now()
        vehicle = parking["vehicle_number"]
        amount = parking["paid_amount"]
        paid = parking["paid"] == 1

        if entry_time:
            hours = max(1, int((exit_time - entry_time).total_seconds() // 3600))
        else:
            hours = 1

    # Prepare receipt dictionary for template
    receipt = {
        "vehicle_number": vehicle or "N/A",
        "slot": slot_code,
        "entry_time": entry_time.strftime("%Y-%m-%d %H:%M") if entry_time else "N/A",
        "exit_time": exit_time.strftime("%Y-%m-%d %H:%M") if exit_time else "N/A",
        "hours": hours,
        "amount": amount,
        "paid": paid,
    }

    return render_template("receipt.html", receipt=receipt)

# --------- Confirm Payment --------- #
def get_slot_id(slot_code):
    """Get database slot_id from slot code (e.g., '3B' -> id)"""
    slot = query_db("SELECT id FROM slots WHERE code=?", (slot_code,), one=True)
    return slot["id"] if slot else None

@app.route("/confirm_payment/<slot_code>", methods=['POST'])
@login_required
def confirm_payment(slot_code):
    """Confirm payment for a parking slot and free it."""
    db = get_db()
    
    try:
        # Find the slot in memory
        slot_obj = next((s for s in slots if s["code"] == slot_code), None)
        
        if slot_obj and slot_obj.get("status") == "occupied":
            entry_time = slot_obj.get("entry_time")
            exit_time = slot_obj.get("exit_time") or datetime.now()
            vehicle = slot_obj.get("vehicle", "Unknown")
            
            # Calculate hours and amount
            if entry_time:
                hours = max(1, int((exit_time - entry_time).total_seconds() // 3600))
            else:
                hours = 1
            
            amount = hours * 50
            
            # Update database - mark as paid
            parking_id = slot_obj.get("parking_id")
            if parking_id:
                exit_iso = exit_time.strftime("%Y-%m-%d %H:%M:%S")
                execute_db(
                    "UPDATE parkings SET exit_time=?, paid=1, paid_amount=? WHERE id=?",
                    (exit_iso, amount, parking_id)
                )
            else:
                # Create new parking record if parking_id doesn't exist
                entry_iso = entry_time.strftime("%Y-%m-%d %H:%M:%S") if entry_time else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                exit_iso = exit_time.strftime("%Y-%m-%d %H:%M:%S")
                parking_id = execute_db(
                    "INSERT INTO parkings (vehicle_number, slot, user_id, entry_time, exit_time, paid, paid_amount) VALUES (?, ?, ?, ?, ?, 1, ?)",
                    (vehicle, slot_code, session.get("user_id"), entry_iso, exit_iso, amount)
                )
            
            # FREE THE SLOT - reset all slot data
            slot_obj["status"] = "free"
            slot_obj["vehicle"] = None
            slot_obj["entry_time"] = None
            slot_obj["exit_time"] = None
            slot_obj["paid"] = False
            slot_obj["paid_amount"] = 0
            slot_obj["parking_id"] = None
            
            return jsonify({
                "success": True,
                "amount": amount,
                "slot": slot_code,
                "vehicle": vehicle,
                "message": f"Payment confirmed and slot {slot_code} is now free"
            })
        
        else:
            # Try to load from database if not in memory
            parking = query_db(
                "SELECT * FROM parkings WHERE slot=? ORDER BY id DESC LIMIT 1",
                (slot_code,),
                one=True
            )
            
            if parking and parking["paid"] == 0:
                entry_time = datetime.strptime(parking["entry_time"], "%Y-%m-%d %H:%M:%S") if parking["entry_time"] else None
                exit_time = datetime.strptime(parking["exit_time"], "%Y-%m-%d %H:%M:%S") if parking["exit_time"] else datetime.now()
                
                if entry_time:
                    hours = max(1, int((exit_time - entry_time).total_seconds() // 3600))
                else:
                    hours = 1
                
                amount = hours * 50
                
                # Update payment in database
                execute_db(
                    "UPDATE parkings SET paid=1, paid_amount=?, exit_time=? WHERE id=?",
                    (amount, exit_time.strftime("%Y-%m-%d %H:%M:%S"), parking["id"])
                )
                
                return jsonify({
                    "success": True,
                    "amount": amount,
                    "slot": slot_code,
                    "vehicle": parking["vehicle_number"],
                    "message": "Payment confirmed"
                })
            
            return jsonify({
                "success": False,
                "message": "Slot not found or already paid"
            })
    
    except Exception as e:
        print(f"⚠️ Error confirming payment: {e}")
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        }), 500
                    
# --------- API for real-time updates --------- #
@app.route("/api/dashboard_stats", methods=['GET'])
@admin_required
def api_dashboard_stats():
    total_slots = query_db("SELECT COUNT(*) AS c FROM slots", one=True)["c"]
    occupied = len([s for s in slots if s["status"] == "occupied"])
    available = total_slots - occupied
    
    # Get revenue from database + in-memory payments
    db_revenue = query_db("SELECT SUM(paid_amount) as total FROM parkings WHERE paid=1", one=True)["total"] or 0
    memory_revenue = sum(s.get("paid_amount", 0) for s in slots if s.get("paid", False))
    total_revenue = db_revenue + memory_revenue
    
    return jsonify({
        "total_slots": total_slots,
        "occupied": occupied,
        "available": available,
        "revenue": total_revenue
    })

# Add this after the confirm_payment route
@app.route("/account")
@login_required
def account():
    user = current_user()
    return render_template("account.html", user=user)

@app.route("/change_password", methods=["POST"])
@login_required
def change_password():
    user = current_user()
    old = request.form.get("old_password")
    newp = request.form.get("new_password")

    # Don't allow admin password change
    if user["username"].lower() == "admin":
        flash("Admin password cannot be changed", "danger")
        return redirect(url_for("account"))

    if not check_password_hash(user["password_hash"], old):
        flash("Old password incorrect", "danger")
        return redirect(url_for("account"))

    execute_db("UPDATE users SET password_hash=? WHERE id=?", (generate_password_hash(newp), user["id"]))
    flash("Password changed successfully", "success")
    return redirect(url_for("account"))

# --------- Forgot / Reset Password --------- #
@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email")
        user = query_db("SELECT * FROM users WHERE email=?", (email,), one=True)
        if user:
            flash("Password reset link generated (simulate here)", "info")
            return redirect(url_for("reset_password", user_id=user["id"]))
        else:
            flash("Email not found", "danger")
    return render_template("forgot_password.html")

@app.route("/reset_password/<int:user_id>", methods=["GET", "POST"])
def reset_password(user_id):
    user = query_db("SELECT * FROM users WHERE id=?", (user_id,), one=True)
    if not user:
        flash("Invalid user", "danger")
        return redirect(url_for("login"))

    # Don't allow admin password reset
    if user["username"].lower() == "admin":
        flash("Admin password cannot be reset", "danger")
        return redirect(url_for("login"))

    if request.method == "POST":
        newp = request.form.get("new_password")
        execute_db("UPDATE users SET password_hash=? WHERE id=?", (generate_password_hash(newp), user_id))
        flash("Password reset successful", "success")
        return redirect(url_for("login"))

    return render_template("reset_password.html")

# Add this route to test the receipt directly
@app.route("/test_receipt/<slot_code>")
def test_receipt(slot_code):
    slot_obj = next((s for s in slots if s["code"] == slot_code), None)
    if slot_obj:
        return f"<pre>Slot Object: {slot_obj}</pre>"
    return "Slot not found"

# ------------------ MAIN ------------------ #
if __name__ == "__main__":
    if not os.path.exists(DATABASE):
        print("âš¡ Creating new database...")
        open(DATABASE, "w").close()
        with app.app_context():
            init_db()
            seed_data()
    else:
        # ðŸ”¥ Run seed_data even if database exists (to add missing slots)
        with app.app_context():
            seed_data()
    
    app.run(debug=True)