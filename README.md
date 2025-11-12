# 🚗 Parking Management System

A **Flask-based web application** for managing parking slots efficiently.  
This system allows **users** to park their vehicles by selecting an available slot, entering vehicle details, and receiving a **receipt** with entry and exit times.  
An **admin panel** helps manage parking slots, monitor users, and track parking activity.

---

## 🧩 Features

### 👤 User Features
- Register and login to their account  
- Park vehicle by:
  - Selecting an available slot  
  - Entering vehicle number  
  - Recording entry and exit time  
  - Generating a parking **receipt**
- View parking history and receipts  
- Access account section to manage profile  

### 🧑‍💼 Admin Features
- Admin login and dashboard access  
- View and manage all parking slots (available/occupied)  
- Manage users and vehicles  
- View all parking history and receipts  
- Park vehicles manually (if needed)  
- Access admin account section  

---

## 🏗️ Tech Stack

| Component | Technology Used |
|------------|----------------|
| **Frontend** | HTML, CSS, Bootstrap, Jinja2 Templates |
| **Backend** | Flask (Python) |
| **Database** | SQLite |
| **Language** | Python 3 |

---

## ⚙️ Installation & Setup

Follow these steps to run the project locally:

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/parking-management-system.git
cd parking-management-system

2. Create and activate a virtual environment
bash
Copy code
python -m venv venv
venv\Scripts\activate      # On Windows
# OR
source venv/bin/activate   # On Mac/Linux

3. Install dependencies
bash
Copy code
pip install -r requirements.txt

4. Initialize the database
bash
Copy code
python
>>> from app import init_db
>>> init_db()
>>> exit()

5. Run the Flask app
bash
Copy code
python app.py

6. Open in browser
Visit 👉 http://127.0.0.1:5000
```

## 🗄️ Database Structure (SQLite)
Tables:

**users** – Stores user credentials and profile info

**vehicles** – Vehicle number, entry time, exit time, user_id

**slots** – Parking slot details and status

**receipts** – Generated after successful parking session

## 📜 Example Receipt
Field	Description

Vehicle Number	GJ-01-AB-1234

Slot Code	A1

Entry Time	2025-11-10 10:30 AM

Exit Time	2025-11-10 12:45 PM

Total Time	2 hours 15 min

Amount	₹50

Status	Paid

## 🔐 User Roles
Role	Description

User	Can book, view receipts, and manage their profile

Admin	Can manage slots, view all bookings, and access dashboard

## 📁 Project Structure
pgsql
```bash
Parking-Management-System/
│
├── app.py
├── database.db
├── requirements.txt
├── schema.sql
│
├── static/
│   ├── css/
│   
├── templates/
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── park.html
│   ├── receipt.html
│   ├── account.html
│   ├── base.html
│   ├── forgot_password.html
│   └── reset_password.html
│
│
└── README.md
```

## 🧠 Future Enhancements
- Payment Gateway Integration 💳
- QR Code on Receipts 📱
- Real-Time Slot Availability 🅿️
- Email/SMS Notifications ✉️
- Multi-Level Parking Management 🏢

## 🧑‍💻 Author
- Developed by: Vruti Lad
- Framework: Flask
- Database: SQLite
- Language: Python
