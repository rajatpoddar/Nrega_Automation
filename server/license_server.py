# license_server.py
# v1.6 with automatic database initialization.

from flask import Flask, request, jsonify, render_template, redirect, url_for, Response, flash
import sqlite3
import uuid
import csv
import io
import os
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'a-very-secret-key-for-flashing')

DATA_DIR = 'data'
DATABASE = os.path.join(DATA_DIR, 'licenses.db')

def init_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    with app.app_context():
        db = get_db()
        db.execute('''
            CREATE TABLE IF NOT EXISTS licenses (
                key TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                is_active INTEGER NOT NULL,
                key_type TEXT DEFAULT "paid",
                machine_id TEXT,
                is_blocked INTEGER DEFAULT 0
            )
        ''')
        db.commit()

def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

init_db()

# ... all routes and functions (check_auth, admin_panel, validate_key, etc.) remain the same ...
def check_auth(username, password):
    return username == os.environ.get('ADMIN_USERNAME', 'admin') and password == os.environ.get('ADMIN_PASSWORD', 'password')

def authenticate():
    return Response(
    'Could not verify your access level for that URL.\n'
    'You have to login with proper credentials', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

@app.route('/admin')
@requires_auth
def admin_panel():
    db = get_db()
    licenses = db.execute('SELECT * FROM licenses ORDER BY created_at DESC').fetchall()
    return render_template("admin.html", licenses=licenses)

@app.route('/generate', methods=['POST'])
@requires_auth
def generate_key():
    duration = request.form.get('duration', 'monthly')
    days = 365 if duration == 'yearly' else 30
    prefix = "NREGA-YEARLY" if duration == 'yearly' else "NREGA-PAID"
    db = get_db()
    new_key = "{}-{}".format(prefix, uuid.uuid4().hex[:8].upper())
    created_at = datetime.now()
    expires_at = created_at + timedelta(days=days)
    db.execute(
        'INSERT INTO licenses (key, created_at, expires_at, is_active, key_type, is_blocked, machine_id) VALUES (?, ?, ?, ?, ?, ?, ?)',
        (new_key, created_at.isoformat(), expires_at.isoformat(), 1, "paid", 0, None)
    )
    db.commit()
    return redirect(url_for('admin_panel'))

@app.route('/admin-action', methods=['POST'])
@requires_auth
def admin_action():
    key = request.form.get('key')
    action = request.form.get('action')
    db = get_db()
    if action == 'extend':
        license_data = db.execute('SELECT expires_at FROM licenses WHERE key = ?', (key,)).fetchone()
        if license_data:
            current_expiry = datetime.fromisoformat(license_data['expires_at'])
            new_expiry = current_expiry + timedelta(days=30)
            db.execute('UPDATE licenses SET expires_at = ? WHERE key = ?', (new_expiry.isoformat(), key))
    elif action == 'block':
        db.execute('UPDATE licenses SET is_blocked = 1 WHERE key = ?', (key,))
    elif action == 'unblock':
        db.execute('UPDATE licenses SET is_blocked = 0 WHERE key = ?', (key,))
    elif action == 'reset_machine':
        db.execute('UPDATE licenses SET machine_id = NULL WHERE key = ?', (key,))
        flash(f'Machine binding for key {key} has been reset.', 'success')
    db.commit()
    return redirect(url_for('admin_panel'))

@app.route('/export')
@requires_auth
def export_keys():
    db = get_db()
    cursor = db.execute('SELECT * FROM licenses')
    keys = cursor.fetchall()
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow([d[0] for d in cursor.description])
    cw.writerows(keys)
    output = si.getvalue()
    return Response(output, mimetype="text/csv", headers={"Content-disposition": "attachment; filename=licenses_backup.csv"})

@app.route('/import', methods=['POST'])
@requires_auth
def import_keys():
    file = request.files.get('file')
    if not file or file.filename == '':
        flash('No file selected for import.', 'error')
        return redirect(url_for('admin_panel'))
    if file and file.filename.endswith('.csv'):
        try:
            stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
            csv_input = csv.reader(stream)
            header = next(csv_input)
            db = get_db()
            for row in csv_input:
                if len(row) == 7:
                    db.execute('INSERT OR IGNORE INTO licenses (key, created_at, expires_at, is_active, key_type, machine_id, is_blocked) VALUES (?, ?, ?, ?, ?, ?, ?)', tuple(row))
            db.commit()
            flash('Successfully imported keys from CSV. Existing keys were ignored.', 'success')
        except Exception as e:
            flash(f'An error occurred during import: {e}', 'error')
    else:
        flash('Invalid file type. Please upload a CSV file.', 'error')
    return redirect(url_for('admin_panel'))

@app.route('/request-trial', methods=['POST'])
def request_trial():
    machine_id = request.json.get('machine_id')
    if not machine_id:
        return jsonify({"status": "error", "reason": "Machine ID is required."}), 400
    db = get_db()
    existing_trial = db.execute('SELECT key FROM licenses WHERE machine_id = ? AND key_type = ?', (machine_id, "trial")).fetchone()
    if existing_trial:
        return jsonify({"status": "error", "reason": "A free trial has already been claimed for this device."}), 403
    new_key = "NREGA-TRIAL-{}".format(uuid.uuid4().hex[:8].upper())
    created_at = datetime.now()
    expires_at = created_at + timedelta(days=30)
    db.execute(
        'INSERT INTO licenses (key, created_at, expires_at, is_active, key_type, machine_id, is_blocked) VALUES (?, ?, ?, ?, ?, ?, ?)',
        (new_key, created_at.isoformat(), expires_at.isoformat(), 1, "trial", machine_id, 0)
    )
    db.commit()
    return jsonify({"status": "success", "key": new_key, "expires_at": expires_at.isoformat()})

@app.route('/validate', methods=['POST'])
def validate_key():
    data = request.get_json()
    license_key = data.get('key')
    machine_id = data.get('machine_id')

    if not license_key or not machine_id:
        return jsonify({"status": "invalid", "reason": "License key and Machine ID are required."}), 400

    db = get_db()
    license_data = db.execute('SELECT * FROM licenses WHERE key = ?', (license_key,)).fetchone()

    if not license_data:
        return jsonify({"status": "invalid", "reason": "License key not found."}), 404
    if license_data['is_blocked']:
        return jsonify({"status": "invalid", "reason": "This license key has been blocked."}), 403
    if not license_data['is_active']:
        return jsonify({"status": "invalid", "reason": "License has been disabled."}), 403
    if datetime.now() > datetime.fromisoformat(license_data['expires_at']):
        return jsonify({"status": "invalid", "reason": "License has expired."}), 403

    stored_machine_id = license_data['machine_id']
    key_type = license_data['key_type']

    if key_type == 'paid' and stored_machine_id is None:
        db.execute('UPDATE licenses SET machine_id = ? WHERE key = ?', (machine_id, license_key))
        db.commit()
    elif stored_machine_id is not None and stored_machine_id != machine_id:
        return jsonify({"status": "invalid", "reason": "This license key is registered to another device."}), 403

    return jsonify({"status": "valid", "expires_at": license_data['expires_at']})


if __name__ == '__main__':
    # Updated: Development server now runs on port 8000 for consistency
    app.run(host='0.0.0.0', port=8000, debug=False)