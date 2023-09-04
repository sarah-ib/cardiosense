from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
import joblib
import pandas as pd
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, login_required, current_user, logout_user, LoginManager, UserMixin, AnonymousUserMixin
from datetime import datetime

app = Flask(__name__, static_folder='assets')
model = joblib.load('attack-model.pkl', mmap_mode=None)

scaler = joblib.load(open('scaler_diabets.pkl', 'rb'))
dmodel = joblib.load(open('diabets_model.pkl', 'rb'))


login_manager = LoginManager(app)
login_manager.login_view = 'login'

app.config['SECRET_KEY'] = 'mysecretkey123'
app.config['MYSQL_HOST'] = 'cardiosense.mysql.database.azure.com'
app.config['MYSQL_USER'] = 'admin01'
app.config['MYSQL_PASSWORD'] = 'Sarah109ha'
app.config['MYSQL_DB'] = 'heartsense'


mysql = MySQL(app)

class User(UserMixin):
    def __init__(self, user_id, email, password):
        self.id = user_id
        self.email = email
        self.password = password

@login_manager.user_loader
def load_user(user_id):
    # Your code to load a user based on user_id, e.g., query the database
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM user WHERE id = %s", (user_id,))
    user_data = cursor.fetchone()
    cursor.close()

    if user_data:
        user = User(user_id=user_data[0], email=user_data[1], password=user_data[2])  # Adjust this line based on your User class setup
        return user
    return None

# Handle anonymous users
@login_manager.request_loader
def load_anonymous_user(request):
    return AnonymousUserMixin()


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/services')
def services():
    return render_template('services.html')

@app.route('/news')
def news():
    return render_template('news.html')

@app.route('/diabets', methods=['GET', 'POST'])
def diabets():
    prediction = -1
    if request.method == 'POST':
        pregs = int(request.form.get('pregs'))
        gluc = int(request.form.get('gluc'))
        bp = int(request.form.get('bp'))
        skin = int(request.form.get('skin'))
        insulin = float(request.form.get('insulin'))
        bmi = float(request.form.get('bmi'))
        func = float(request.form.get('func'))
        age = int(request.form.get('age'))

        input_features = [[pregs, gluc, bp, skin, insulin, bmi, func, age]]
        # print(input_features)
        prediction = dmodel.predict(scaler.transform(input_features))
        # print(prediction)
        
    return render_template('diabets.html', prediction=prediction)



@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('login'))


@app.route('/predict', methods=['GET', 'POST'])
@login_required
def predict():
  if request.method == 'POST':
    age = float(request.form['age'])
    sex = float(request.form['sex'])
    cp = float(request.form['cp'])
    trestbps = float(request.form['trestbps'])
    chol = float(request.form['chol'])
    fbs = float(request.form['fbs'])
    restecg = float(request.form['restecg'])
    thalach = float(request.form['thalach'])
    exang = float(request.form['exang'])
    oldpeak = float(request.form['oldpeak'])
    slope = float(request.form['slope'])
    # ca = float(request.form['ca'])
    thal = float(request.form['thal'])
    userid = current_user.id
    feature_names = ['age', 'sex', 'cp', 'trestbps', 'chol', 'fbs', 'restecg', 'thalach', 'exang', 'oldpeak', 'slope', 'thal']
    user_input = [age, sex, cp, trestbps, chol, fbs, restecg, thalach, exang, oldpeak, slope, thal]
    input_data = pd.DataFrame([user_input], columns=feature_names)
   
    prediction = model.predict(input_data)[0]

    if prediction == 1:
        result = "High Risk"
    else:
        result = "Low Risk"
       # Get the current date and time
    current_datetime = datetime.now()
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO user_infos (userid, age, sex, cp, trestbps, chol, fbs, restecg, thalach, exang, oldpeak, slope, thal, result, date) VALUES ( %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (userid, age, sex, cp, trestbps, chol, fbs, restecg, thalach, exang, oldpeak, slope, thal, result, current_datetime))
    mysql.connection.commit()
    cur.close()

    # return render_template('predict.html', prediction=result)
    return redirect(url_for('dashboard'))
  
  return render_template('predict.html')



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM user WHERE email = %s", (email,))
        user_data = cursor.fetchone()
        cursor.close()
        
        if user_data and check_password_hash(user_data[2], password):
            user = User(user_id=user_data[0], email=user_data[1], password=user_data[2])
            session['user_id'] = user_data[0]
            login_user(user)  # Log in the user
            return redirect(url_for('dashboard'))
      
        else:
          flash('Invalid email or password', 'danger')
          error = "Invalid email or password. Please try again!"
          return render_template('login.html', error=error)

       
    return render_template('login.html')


@app.route('/dashboard')
@login_required
def dashboard():
    # Fetch user data from the database
  userid = current_user.id
  print(userid)
  if current_user.is_authenticated:
    userid = current_user.id
   
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, email, password FROM user WHERE id = %s", (userid,))
    user_data = cur.fetchall()
    cur.close()

    if len(user_data) == 0:
        return "User not found."

    user = User(user_data[0][0], user_data[0][1], user_data[0][2])
      # Fetch user data from the user_infos table
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM user_infos WHERE userid = %s ORDER BY date desc", (userid,))
    user_infos = cur.fetchall()
    cur.close()
   # Convert sex values to labels
    def get_sex_label(sex_value):
      return "Male" if sex_value == 1 else "Female"

# Convert cp values to labels
    def get_cp_label(cp_value):
      cp_labels = ["Typical Angina", "Atypical Angina", "Non-anginal Pain", "Asymptomatic"]
      return cp_labels[int(cp_value)]

# Convert fbs values to labels
    def get_fbs_label(fbs_value):
      return "True" if fbs_value == 1 else "False"

# Convert restecg values to labels
    def get_restecg_label(restecg_value):
         restecg_labels = ["Normal", "ST-T Wave Abnormality", "Probable"]
         return restecg_labels[int(restecg_value)]

# Convert exang values to labels
    def get_exang_label(exang_value):
      return "Yes" if exang_value == 1 else "No"

# Convert slope values to labels
    def get_slope_label(slope_value):
       slope_labels = ["Upsloping", "Flat", "Downsloping"]
       return slope_labels[int(slope_value)]

# Convert thal values to labels
    def get_thal_label(thal_value):
       thal_labels = ["Normal", "Fixed","Defect", "Reversible Defect"]
       return thal_labels[int(thal_value)]

# Convert result values to labels
    def get_result_label(result_value):
      return " Your assessment suggests a higher risk of cardiovascular issues. Please remember that this is not a diagnosis, but an opportunity to take proactive steps towards a healthier future" if result_value == "High Risk" else " Your heart health assessment indicates a low risk of cardiovascular issues. This is fantastic news and a testament to your efforts towards maintaining a healthy lifestyle. "

    transformed_user_infos = []
    for info in user_infos:
        transformed_info = list(info)
        transformed_info[3] = get_sex_label(info[3])
        transformed_info[14] = get_result_label(info[14])
        transformed_info[13] =  get_thal_label(info[13])
        transformed_info[12] =  get_slope_label(info[12])
        transformed_info[10] =  get_exang_label(info[10])
        transformed_info[7] =  get_fbs_label(info[7])
        transformed_info[4] =  get_cp_label(info[4])
        transformed_info[8] =  get_restecg_label(info[8])
        transformed_user_infos.append(transformed_info)

    return render_template('dashboard.html', user=current_user, user_infos=transformed_user_infos)



   # return render_template('dashboard.html', user=current_user, user_infos=user_infos)

    #return render_template('dashboard.html', user=user)
  return render_template('login.html')



@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO user (email, password) VALUES (%s, %s)", (email, password))
        mysql.connection.commit()
        cursor.close()

        # Retrieve the user's ID from the database
        cur = mysql.connection.cursor()
        cur.execute("SELECT id, email, password FROM user WHERE email = %s", (email,))
        user_data = cur.fetchone()
        cur.close()

        if user_data:
            user = User(user_id=user_data[0], email=user_data[1], password=user_data[2])
            login_user(user)  # Log in the user
            # Store the user_id in the session
            session['user_id'] = user_data[0]

            return redirect(url_for('dashboard'))

    return render_template('signup.html')




if __name__ == '__main__':
    app.run(debug=True)
