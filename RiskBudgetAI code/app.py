import csv
import os
import random
from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
from sklearn.linear_model import LinearRegression
import plotly.express as px


app = Flask(__name__)
app.secret_key = os.urandom(24)



# Charger les données et entraîner le modèle
data = pd.read_csv('project_budgets.csv')
X = data[['initial_budget', 'cotation_provisoire', 'cotation_definitive', 'cotation_adjudicataires']]
y = data['market_budget']
model = LinearRegression()
model.fit(X, y)

# Charger les utilisateurs depuis CSV
def load_users():
    users = []
    with open('users.csv', mode='r') as file:
        reader = csv.reader(file)
        header = next(reader)
        for row in reader:
            users.append(dict(zip(header, row)))
    return users

users = load_users()
last_id = max(int(user['id']) for user in users) if users else 0

admin_credentials = {
    'full_name': 'Ait Said Ali khaoula',
    'password': 'V9y^3Lj%t6n#',
    'email': 'khaoula.aitsaidali20@example.ma'
}

# Validation de l'utilisateur
def validate_user(user_id):
    return any(user['id'] == user_id for user in users)

# Fonction pour détecter le risque budgétaire
def detect_budget_risk(initial_budget, cotation_provisoire, cotation_definitive, cotation_adjudicataires, model):
    X_new = [[initial_budget, cotation_provisoire, cotation_definitive, cotation_adjudicataires]]
    predicted_market_budget = model.predict(X_new)[0]
    risk = abs(predicted_market_budget - initial_budget) / initial_budget
    return predicted_market_budget, float(risk)

# Interface admin
@app.route('/admin', methods=['GET', 'POST'])
def admin_interface():
    if 'logged_in' in session and session['logged_in']:
        if request.method == 'POST':
            action = request.form['action']
            if action == 'add':
                full_name = request.form['full_name']
                role = request.form['role']
                result = add_user(full_name, role)
                if isinstance(result, str):
                    return render_template('admin.html', users=users, error=result)
                return redirect(url_for('admin_interface'))
            elif action == 'delete':
                full_name = request.form['full_name']
                id = request.form['id']
                result = delete_user(full_name, id)
                if isinstance(result, str):
                    return render_template('admin.html', users=users, error=result)
                return redirect(url_for('admin_interface'))
        return render_template('admin.html', users=users)
    else:
        return render_template('login.html')

# Ajouter un utilisateur
def add_user(full_name, role):
    global last_id
    for user in users:
        if user['full_name'] == full_name:
            return "Utilisateur déjà existe dans la liste des utilisateurs"

    new_id = generate_unique_id()
    new_user = {'full_name': full_name, 'role': role, 'id': new_id}
    users.append(new_user)
    update_csv()
    return "Utilisateur est ajouté avec succès"

# Générer un ID unique
def generate_unique_id():
    global last_id
    new_id = str(random.randint(10000, 99999))
    while any(user['id'] == new_id for user in users):
        new_id = str(random.randint(10000, 99999))
    last_id += 1
    return new_id

# Supprimer un utilisateur
def delete_user(full_name, id):
    for user in users:
        if user['full_name'] == full_name and user['id'] == id:
            users.remove(user)
            update_csv()
            return "Utilisateur est supprimé avec succès"
    return "Utilisateur introuvable"

# Mettre à jour le fichier CSV des utilisateurs
def update_csv():
    with open('users.csv', mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=['full_name', 'role', 'id'])
        writer.writeheader()
        writer.writerows(users)

# Formulaire de connexion admin
@app.route('/admin_form', methods=['GET', 'POST'])
def admin_form():
    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        password = request.form['password']
        if (full_name == admin_credentials['full_name'] and
            email == admin_credentials['email'] and
            password == admin_credentials['password']):
            session['logged_in'] = True
            return redirect(url_for('admin_interface'))
        else:
            return render_template('access_denied.html')
    return render_template('admin_form.html')

# Déconnexion
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('index'))

# Page d'accueil avec formulaire de login
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        user_id = request.form['id']
        if validate_user(user_id):
            return redirect(url_for('budget_form', user_id=user_id))
        else:
            return render_template('access_denied.html')
    return render_template('home.html')

# Page de connexion
@app.route('/connexion', methods=['GET', 'POST'])
def connexion():
    if request.method == 'POST':
        user_id = request.form['id']
        if validate_user(user_id):
            return redirect(url_for('budget_form', user_id=user_id))
        else:
            return render_template('access_denied.html')
    return render_template('connexion.html')

# Formulaire de saisie de budget
@app.route('/budget_form', methods=['GET', 'POST'])
def budget_form():
    user_id = request.args.get('user_id')
    if request.method == 'POST':
        try:
            initial_budget = float(request.form['initial_budget'])
            cotation_provisoire = float(request.form['cotation_provisoire'])
            cotation_definitive = float(request.form['cotation_definitive'])
            cotation_adjudicataires = float(request.form['cotation_adjudicataires'])
        except ValueError:
            return "Entrée invalide. Veuillez saisir des valeurs numériques pour les budgets et les cotations."

        return redirect(url_for('prediction', user_id=user_id, initial_budget=initial_budget,
                                cotation_provisoire=cotation_provisoire,
                                cotation_definitive=cotation_definitive,
                                cotation_adjudicataires=cotation_adjudicataires))
    return render_template('budget_form.html', user_id=user_id)

# Prédiction du budget de marché
@app.route('/prediction', methods=['GET'])
def prediction():
    user_id = request.args.get('user_id')
    initial_budget = float(request.args.get('initial_budget'))
    cotation_provisoire = float(request.args.get('cotation_provisoire'))
    cotation_definitive = float(request.args.get('cotation_definitive'))
    cotation_adjudicataires = float(request.args.get('cotation_adjudicataires'))
    
    user_info = next(user for user in users if user['id'] == user_id)
    predicted_market_budget, risk = detect_budget_risk(initial_budget, cotation_provisoire, cotation_definitive, cotation_adjudicataires, model)
    
    return render_template('prediction.html', user_info=user_info, predicted_market_budget=int(predicted_market_budget), risk=round(risk, 5))

# Tableaux de bord pour visualisation
@app.route('/dashboard')
def dashboard():
    data = pd.read_csv('project_budgets.csv')
    
    # Histogramme du Budget Initial
    fig1 = px.histogram(data, x='initial_budget', title='Distribution du Budget Initial')
    fig1.update_layout(xaxis_title='Budget Initial', yaxis_title='Nombre de Projets')
    
    # Histogramme du Budget de Marché
    fig2 = px.histogram(data, x='market_budget', title='Distribution du Budget de Marché')
    fig2.update_layout(xaxis_title='Budget de Marché', yaxis_title='Nombre de Projets')
    
    # Nuage de points Budget Initial vs Budget de Marché
    fig3 = px.scatter(data, x='initial_budget', y='market_budget', title='Budget Initial Vs Budget de Marché')
    fig3.update_layout(xaxis_title='Budget Initial', yaxis_title='Budget de Marché')
    
    # Boîte à moustaches des Cotations des Projets
    fig4 = px.box(data[['cotation_provisoire', 'cotation_definitive', 'cotation_adjudicataires']], 
                  title='Comparaison des Cotations des Projets')
    fig4.update_layout(xaxis_title='Type de Cotation', yaxis_title='Montant')
    
    # Barres des Budgets Initiaux et de Marché par Projet
    fig5 = px.bar(data, x='project_name', y=['initial_budget', 'market_budget'], 
                  title='Budgets Initiaux et de Marché par Projet')
    fig5.update_layout(xaxis_title='Nom du Projet', yaxis_title='Montant', legend_title='Type de Budget')
    fig5.for_each_trace(lambda t: t.update(name=t.name.replace("variable", "Type de Budget")))

    # Heatmap de Corrélation
    corr_matrix = data[['initial_budget', 'market_budget', 'cotation_provisoire', 'cotation_definitive', 'cotation_adjudicataires']].corr()
    fig6 = px.imshow(corr_matrix, text_auto=True, title='Heatmap de Corrélation')
    fig6.update_layout(xaxis_title='Variables', yaxis_title='Variables')
    
    # Scatter Matrix
    fig7 = px.scatter_matrix(data, dimensions=['initial_budget', 'market_budget', 'cotation_provisoire', 'cotation_definitive', 'cotation_adjudicataires'],
                             title='Matrice de Nuages de Points', width=1000, height=800)
    fig7.update_traces(marker=dict(size=3))
    fig7.update_layout(font=dict(size=10))
    
    # Line Plot de l'évolution des Budgets par Projet
    fig8 = px.line(data, x=data.index, y=['initial_budget', 'market_budget'], color='project_name', 
                   title='Évolution des Budgets par Projet', width=1000, height=600)
    fig8.update_layout(xaxis_title='Indice', yaxis_title='Budget', legend_title='Projet')
    fig8.update_traces(mode='lines+markers')
    
    graphs = {
        'Distribution du Budget Initial': fig1.to_html(full_html=False),
        'Distribution du Budget de Marché': fig2.to_html(full_html=False),
        'Budget Initial Vs Budget de Marché': fig3.to_html(full_html=False),
        'Comparaison des Cotations des Projets': fig4.to_html(full_html=False),
        'Budgets Initiaux et de Marché par Projet': fig5.to_html(full_html=False),
        'Heatmap de Corrélation': fig6.to_html(full_html=False),
        'Matrice de Nuages de Points': fig7.to_html(full_html=False),
        'Évolution des Budgets par Projet': fig8.to_html(full_html=False)
    }
    
    return render_template('dashboard.html', graphs=graphs)


# Fonction d'envoi des messages clients
@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']  # Assurez-vous que le nom du champ est 'email'
        subject = request.form['subject']
        message = request.form['message']
        
        # Vérifier l'existence de `client_messages.csv`, sinon le créer avec les en-têtes
        file_exists = os.path.isfile('client_messages.csv')
        with open('client_messages.csv', mode='a', newline='') as file:
            fieldnames = ['id', 'full_name', 'email', 'subject', 'message']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            new_id = 1
            if file_exists:
                with open('client_messages.csv', mode='r') as read_file:
                    reader = csv.DictReader(read_file)
                    rows = list(reader)
                    if rows:
                        last_row = rows[-1]
                        new_id = int(last_row['id']) + 1
            writer.writerow({'id': new_id, 'full_name': full_name, 'email': email, 'subject': subject, 'message': message})
        
        return redirect(url_for('contact_confirmation'))
    return render_template('contact.html')

@app.route('/contact_confirmation')
def contact_confirmation():
    return render_template('contact_confirmation.html', message="Votre message a été envoyé avec succès !")


if __name__ == '__main__':
    app.run(debug=True)
