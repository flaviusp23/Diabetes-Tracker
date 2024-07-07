from flask import Flask, jsonify, request, render_template
from flask_pymongo import PyMongo
from bson.json_util import dumps
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
from datetime import datetime
from flask import redirect, url_for, session
from functools import wraps
import pandas as pd
from flask import Response
import private

app = Flask(__name__)

connection_string = private.connection_string
secret_key = private.secret_key

app.secret_key = secret_key
app.config['MONGO_URI'] = connection_string

try:
    mongo = PyMongo(app)
    print("conectat cu DB!")
except Exception as e:
    print("eroare la conectarea cu DB: {e}")


@app.route('/')
def home():
    return redirect(url_for('add_user'))


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('verify_user'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('verify_user'))


@app.route('/signup', methods=['GET', 'POST'])
def add_user():

    if request.method == 'POST':

        if request.content_type == 'application/json':
            _json = request.json
            _name = _json['name']
            _password = _json['password']
            _confirm_password = _json['confirm_password']
        else:
            _name = request.form['name']
            _password = request.form['password']
            _confirm_password = request.form['confirm_password']

        _hashedpassword = generate_password_hash(_password)

        data = {
            'name': _name, 
            'password': _hashedpassword
        }

        if _name and _password and _confirm_password:
            if _password != _confirm_password:
                return render_template('signup.html', error = 'Parolele nu coincid.', name = _name), 400

            if mongo.db.Users.find_one({'name': _name}):
                return render_template('signup.html', error = 'Numele de utilizator există deja', name = _name), 400

            id = mongo.db.Users.insert_one(data)

            resp = jsonify("User adaugat cu succes")
            resp.status_code = 200
            user_id = str(id)
            
            return redirect(url_for('verify_user'))
        else:
            return not_found()
    else : 
        return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])

def verify_user():
    if request.method == 'POST':
        if request.content_type == 'application/json':
            _json = request.json
            _name = _json['name']
            _password = _json['password']
        else:
            _name = request.form['name']
            _password = request.form['password']

        existing_user = mongo.db.Users.find_one({'name': _name})

        if existing_user : 
            if _name and _password:
                is_password_correct = check_password_hash(existing_user['password'], _password)

                if is_password_correct:
                    user_id = str(existing_user['_id'])
                    session['user_id'] = user_id
                    print(f"Login successful for user with ID: {user_id}")

                    return redirect(url_for('formular_user', id = user_id))
                else:
                    return render_template('login.html', error='Username sau parola gresite')
        else : 
            return render_template('login.html', error = 'Username inexistent')
    else : 
        return render_template('login.html')

@app.route('/users/<id>', methods = ['GET'])
@login_required
def user(id) : 
    user = mongo.db.Users.find_one({'_id' : ObjectId(id)})
    resp  = dumps(user)
    return resp

@app.route('/users/<id>/formular', methods=['GET', 'POST'])
@login_required
def formular_user(id):
    user = mongo.db.Users.find_one({'_id': ObjectId(id)})
    user_name = user.get('name', '')

    if request.method == 'POST':
        if request.content_type == 'application/json':
            _json = request.json
            _bloodsugar = _json['bloodsugar']
            _insulindose = _json['insulindose']
            _nrmese = _json['nr_mese']
            _activitate = _json['activitate']
        else:
            _bloodsugar = int(request.form['bloodsugar'])
            _insulindose = int(request.form['insulindose'])
            _nrmese = int(request.form['nr_mese'])
            _activitate = int(request.form['activitate'])

        data_form = {
            'user_id': id, 
            'bloodsugar': _bloodsugar, 
            'insulindose': _insulindose, 
            'nr_mese': _nrmese, 
            'activitate' : _activitate, 
            'timestamp': datetime.utcnow()
        }

        if data_form:
            id2 = mongo.db.Forms.insert_one(data_form)
            resp = jsonify("Formular completat")
            resp.status_code = 200
            return render_template('formular_complet.html', id = str(id), message = 'Formular completat cu succes',name=user_name)
        else:
            return not_found()
        
    else :     
        return render_template('formular.html', id=str(id), name = user_name)

@app.route('/users/<id>/dashboard', methods=['GET'])
@login_required
def dashboard(id):
    user = mongo.db.Users.find_one({'_id': ObjectId(id)})

    if user:
        user_name = user.get('name', '')

        forms_data = list(mongo.db.Forms.find({'user_id': id}, {'_id': 0, 'timestamp': 0, 'user_id': 0}))

        if forms_data:
            chart_data = {
                'labels': [form.get('timestamp', '') for form in forms_data],
                'bloodsugar': [form.get('bloodsugar', 0) for form in forms_data],
                'insulindose': [form.get('insulindose', 0) for form in forms_data],
                'nr_mese': [form.get('nr_mese', 0) for form in forms_data],
                'activitate': [form.get('activitate', 0) for form in forms_data],
            }

            return render_template('dashboard.html', id=str(id), name=user_name, chart_data=chart_data)
    return render_template('formular_complet.html', id = str(id), message = 'Completeaza formularul pentru a putea vizualiza statistici',name=user_name)

@app.route('/users/<id>/remindere', methods = ['GET', 'POST'])
@login_required
def user_form(id):

    user = mongo.db.Users.find_one({'_id': ObjectId(id)})
    user_name = user.get('name', '')

    return render_template('calendar.html', id = str(id), name=user_name)
        
@app.route('/users/<id>/analiza', methods = ['GET'])
@login_required
def analiza(id):
    user = mongo.db.Users.find_one({'_id': ObjectId(id)})
    user_name = user.get('name', '')

    forms_data = list(mongo.db.Forms.find({'user_id': id}, {'_id': 0, 'timestamp': 0, 'user_id': 0}))

    if forms_data:
        df = pd.DataFrame(forms_data)
        
        # Realizează analize statistice cu Pandas aici
        blood_sugar_stats = df['bloodsugar'].describe().round(2)
        insulindose_stats = df['insulindose'].describe().round(2)
        nr_mese_stats = df['nr_mese'].describe().round(2)
        activitate_stats = df['activitate'].describe().round(2)

        return render_template('analiza.html', id=str(id), name=user_name,
                               blood_sugar_stats=blood_sugar_stats,
                               insulindose_stats=insulindose_stats,
                               nr_mese_stats=nr_mese_stats,
                               activitate_stats=activitate_stats)
    else:
        return render_template('formular_complet.html', id = str(id), message = 'Completeaza formularul pentru a putea vizualiza statistici',name=user_name)
    
def string_to_array(input_string):
    try:
        result_array = [int(num) for num in input_string.split(',')]
        return result_array
    except ValueError:
        print("Invalid input format. Please provide a string of comma-separated integers.")
        return None

@app.route('/users/<id>/export', methods=['GET'])
@login_required
def export_user_data(id):
    forms_data = list(mongo.db.Forms.find({'user_id': id}, {'_id': 0, 'timestamp': 0, 'user_id': 0}))
    zi = 1

    if forms_data:
        csv_data = ""
                                                                                                                                                                                        
        for form in forms_data:
            # csv_data += f"ziua {zi} : {form['bloodsugar']} mg/dL, {form['insulindose']} doze, {form['nr_mese']} mese, {form['activitate']} minute de activitate\n"
            csv_data += f"{form['bloodsugar']}, {form['insulindose']}, {form['nr_mese']}, {form['activitate']}\n"
            zi = zi + 1
        return Response(csv_data, mimetype='text/csv', headers={'Content-Disposition': 'attachment;filename=date_user.csv'})

    return not_found()
        
@app.route('/users/<id>/import', methods=['POST'])
@login_required
def import_data(id):

    import_file = request.files['import_file']

    if import_file:
        content = import_file.read().decode('utf-8')
        lines = content.split('\n')[2:]

        json_data = []

        for line in lines:
            cleaned_line = ''.join(char for char in line if char.isnumeric() or char in [',', ':'])

            if ':' in cleaned_line:
                cleaned_line = cleaned_line.split(':', 1)[1].strip()
                data_array = string_to_array(cleaned_line)
                data_form = {
                    'user_id': id,
                    'bloodsugar': data_array[0],
                    'insulindose': data_array[1],
                    'nr_mese': data_array[2],
                    'activitate': data_array[3],
                    'timestamp': datetime.utcnow()
                }
                id2 = mongo.db.Forms.insert_one(data_form)
                json_data.append(data_form)

        response_data = {'data': json_data}
        return jsonify(response_data), 200
        
    else:
        return jsonify({'error': 'fisier invalid'}), 400
    
@app.route('/users', methods = ['GET'])
@login_required
def users() : 
    users = mongo.db.Users.find()
    resp = dumps(users)
    return resp
    
@app.errorhandler(404)
def not_found(error = None) : 

    message = { 
        'status' : 404,
        'message' : "user negasit " + request.url
    }

    resp = jsonify(message)
    resp.status_code = 404

    return resp

if __name__ == "__main__" : 
    app.run(debug = True)

