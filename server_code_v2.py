# server_v1.py
import os
import json
from flask import Flask, jsonify, request, render_template_string, redirect, url_for

app = Flask(__name__)

DB_FILE = 'patients_db.json'

def load_db():
    """Load the database from the JSON file."""
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_db(db):
    """Save the database to the JSON file."""
    with open(DB_FILE, 'w') as f:
        json.dump(db, f, indent=4)

def get_or_create_patient(pid):
    """Fetch existing patient from file or create data embedded with RTCI keys."""
    db = load_db()
    str_pid = str(pid)
    
    if str_pid not in db:
        db[str_pid] = {
            # Standard Application Metadata
            "patient_id": pid,
            "name": f"Patient {pid}",
            "admission_date": "2026-10-24",
            "primary_diagnosis": "Cardiac Observation",
            "blood_type": "O+" if pid % 2 == 0 else "A-",
            "allergies": ["Penicillin", "Latex"] if pid % 3 == 0 else ["None"],
            "medical_history": [
                "Hypertension (Diagnosed 2018)",
                "Type 2 Diabetes"
            ],
            "doctor_notes": "Patient stable. Monitor HR and SpO2 closely.",
            
            # Formatted exactly to match the parser expectations in praser.c
            "Patient_ID_[patient_id]": pid,
            "Age_[age]": 65 if pid % 2 == 0 else 30,
            "Chronic_Health_Points_[chronic_health_points]": 2 if pid % 2 == 0 else 0,
            "Temperature_in_Celsius_[temp_c]": 36.5,
            "Mean_Arterial_Pressure_[map_val]": 90.0,
            "Heart_Rate_[hr]": 75,
            "Respiratory_Rate_[rr]": 16,
            "Systolic_Blood_Pressure_[sbp]": 120,
            "Oxygen_Saturation_[spo2]": 98,
            "On_Supplemental_Oxygen_[on_oxygen]": 0,
            "Level_of_Consciousness_Alert_[is_alert]": 1,
            "Fraction_of_Inspired_Oxygen_[fio2]": 0.21,
            "Partial_Pressure_of_Arterial_Oxygen_[pao2]": 95.0,
            "Alveolar-Arterial_Oxygen_Gradient_[a_a_gradient]": 0.0,
            "Arterial_pH_[ph]": 7.4,
            "Serum_Sodium_[na]": 140.0,
            "Serum_Potassium_[k]": 4.0,
            "Serum_Creatinine_[cr]": 1.0,
            "Acute_Renal_Failure_Presence_[acute_renal_failure]": 0,
            "Hematocrit_[hct]": 45.0,
            "White_Blood_Cell_Count_[wbc]": 8.0,
            "Glasgow_Coma_Scale_[gcs]": 15
        }
        save_db(db)
    return db[str_pid]

def get_val(form_key, old_val, cast_type):
    """Safely extracts and casts a form value, falling back to old_val if blank/invalid."""
    val = request.form.get(form_key)
    if val is None or str(val).strip() == '':
        return old_val
    try:
        return cast_type(val)
    except ValueError:
        return old_val

# --- API ENDPOINT FOR PI 1 (C MONITOR) ---
@app.route('/patient/<int:pid>', methods=['GET'])
def api_get_patient_history(pid):
    """Returns the JSON data required by the QNX C monitor program."""
    patient = get_or_create_patient(pid)
    return jsonify(patient)

# --- WEB DASHBOARD ROUTES ---
@app.route('/', methods=['GET'])
def dashboard_index():
    """List all currently active/viewed patients."""
    for i in range(1, 101):
        get_or_create_patient(i)
    
    db = load_db()
    return render_template_string(INDEX_TEMPLATE, patients=db.values())

@app.route('/dashboard/patient/<int:pid>', methods=['GET', 'POST'])
def dashboard_edit_patient(pid):
    """View and edit patient details."""
    get_or_create_patient(pid)
    str_pid = str(pid)
    
    if request.method == 'POST':
        db = load_db()
        patient = db[str_pid]
        
        # Standard Info - Use .get() to prevent KeyErrors on legacy DB entries
        patient['name'] = request.form.get('name', patient.get('name', f"Patient {pid}"))
        patient['admission_date'] = request.form.get('admission_date', patient.get('admission_date', '2026-10-24'))
        patient['primary_diagnosis'] = request.form.get('primary_diagnosis', patient.get('primary_diagnosis', 'Cardiac Observation'))
        patient['blood_type'] = request.form.get('blood_type', patient.get('blood_type', 'O+'))
        patient['doctor_notes'] = request.form.get('doctor_notes', patient.get('doctor_notes', ''))
        
        allergies_raw = request.form.get('allergies', '')
        patient['allergies'] = [a.strip() for a in allergies_raw.split(',') if a.strip()]
        
        history_raw = request.form.get('medical_history', '')
        patient['medical_history'] = [h.strip() for h in history_raw.split('\n') if h.strip()]
        
        # RTCI & NEWS2 Config (Full 21 Parameters) - Use .get() with safe defaults
        patient['Age_[age]'] = get_val('age', patient.get('Age_[age]', 30), int)
        patient['Chronic_Health_Points_[chronic_health_points]'] = get_val('chronic_points', patient.get('Chronic_Health_Points_[chronic_health_points]', 0), int)
        patient['Temperature_in_Celsius_[temp_c]'] = get_val('temp_c', patient.get('Temperature_in_Celsius_[temp_c]', 36.5), float)
        patient['Mean_Arterial_Pressure_[map_val]'] = get_val('map_val', patient.get('Mean_Arterial_Pressure_[map_val]', 90.0), float)
        patient['Heart_Rate_[hr]'] = get_val('hr', patient.get('Heart_Rate_[hr]', 75), int)
        patient['Respiratory_Rate_[rr]'] = get_val('rr', patient.get('Respiratory_Rate_[rr]', 16), int)
        patient['Systolic_Blood_Pressure_[sbp]'] = get_val('sbp', patient.get('Systolic_Blood_Pressure_[sbp]', 120), int)
        patient['Oxygen_Saturation_[spo2]'] = get_val('spo2', patient.get('Oxygen_Saturation_[spo2]', 98), int)
        patient['On_Supplemental_Oxygen_[on_oxygen]'] = get_val('on_oxygen', patient.get('On_Supplemental_Oxygen_[on_oxygen]', 0), int)
        patient['Level_of_Consciousness_Alert_[is_alert]'] = get_val('is_alert', patient.get('Level_of_Consciousness_Alert_[is_alert]', 1), int)
        patient['Fraction_of_Inspired_Oxygen_[fio2]'] = get_val('fio2', patient.get('Fraction_of_Inspired_Oxygen_[fio2]', 0.21), float)
        patient['Partial_Pressure_of_Arterial_Oxygen_[pao2]'] = get_val('pao2', patient.get('Partial_Pressure_of_Arterial_Oxygen_[pao2]', 95.0), float)
        patient['Alveolar-Arterial_Oxygen_Gradient_[a_a_gradient]'] = get_val('a_a_gradient', patient.get('Alveolar-Arterial_Oxygen_Gradient_[a_a_gradient]', 0.0), float)
        patient['Arterial_pH_[ph]'] = get_val('ph', patient.get('Arterial_pH_[ph]', 7.4), float)
        patient['Serum_Sodium_[na]'] = get_val('na', patient.get('Serum_Sodium_[na]', 140.0), float)
        patient['Serum_Potassium_[k]'] = get_val('k', patient.get('Serum_Potassium_[k]', 4.0), float)
        patient['Serum_Creatinine_[cr]'] = get_val('cr', patient.get('Serum_Creatinine_[cr]', 1.0), float)
        patient['Acute_Renal_Failure_Presence_[acute_renal_failure]'] = get_val('acute_renal_failure', patient.get('Acute_Renal_Failure_Presence_[acute_renal_failure]', 0), int)
        patient['Hematocrit_[hct]'] = get_val('hct', patient.get('Hematocrit_[hct]', 45.0), float)
        patient['White_Blood_Cell_Count_[wbc]'] = get_val('wbc', patient.get('White_Blood_Cell_Count_[wbc]', 8.0), float)
        patient['Glasgow_Coma_Scale_[gcs]'] = get_val('gcs', patient.get('Glasgow_Coma_Scale_[gcs]', 15), int)
        
        save_db(db)
        return redirect(url_for('dashboard_index'))
        
    current_patient_data = load_db()[str_pid]
    return render_template_string(EDIT_TEMPLATE, patient=current_patient_data)

# --- HTML TEMPLATES ---
INDEX_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Hospital Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
<div class="container mt-5">
    <h2 class="mb-4">Patient History Dashboard</h2>
    <div class="card shadow-sm">
        <div class="card-body">
            <table class="table table-hover">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Name</th>
                        <th>Admission Date</th>
                        <th>Diagnosis</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    {% for p in patients|sort(attribute='patient_id') %}
                    <tr>
                        <td>{{ p.patient_id }}</td>
                        <td>{{ p.name }}</td>
                        <td>{{ p.admission_date }}</td>
                        <td>{{ p.primary_diagnosis }}</td>
                        <td><a href="/dashboard/patient/{{ p.patient_id }}" class="btn btn-sm btn-primary">Edit / View</a></td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</div>
</body>
</html>
"""

EDIT_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Edit Patient {{ patient.patient_id }}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
<div class="container mt-5 mb-5">
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h2>Editing: {{ patient.name }} (ID: {{ patient.patient_id }})</h2>
        <a href="/" class="btn btn-outline-secondary">Back to Dashboard</a>
    </div>
    
    <div class="card shadow-sm mb-4">
        <div class="card-body">
            <form method="POST" enctype="multipart/form-data">
                
                <h5 class="text-muted mb-3">General Information</h5>
                <div class="row mb-3">
                    <div class="col-md-6">
                        <label class="form-label">Full Name</label>
                        <input type="text" class="form-control" name="name" value="{{ patient.name }}" required>
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">Blood Type</label>
                        <input type="text" class="form-control" name="blood_type" value="{{ patient.blood_type }}">
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">Admission Date</label>
                        <input type="date" class="form-control" name="admission_date" value="{{ patient.admission_date }}">
                    </div>
                </div>

                <div class="mb-3">
                    <label class="form-label">Primary Diagnosis</label>
                    <input type="text" class="form-control" name="primary_diagnosis" value="{{ patient.primary_diagnosis }}">
                </div>

                <div class="mb-3">
                    <label class="form-label">Allergies (Comma separated)</label>
                    <input type="text" class="form-control" name="allergies" value="{{ patient.allergies|join(', ') }}">
                </div>

                <div class="mb-3">
                    <label class="form-label">Medical History (One entry per line)</label>
                    <textarea class="form-control" name="medical_history" rows="3">{{ patient.medical_history|join('\n') }}</textarea>
                </div>

                <div class="mb-3">
                    <label class="form-label">Doctor Notes</label>
                    <textarea class="form-control" name="doctor_notes" rows="3">{{ patient.doctor_notes }}</textarea>
                </div>

                <hr class="my-4">
                <h5 class="text-muted mb-3">RTCI Engine Parameters (APACHE II & NEWS2)</h5>
                
                <div class="row mb-3">
                    <div class="col-md-4">
                        <label class="form-label">Age</label>
                        <input type="number" class="form-control" name="age" value="{{ patient['Age_[age]'] }}">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">Chronic Health Points</label>
                        <input type="number" class="form-control" name="chronic_points" value="{{ patient['Chronic_Health_Points_[chronic_health_points]'] }}">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">Baseline Temperature (C)</label>
                        <input type="number" step="0.1" class="form-control" name="temp_c" value="{{ patient['Temperature_in_Celsius_[temp_c]'] }}">
                    </div>
                </div>

                <div class="row mb-3">
                    <div class="col-md-4">
                        <label class="form-label">Mean Arterial Pressure</label>
                        <input type="number" step="0.1" class="form-control" name="map_val" value="{{ patient['Mean_Arterial_Pressure_[map_val]'] }}">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">Heart Rate (Baseline)</label>
                        <input type="number" class="form-control" name="hr" value="{{ patient['Heart_Rate_[hr]'] }}">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">Respiratory Rate (Baseline)</label>
                        <input type="number" class="form-control" name="rr" value="{{ patient['Respiratory_Rate_[rr]'] }}">
                    </div>
                </div>

                <div class="row mb-3">
                    <div class="col-md-4">
                        <label class="form-label">Systolic BP (Baseline)</label>
                        <input type="number" class="form-control" name="sbp" value="{{ patient['Systolic_Blood_Pressure_[sbp]'] }}">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">SpO2 (%) (Baseline)</label>
                        <input type="number" class="form-control" name="spo2" value="{{ patient['Oxygen_Saturation_[spo2]'] }}">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">On Supplemental O2 (1=Yes, 0=No)</label>
                        <input type="number" min="0" max="1" class="form-control" name="on_oxygen" value="{{ patient['On_Supplemental_Oxygen_[on_oxygen]'] }}">
                    </div>
                </div>

                <div class="row mb-3">
                    <div class="col-md-4">
                        <label class="form-label">Alert / Conscious (1=Yes, 0=No)</label>
                        <input type="number" min="0" max="1" class="form-control" name="is_alert" value="{{ patient['Level_of_Consciousness_Alert_[is_alert]'] }}">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">FiO2</label>
                        <input type="number" step="0.01" class="form-control" name="fio2" value="{{ patient['Fraction_of_Inspired_Oxygen_[fio2]'] }}">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">PaO2</label>
                        <input type="number" step="0.1" class="form-control" name="pao2" value="{{ patient['Partial_Pressure_of_Arterial_Oxygen_[pao2]'] }}">
                    </div>
                </div>

                <div class="row mb-3">
                    <div class="col-md-4">
                        <label class="form-label">A-a Gradient</label>
                        <input type="number" step="0.1" class="form-control" name="a_a_gradient" value="{{ patient['Alveolar-Arterial_Oxygen_Gradient_[a_a_gradient]'] }}">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">Arterial pH</label>
                        <input type="number" step="0.01" class="form-control" name="ph" value="{{ patient['Arterial_pH_[ph]'] }}">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">Serum Sodium (Na)</label>
                        <input type="number" step="0.1" class="form-control" name="na" value="{{ patient['Serum_Sodium_[na]'] }}">
                    </div>
                </div>

                <div class="row mb-3">
                    <div class="col-md-4">
                        <label class="form-label">Serum Potassium (K)</label>
                        <input type="number" step="0.1" class="form-control" name="k" value="{{ patient['Serum_Potassium_[k]'] }}">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">Serum Creatinine (Cr)</label>
                        <input type="number" step="0.1" class="form-control" name="cr" value="{{ patient['Serum_Creatinine_[cr]'] }}">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">Acute Renal Failure (1=Yes, 0=No)</label>
                        <input type="number" min="0" max="1" class="form-control" name="acute_renal_failure" value="{{ patient['Acute_Renal_Failure_Presence_[acute_renal_failure]'] }}">
                    </div>
                </div>

                <div class="row mb-3">
                    <div class="col-md-4">
                        <label class="form-label">Hematocrit (Hct)</label>
                        <input type="number" step="0.1" class="form-control" name="hct" value="{{ patient['Hematocrit_[hct]'] }}">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">White Blood Cell Count</label>
                        <input type="number" step="0.1" class="form-control" name="wbc" value="{{ patient['White_Blood_Cell_Count_[wbc]'] }}">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">Glasgow Coma Scale</label>
                        <input type="number" min="3" max="15" class="form-control" name="gcs" value="{{ patient['Glasgow_Coma_Scale_[gcs]'] }}">
                    </div>
                </div>

                <button type="submit" class="btn btn-success w-100">Save Changes</button>
            </form>
        </div>
    </div>
</div>
</body>
</html>
"""

if __name__ == '__main__':
    print("Starting History Server & Dashboard on port 5000...")
    app.run(host='0.0.0.0', port=5000)