"""
----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
Start of Imports and Setup
----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
"""

from flask import Flask, render_template, request, redirect, url_for, session, send_file
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
import json
import os

"""
----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
End of Imports and Setup
----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
"""


""" 
----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
 User Management Class
----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
[Summary] UserManager handles user registration, login, and management
[Details] It loads users from a JSON file, allows adding new users, and checks for existing emails.

"""

class UserManager:
    def __init__(self, user_file):
        self.user_file = user_file
        self.users = self.load_users()

    # This method Load users from the JSON file or return an empty list if the file doesn't exist.
    def load_users(self):
        """Load users from the JSON file, or return empty list if file doesn't exist."""
        if os.path.exists(self.user_file):
            with open(self.user_file, 'r') as f:
                return json.load(f)
        return []

    # This method writes the users list to the specified JSON file.
    def save_users(self):
        """Save the current users list to the JSON file."""
        with open(self.user_file, 'w') as f:
            json.dump(self.users, f)

    # This method adds a new user to the users list and saves it to the JSON file.
    def add_user(self, name, email, password, role='Owner'):
        """Add a new user and save."""
        self.users.append({
            'name': name,
            'email': email,
            'password': generate_password_hash(password),
            'role': role
        })
        self.save_users()

    # This method finds a user by email in the users list, It returns the user dictionary if found, or None if not found.
    def find_user(self, email):
        """Find a user by email."""
        return next((u for u in self.users if u['email'] == email), None)

    # This method checks if an email already exists in the users list, It returns True if the email is found, or False otherwise.
    def email_exists(self, email):
        """Check if an email is already registered."""
        return any(u['email'] == email for u in self.users)

"""
----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
AI Report Generator Class
----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
[Summary] AIReportGenerator generates a summary AI report from the filtered DataFrame.
[Details] Defines a static method to create a report based on the filtered DataFrame, summarizing key metrics like total trips, profit percentage, and financials.

"""

class AIReportGenerator:
    # This method generates a summary AI report from the filtered DataFrame.
    @staticmethod
    def generate(filtered_df):
        """Generate a summary AI report from the filtered DataFrame."""
        if filtered_df.empty:
            return "No data available for AI report."
        most_profitable_vehicle = filtered_df.groupby('Vehicle ID')['Net Profit'].sum().idxmax()
        top_routes = ", ".join(filtered_df['Route'].value_counts().head(2).index) if 'Route' in filtered_df.columns else "N/A"
        avg_profit_per_trip = round(filtered_df['Net Profit'].sum() / len(filtered_df), 2)
        rev = filtered_df['Freight Amount'].sum()
        exp = filtered_df['Total Trip Expense'].sum()
        profit = filtered_df['Net Profit'].sum()
        kms = filtered_df['Actual Distance (KM)'].sum()
        profit_pct = round((profit / rev * 100), 1) if rev else 0
        per_km = round(profit / kms, 2) if kms else 0
        return f"""
AI Report Highlights:

Total Trips: {len(filtered_df)}
On-going Trips: {filtered_df[filtered_df['Trip Status'] == 'Pending Closure'].shape[0]}
Completed Trips: {filtered_df[filtered_df['Trip Status'] == 'Completed'].shape[0]}
Profit Percentage: {profit_pct}%

Financials:
- Revenue: Rs{round(rev / 1e6, 2)}M
- Expense: Rs{round(exp / 1e6, 2)}M
- Profit: Rs{round(profit / 1e6, 2)}M
- KMs Travelled: {round(kms / 1e3, 1)}K
- Cost per KM: Rs{per_km}

AI Insights:
- Top Vehicle: {most_profitable_vehicle}
- Average Profit per Trip: Rs{avg_profit_per_trip}
- Top Routes: {top_routes}
"""

"""
----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
Main Application Class
----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
[Summary] TripAuditorApp is the main Flask application for managing trip audits.
[Details] It initializes the Flask app, loads datasets, manages user sessions, and defines all routes for the application.

"""

class TripAuditorApp:
    # This method initializes the Flask app, loads datasets, prepares vehicle and route lists, and sets up user management.
    def __init__(self):
        # Initialize Flask app
        self.app = Flask(__name__)
        self.app.config['UPLOAD_FOLDER'] = 'uploads'
        os.makedirs(self.app.config['UPLOAD_FOLDER'], exist_ok=True)
        self.app.secret_key = 'supersecret'

        # Load datasets
        self.fleet_file = 'fleet_50_entries.xlsx'
        self.closure_file = 'Trip_Closure_Sheet_Oct2024_Mar2025.xlsx'
        self.df = self.load_fleet_data()
        self.closure_df = self.load_closure_data()

        # Prepare vehicle and route lists
        self.vehicles = sorted(self.df['Vehicle ID'].dropna().unique())
        self.routes = sorted(self.df['Route'].dropna().unique()) if 'Route' in self.df.columns else []

        # User management
        self.user_manager = UserManager(os.path.join(os.getcwd(), 'users.json'))

        # Register all routes
        self.register_routes()

    # This method loads and preprocesses the fleet Excel data, converting date columns and cleaning up column names.
    def load_fleet_data(self):
        """Load and preprocess the fleet Excel data."""
        df = pd.read_excel(self.fleet_file)
        df.columns = df.columns.str.strip()
        df['Trip Date'] = pd.to_datetime(df['Trip Date'], errors='coerce')
        df['Day'] = df['Trip Date'].dt.day
        return df

    # This method loads and preprocesses the closure Excel data, converting date columns and cleaning up column names.
    def load_closure_data(self):
        """Load and preprocess the closure Excel data."""
        df = pd.read_excel(self.closure_file)
        df.columns = df.columns.str.strip()
        df['Trip Date'] = pd.to_datetime(df['Trip Date'], errors='coerce')
        df['Day'] = df['Trip Date'].dt.day
        return df

    # This method registers all Flask routes for the application, defining the logic for each route.
    def register_routes(self):
        """Define all Flask routes for the app."""

        @self.app.route('/')
        def home():
            # Redirect to signup page
            return redirect(url_for('signup'))

        @self.app.route('/signup', methods=['GET', 'POST'])
        def signup():
            # Handle user signup
            if request.method == 'POST':
                email = request.form['email']
                if self.user_manager.email_exists(email):
                    return render_template('signup.html', error="Email already registered!")
                self.user_manager.add_user(
                    name=request.form['fullname'],
                    email=email,
                    password=request.form['password']
                )
                return redirect(url_for('login'))
            return render_template('signup.html')

        @self.app.route('/login', methods=['GET', 'POST'])
        def login():
            # Handle user login
            if request.method == 'POST':
                user = self.user_manager.find_user(request.form['email'])
                if user and check_password_hash(user['password'], request.form['password']):
                    session['user'] = user
                    return redirect(url_for('dashboard'))
                return render_template('login.html', error="Invalid credentials.")
            return render_template('login.html')

        @self.app.route('/dashboard')
        def dashboard():
            # Main dashboard with filters and summary
            if 'user' not in session:
                return redirect(url_for('login'))
            vehicle = request.args.get('vehicle')
            route = request.args.get('route')
            filtered = self.df.copy()
            if vehicle:
                filtered = filtered[filtered['Vehicle ID'] == vehicle]
            if route:
                filtered = filtered[filtered['Route'] == route]

            total_trips = len(filtered)
            ongoing = filtered[filtered['Trip Status'] == 'Pending Closure'].shape[0]
            closed = filtered[filtered['Trip Status'] == 'Completed'].shape[0]
            flags = filtered[filtered['Trip Status'] == 'Under Audit'].shape[0]
            resolved = filtered[(filtered['Trip Status'] == 'Under Audit') & (filtered['POD Status'] == 'Yes')].shape[0]

            rev = filtered['Freight Amount'].sum()
            exp = filtered['Total Trip Expense'].sum()
            profit = filtered['Net Profit'].sum()
            kms = filtered['Actual Distance (KM)'].sum()

            rev_m = round(rev / 1e6, 2)
            exp_m = round(exp / 1e6, 2)
            profit_m = round(profit / 1e6, 2)
            kms_k = round(kms / 1e3, 1)
            per_km = round(profit / kms, 2) if kms else 0
            profit_pct = round((profit / rev) * 100, 1) if rev else 0

            daily = filtered.groupby('Day')['Trip ID'].count().reindex(range(1, 32), fill_value=0).tolist()
            audited = filtered[filtered['Trip Status'] == 'Under Audit'].groupby('Day')['Trip ID'].count().reindex(range(1, 32), fill_value=0).tolist()
            audit_pct = [round(a / b * 100, 1) if b else 0 for a, b in zip(audited, daily)]

            bar_labels = ['Revenue', 'Expense', 'Profit']
            bar_values = [float(rev_m), float(exp_m), float(profit_m)]
            ai_report = AIReportGenerator.generate(filtered)

            return render_template('dashboard.html',
                total_trips=total_trips, ongoing=ongoing, closed=closed,
                flags=flags, resolved=resolved, rev_m=rev_m, exp_m=exp_m,
                profit_m=profit_m, kms_k=kms_k, per_km=per_km, profit_pct=profit_pct,
                ai_report=ai_report, vehicles=self.vehicles, routes=self.routes,
                selected_vehicle=vehicle, selected_route=route,
                daily=daily, audited=audited, audit_pct=audit_pct,
                bar_labels=bar_labels, bar_values=bar_values)

        @self.app.route('/trip-generator', methods=['GET', 'POST'])
        def trip_generator():
            import sqlite3
            import os
            import fitz  # PyMuPDF
        
            UPLOAD_FOLDER = 'uploads'
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        
            def init_db():
                conn = sqlite3.connect('trips.db')
                c = conn.cursor()
                c.execute('''
                    CREATE TABLE IF NOT EXISTS trips (
                        trip_id TEXT,
                        trip_date TEXT,
                        vehicle_id TEXT,
                        driver_id TEXT,
                        planned_distance REAL,
                        advance_given REAL,
                        origin TEXT,
                        destination TEXT,
                        vehicle_type TEXT,
                        flags TEXT DEFAULT '',
                        total_freight REAL DEFAULT 0.0
                    )
                ''')
                conn.commit()
                conn.close()
        
            def parse_pdf(filepath):
                doc = fitz.open(filepath)
                text = ""
                for page in doc:
                    text += page.get_text()
        
                result = {}
                fields = [
                    'trip_id', 'trip_date', 'vehicle_id', 'driver_id', 'planned_distance',
                    'advance_given', 'origin', 'destination', 'vehicle_type', 'flags', 'total_freight'
                ]
                for field in fields:
                    for line in text.splitlines():
                        if field.replace("_", " ").lower() in line.lower():
                            try:
                                value = line.split(":")[1].strip()
                            except:
                                value = ""
                            result[field] = value
                            break
                    else:
                        result[field] = ""
        
                try:
                    result['total_freight'] = float(result.get('total_freight', 0) or 0)
                except:
                    result['total_freight'] = 0.0
        
                return result
        
            # Initialize DB once
            init_db()
        
            parsed_data = {}
        
            if request.method == 'POST':
                if 'pdf_file' in request.files and request.files['pdf_file'].filename != '':
                    pdf_file = request.files['pdf_file']
                    if pdf_file.filename.endswith('.pdf'):
                        filepath = os.path.join(UPLOAD_FOLDER, pdf_file.filename)
                        pdf_file.save(filepath)
                        parsed_data = parse_pdf(filepath)
                else:
                    fields = [
                        'trip_id', 'trip_date', 'vehicle_id', 'driver_id', 'planned_distance',
                        'advance_given', 'origin', 'destination', 'vehicle_type', 'flags', 'total_freight'
                    ]
                    data = []
                    for f in fields:
                        val = request.form.get(f, '')
                        if f == 'total_freight':
                            try:
                                val = float(val)
                            except:
                                val = 0.0
                        data.append(val)
        
                    conn = sqlite3.connect('trips.db')
                    c = conn.cursor()
                    c.execute(f"INSERT INTO trips ({','.join(fields)}) VALUES (?,?,?,?,?,?,?,?,?,?,?)", data)
                    conn.commit()
                    conn.close()
                    return redirect(url_for('trip_generator'))
        
            # Fetch summary statistics
            conn = sqlite3.connect('trips.db')
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM trips")
            trip_count = c.fetchone()[0]
        
            c.execute("SELECT COUNT(*) FROM trips WHERE flags IS NOT NULL AND flags != ''")
            total_flags = c.fetchone()[0]
        
            c.execute("SELECT SUM(total_freight) FROM trips")
            total_freight = c.fetchone()[0] or 0.0
            conn.close()
        
            return render_template(
                'trip_generator.html',
                parsed_data=parsed_data,
                trip_count=trip_count,
                total_flags=total_flags,
                total_freight=total_freight
            )

        @self.app.route('/trip-closure')
        def trip_closure():
            import sqlite3
            import os
        
            # Ensure DB and folders exist
            os.makedirs(self.app.config['UPLOAD_FOLDER'], exist_ok=True)
        
            def init_db():
                conn = sqlite3.connect('trips.db')
                c = conn.cursor()
                c.execute('''CREATE TABLE IF NOT EXISTS trips (
                    trip_id TEXT PRIMARY KEY,
                    trip_date TEXT,
                    vehicle_id TEXT,
                    driver_id TEXT,
                    planned_distance REAL,
                    advance_given REAL,
                    origin TEXT,
                    destination TEXT,
                    vehicle_type TEXT,
                    flags TEXT DEFAULT '',
                    total_freight REAL DEFAULT 0.0
                )''')
                c.execute('''CREATE TABLE IF NOT EXISTS trip_closure (
                    trip_id TEXT PRIMARY KEY,
                    actual_distance REAL,
                    actual_delivery_date TEXT,
                    trip_delay_reason TEXT,
                    fuel_quantity REAL,
                    fuel_rate REAL,
                    fuel_cost REAL,
                    toll_charges REAL,
                    food_expense REAL,
                    lodging_expense REAL,
                    miscellaneous_expense REAL,
                    maintenance_cost REAL,
                    loading_charges REAL,
                    unloading_charges REAL,
                    penalty_fine REAL,
                    total_trip_expense REAL,
                    freight_amount REAL,
                    incentives REAL,
                    net_profit REAL,
                    payment_mode TEXT,
                    pod_status TEXT,
                    trip_status TEXT
                )''')
                conn.commit()
                conn.close()
        
            init_db()
        
            fields = [
                ('actual_distance', 'Actual Distance (KM)', 'number'),
                ('actual_delivery_date', 'Actual Delivery Date', 'date'),
                ('trip_delay_reason', 'Trip Delay Reason', 'text'),
                ('fuel_quantity', 'Fuel Quantity (L)', 'number'),
                ('fuel_rate', 'Fuel Rate', 'number'),
                ('fuel_cost', 'Fuel Cost', 'number'),
                ('toll_charges', 'Toll Charges', 'number'),
                ('food_expense', 'Food Expense', 'number'),
                ('lodging_expense', 'Lodging Expense', 'number'),
                ('miscellaneous_expense', 'Miscellaneous Expense', 'number'),
                ('maintenance_cost', 'Maintenance Cost', 'number'),
                ('loading_charges', 'Loading Charges', 'number'),
                ('unloading_charges', 'Unloading Charges', 'number'),
                ('penalty_fine', 'Penalty/Fine', 'number'),
                ('total_trip_expense', 'Total Trip Expense', 'number'),
                ('freight_amount', 'Freight Amount', 'number'),
                ('incentives', 'Incentives', 'number'),
                ('net_profit', 'Net Profit', 'number'),
                ('payment_mode', 'Payment Mode', 'text'),
                ('pod_status', 'POD Status', 'text'),
                ('trip_status', 'Trip Status', 'text')
            ]
        
            parsed_data = {}
        
            if request.method == 'POST':
                trip_id = request.form.get('trip_id', '').strip()
                if not trip_id:
                    return "Trip ID is required", 400
        
                data = [trip_id]
                for f, label, ftype in fields:
                    val = request.form.get(f, '')
                    if ftype == 'number':
                        try:
                            val = float(val) if val != '' else 0.0
                        except:
                            val = 0.0
                    data.append(val)
        
                conn = sqlite3.connect('trips.db')
                c = conn.cursor()
                placeholders = ','.join('?' * len(data))
                c.execute(f'''
                    INSERT OR REPLACE INTO trip_closure (
                        trip_id, {','.join(f for f, _, _ in fields)}
                    ) VALUES ({placeholders})
                ''', data)
                conn.commit()
                conn.close()
                return redirect(url_for('trip_closure'))
        
            # GET method – fetch stats and closures
            conn = sqlite3.connect('trips.db')
            c = conn.cursor()
        
            c.execute("SELECT COUNT(*) FROM trip_closure")
            total_closures = c.fetchone()[0]
        
            c.execute("SELECT SUM(total_trip_expense), SUM(net_profit) FROM trip_closure")
            sums = c.fetchone()
            total_expense = sums[0] or 0.0
            total_profit = sums[1] or 0.0
        
            c.execute("SELECT * FROM trip_closure ORDER BY trip_id DESC")
            closures = c.fetchall()
            conn.close()
        
            return render_template(
                'trip_closer.html',
                parsed_data=parsed_data,
                total_closures=total_closures,
                total_expense=total_expense,
                total_profit=total_profit,
                closures=closures,
                fields=fields
            )

        @self.app.route('/trip-auditor')
        def trip_auditor():
            import pandas as pd
            from flask import request, render_template
        
            EXCEL_FILE = 'Trip_Closure_Sheet_Oct2024_Mar2025.xlsx'
        
            def load_data():
                df = pd.read_excel(EXCEL_FILE)
                df.columns = df.columns.str.strip().str.title()  # Clean column names
                return df
        
            df = load_data()
        
            trip_id = request.args.get('trip_id')  # If trip_id is passed, show details
        
            if trip_id:
                # Audit detail view
                if 'Trip Id' not in df.columns:
                    return "<h1 style='color:white'>No Trip Id column found in data.</h1>"
        
                trip = df[df['Trip Id'].astype(str) == str(trip_id)]
                if trip.empty:
                    return f"<h1 style='color:white'>Trip ID {trip_id} not found.</h1>"
        
                return render_template('trip_audit_detail.html', trip=trip.iloc[0].to_dict())
        
            # Dashboard summary view
            status_col = df['Status'] if 'Status' in df.columns else pd.Series(dtype=str)
            audited_col = df['Audited'] if 'Audited' in df.columns else pd.Series(dtype=str)
            flag_col = df['Flag'] if 'Flag' in df.columns else pd.Series(dtype=str)
            trip_id_col = df['Trip Id'] if 'Trip Id' in df.columns else pd.Series(dtype=str)
        
            total_trips = len(df)
            opened = len(df[status_col.str.lower() == 'open']) if not status_col.empty else 0
            audited = len(df[audited_col.str.lower() == 'yes']) if not audited_col.empty else 0
            closed = len(df[status_col.str.lower() == 'closed']) if not status_col.empty else 0
            audit_closed = len(df[
                (status_col.str.lower() == 'closed') & (audited_col.str.lower() == 'yes')
            ]) if not status_col.empty and not audited_col.empty else 0
            flags = len(df[flag_col.str.lower() == 'yes']) if not flag_col.empty else 0
        
            trip_data = df[['Trip Id']].dropna().to_dict('records') if 'Trip Id' in df.columns else []
        
            return render_template(
                'trip_auditor.html',
                total_trips=total_trips,
                opened=opened,
                audited=audited,
                closed=closed,
                audit_closed=audit_closed,
                flags=flags,
                trips=trip_data
            )


        @self.app.route('/trip-ongoing')
        def trip_ongoing():
            # Show ongoing trips
            data = self.df[self.df['Trip Status'] == 'Pending Closure'][['Trip ID', 'Vehicle ID', 'Trip Status']]
            return render_template('table_page.html', title="Ongoing Trips", table=data.to_html(classes='text-white', index=False))

        @self.app.route('/trip-stats')
        def trip_stats():
            # Show trip statistics by day
            days = list(range(1, 32))
            total = self.df.groupby('Day')['Trip ID'].count().reindex(days, fill_value=0).tolist()
            ongoing = self.df[self.df['Trip Status'] == 'Pending Closure'].groupby('Day')['Trip ID'].count().reindex(days, fill_value=0).tolist()
            closed = self.df[self.df['Trip Status'] == 'Completed'].groupby('Day')['Trip ID'].count().reindex(days, fill_value=0).tolist()

            total_json = json.dumps(total)
            ongoing_json = json.dumps(ongoing)
            closed_json = json.dumps(closed)

            total_sum = sum(total)
            ongoing_sum = sum(ongoing)
            closed_sum = sum(closed)

            return render_template('trip_stats.html',
                total_data=total_json, ongoing_data=ongoing_json, closed_data=closed_json,
                total_sum=total_sum, ongoing_sum=ongoing_sum, closed_sum=closed_sum)

        @self.app.route('/financial-dashboard')
        def financial_dashboard():
            # Show financial dashboard with recent 10 days data
            df_fin = self.closure_df.copy()
            recent_days = sorted(df_fin['Day'].dropna().unique())[-10:]
            day_labels = [f"Day {int(d)}" for d in recent_days]
            daily = df_fin[df_fin['Day'].isin(recent_days)]
            revenue_data = daily.groupby('Day')['Freight Amount'].sum().reindex(recent_days, fill_value=0).astype(int).tolist()
            expense_data = daily.groupby('Day')['Total Trip Expense'].sum().reindex(recent_days, fill_value=0).astype(int).tolist()
            profit_data = [r - e for r, e in zip(revenue_data, expense_data)]
            total_revenue = round(df_fin['Freight Amount'].sum() / 1e6, 2)
            total_profit = round(df_fin['Net Profit'].sum() / 1e6, 2)
            total_km = round(df_fin['Actual Distance (KM)'].sum() / 1e3, 1)
            per_km = round(df_fin['Net Profit'].sum() / df_fin['Actual Distance (KM)'].sum(), 2) if df_fin['Actual Distance (KM)'].sum() else 0

            return render_template('financial_dashboard.html',
                days=day_labels, revenue=revenue_data, expense=expense_data, profit=profit_data,
                total_revenue=total_revenue, total_profit=total_profit, total_km=total_km, per_km=per_km)

        @self.app.route('/logout')
        def logout():
            # Log out the current user
            session.pop('user', None)
            return redirect(url_for('login'))

        @self.app.route('/download-summary')
        def download_summary():
            # Download AI report summary as a text file
            filtered = self.df
            report = AIReportGenerator.generate(filtered)
            with open("AI_Report_Summary.txt", 'w', encoding='utf-8') as f:
                f.write(report)
            return send_file("AI_Report_Summary.txt", as_attachment=True)

    def run(self):
        """Run the Flask app."""
        self.app.run(host='0.0.0.0', port=7860, debug=True)

"""
----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
Entry Point
----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
This is the entry point for the application, where the TripAuditorApp is created and run.

"""

if __name__ == "__main__":
    # Create and run the OOP-based TripAuditor app
    app = TripAuditorApp()
    app.run()