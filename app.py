from flask import Flask, render_template, request, redirect, url_for, flash, session
import json
import os
from datetime import datetime
from dotenv import load_dotenv
import requests
from functools import wraps

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

# Variables d'environnement
VERIFY_TOKEN = os.getenv('VERIFY_TOKEN')
PAGE_ACCESS_TOKEN = os.getenv('PAGE_ACCESS_TOKEN')
FB_API_VERSION = os.getenv('FB_API_VERSION')
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')

app = Flask(__name__)
app.secret_key = os.urandom(24)

DATA_FILE = 'data.json'  # Fichier de données pour les questions/réponses
EMPLOIS_FILE = os.path.join(os.path.dirname(__file__), 'emplois_du_temps.json')  # Fichier pour les emplois du temps
COMPTES_FILE = os.path.join(os.path.dirname(__file__), 'comptes.json')  # Fichier pour les comptes utilisateurs

# Utils
def charger_donnees():
    """Charge les données du fichier JSON"""
    if not os.path.exists(DATA_FILE):
        print(f"File {DATA_FILE} does not exist")
        return []
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"Loaded data from {DATA_FILE}: {data}")
            return data
    except Exception as e:
        print(f"Error loading {DATA_FILE}: {e}")
        return []

def charger_emplois():
    """Charge les emplois du temps depuis le fichier JSON"""
    if not os.path.exists(EMPLOIS_FILE):
        print(f"File {EMPLOIS_FILE} does not exist")
        return []
    try:
        with open(EMPLOIS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"Loaded emplois from {EMPLOIS_FILE}: {data}")
            return data
    except json.JSONDecodeError as e:
        print(f"JSON decode error in {EMPLOIS_FILE}: {e}")
        return []
    except Exception as e:
        print(f"Error loading {EMPLOIS_FILE}: {e}")
        return []

def charger_comptes():
    """Charge les comptes utilisateurs"""
    if not os.path.exists(COMPTES_FILE):
        print(f"File {COMPTES_FILE} does not exist")
        return []
    try:
        with open(COMPTES_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"Loaded comptes from {COMPTES_FILE}: {data}")
            return data
    except Exception as e:
        print(f"Error loading {COMPTES_FILE}: {e}")
        return []

def sauvegarder_donnees(donnees, fichier):
    """Sauvegarde les données dans un fichier JSON"""
    try:
        with open(fichier, 'w', encoding='utf-8') as f:
            json.dump(donnees, f, indent=2, ensure_ascii=False)
        print(f"Data saved to {fichier}")
    except IOError as e:
        print(f"IO error saving to {fichier}: {e}")
        raise

def prochain_id(donnees):
    """Retourne le prochain ID disponible"""
    if not donnees:
        return 1
    try:
        ids = [int(item['id']) for item in donnees if str(item['id']).isdigit()]
        return max(ids, default=0) + 1
    except Exception as e:
        print(f"Error calculating next ID: {e}")
        return 1

def chercher_reponse(question, donnees):
    """Cherche la réponse à une question donnée dans les données"""
    try:
        if question.lower() == "aide":
            liste_questions = [item['question'] for item in donnees]
            reponse = "Voici les questions que vous pouvez poser :\n- " + "\n- ".join(liste_questions)
            return reponse

        for item in donnees:
            if item['question'].lower() == question.lower():
                return item['reponse']

        return "Je n'ai pas compris votre question. Pouvez-vous reformuler ou taper 'aide' ?"
    except Exception as e:
        print(f"Error in chercher_reponse: {e}")
        return "Erreur lors du traitement de la question."

def login_required(f):
    """Décorateur pour vérifier si l'utilisateur est connecté"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash('Veuillez vous connecter', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Routes publiques
@app.route('/')
def index():
    messages = [
        {'sender': 'Utilisateur', 'content': 'Bonjour !'},
        {'sender': 'Bot', 'content': 'Salut ! Comment puis-je t’aider ?'}
    ]
    return render_template('index.html', messages=messages)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            session['role'] = 'admin'
            flash('Connexion réussie', 'success')
            return redirect(url_for('admin'))
        else:
            flash('Identifiants invalides', 'danger')
    return render_template('login.html')

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('admin_logged_in', None)
    flash('Déconnecté avec succès', 'info')
    return redirect(url_for('login'))

# Interface Admin
@app.route('/admin')
@login_required
def admin():
    return render_template('admin_layout.html')

@app.route('/admin/questions')
@login_required
def admin_questions():
    donnees = charger_donnees()
    return render_template('admin_questions.html', donnees=donnees)

@app.route('/admin/comptes')
@login_required
def admin_comptes():
    comptes = charger_comptes()
    return render_template('admin_comptes.html', comptes=comptes)

@app.route('/admin_emplois')
@login_required
def admin_emplois():
    emplois = charger_emplois()
    return render_template('admin_emplois.html', emplois=emplois)

@app.route('/admin/etudiants')
@login_required
def admin_etudiants():
    emplois = charger_emplois()
    return render_template('admin_etudiants.html', emplois=emplois)

# CRUD Questions/Réponses
@app.route('/ajouter', methods=['POST'])
@login_required
def ajouter():
    try:
        question = request.form['question']
        reponse = request.form['reponse']
        print(f"Received form data: question={question}, reponse={reponse}")
        donnees = charger_donnees()
        print(f"Current data: {donnees}")
        nouvel_id = prochain_id(donnees)
        print(f"New ID: {nouvel_id}")
        donnees.append({'id': nouvel_id, 'question': question, 'reponse': reponse})
        sauvegarder_donnees(donnees, DATA_FILE)
        flash('Question ajoutée avec succès', 'success')
        return redirect(url_for('admin_questions'))
    except KeyError as e:
        print(f"Form error: Missing key {e}")
        flash(f"Erreur : Champ manquant ({e})", 'danger')
        return redirect(url_for('admin_questions'))
    except IOError as e:
        print(f"IO error saving to {DATA_FILE}: {e}")
        flash(f"Erreur : Impossible d'enregistrer les données ({e})", 'danger')
        return redirect(url_for('admin_questions'))
    except Exception as e:
        print(f"Unexpected error in ajouter: {e}")
        flash(f"Erreur inattendue : {e}", 'danger')
        return redirect(url_for('admin_questions'))

@app.route('/modifier/<int:id>', methods=['POST'])
@login_required
def modifier(id):
    try:
        question = request.form['question']
        reponse = request.form['reponse']
        print(f"Modifying ID {id}: question={question}, reponse={reponse}")
        donnees = charger_donnees()
        for item in donnees:
            if int(item['id']) == id:
                item['question'] = question
                item['reponse'] = reponse
                break
        sauvegarder_donnees(donnees, DATA_FILE)
        flash('Question modifiée avec succès', 'success')
        return redirect(url_for('admin_questions'))
    except Exception as e:
        print(f"Error in modifier: {e}")
        flash(f"Erreur lors de la modification : {e}", 'danger')
        return redirect(url_for('admin_questions'))

@app.route('/supprimer/<int:id>')
@login_required
def supprimer(id):
    try:
        print(f"Deleting ID {id}")
        donnees = charger_donnees()
        donnees = [item for item in donnees if int(item['id']) != id]
        sauvegarder_donnees(donnees, DATA_FILE)
        flash('Question supprimée avec succès', 'danger')
        return redirect(url_for('admin_questions'))
    except Exception as e:
        print(f"Error in supprimer: {e}")
        flash(f"Erreur lors de la suppression : {e}", 'danger')
        return redirect(url_for('admin_questions'))

# Gestion des emplois du temps
@app.route('/ajouter_emploi', methods=['POST'])
@login_required
def ajouter_emploi():
    try:
        matricule = request.form['matricule']
        filiere = request.form['filiere']
        annee = request.form['annee']
        emploi_du_temps = request.form['emploi_du_temps']
        mot_de_passe = request.form['mot_de_passe']
        print(f"Adding emploi: matricule={matricule}, filiere={filiere}")

        emplois = charger_emplois()
        nouvel_emploi = {
            'matricule': matricule,
            'filiere': filiere,
            'annee': annee,
            'emploi_du_temps': json.loads(emploi_du_temps),
            'mot_de_passe': mot_de_passe
        }
        emplois.append(nouvel_emploi)
        sauvegarder_donnees(emplois, EMPLOIS_FILE)
        flash('Emploi du temps ajouté avec succès', 'success')
        return redirect(url_for('admin_emplois'))
    except Exception as e:
        print(f"Error in ajouter_emploi: {e}")
        flash(f"Erreur lors de l'ajout de l'emploi : {e}", 'danger')
        return redirect(url_for('admin_emplois'))

@app.route('/modifier_emploi/<matricule>', methods=['POST'])
@login_required
def modifier_emploi(matricule):
    try:
        filiere = request.form['filiere']
        annee = request.form['annee']
        emploi_du_temps = request.form['emploi_du_temps']
        mot_de_passe = request.form['mot_de_passe']
        print(f"Modifying emploi: matricule={matricule}")

        emplois = charger_emplois()
        for emploi in emplois:
            if emploi['matricule'] == matricule:
                emploi['filiere'] = filiere
                emploi['annee'] = annee
                try:
                    emploi['emploi_du_temps'] = json.loads(emploi_du_temps)
                except json.JSONDecodeError:
                    flash('Erreur : le format de l’emploi du temps n’est pas un JSON valide.', 'danger')
                    return redirect(url_for('admin_emplois'))
                emploi['mot_de_passe'] = mot_de_passe
                break
        sauvegarder_donnees(emplois, EMPLOIS_FILE)
        flash('Emploi du temps modifié avec succès', 'success')
        return redirect(url_for('admin_emplois'))
    except Exception as e:
        print(f"Error in modifier_emploi: {e}")
        flash(f"Erreur lors de la modification : {e}", 'danger')
        return redirect(url_for('admin_emplois'))

@app.route('/supprimer_emploi/<matricule>')
@login_required
def supprimer_emploi(matricule):
    try:
        print(f"Deleting emploi: matricule={matricule}")
        emplois = charger_emplois()
        emplois = [emploi for emploi in emplois if emploi['matricule'] != matricule]
        sauvegarder_donnees(emplois, EMPLOIS_FILE)
        flash('Emploi du temps supprimé avec succès', 'danger')
        return redirect(url_for('admin_emplois'))
    except Exception as e:
        print(f"Error in supprimer_emploi: {e}")
        flash(f"Erreur lors de la suppression : {e}", 'danger')
        return redirect(url_for('admin_emplois'))

# Gestion des comptes utilisateurs
@app.route('/ajouter_compte', methods=['POST'])
@login_required
def ajouter_compte():
    try:
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        print(f"Adding compte: username={username}")
        comptes = charger_comptes()
        nouvel_compte = {
            'username': username,
            'password': password,
            'role': role,
            'status': 'active'
        }
        comptes.append(nouvel_compte)
        sauvegarder_donnees(comptes, COMPTES_FILE)
        flash('Compte ajouté avec succès', 'success')
        return redirect(url_for('admin_comptes'))
    except Exception as e:
        print(f"Error in ajouter_compte: {e}")
        flash(f"Erreur lors de l'ajout du compte : {e}", 'danger')
        return redirect(url_for('admin_comptes'))

@app.route('/modifier_compte/<username>', methods=['POST'])
@login_required
def modifier_compte(username):
    try:
        password = request.form['password']
        role = request.form['role']
        status = request.form['status']
        print(f"Modifying compte: username={username}")
        comptes = charger_comptes()
        for compte in comptes:
            if compte['username'] == username:
                compte['password'] = password
                compte['role'] = role
                compte['status'] = status
                break
        sauvegarder_donnees(comptes, COMPTES_FILE)
        flash('Compte modifié avec succès', 'success')
        return redirect(url_for('admin_comptes'))
    except Exception as e:
        print(f"Error in modifier_compte: {e}")
        flash(f"Erreur lors de la modification : {e}", 'danger')
        return redirect(url_for('admin_comptes'))

@app.route('/supprimer_compte/<username>')
@login_required
def supprimer_compte(username):
    try:
        print(f"Deleting compte: username={username}")
        comptes = charger_comptes()
        comptes = [compte for compte in comptes if compte['username'] != username]
        sauvegarder_donnees(comptes, COMPTES_FILE)
        flash('Compte supprimé avec succès', 'danger')
        return redirect(url_for('admin_comptes'))
    except Exception as e:
        print(f"Error in supprimer_compte: {e}")
        flash(f"Erreur lors de la suppression : {e}", 'danger')
        return redirect(url_for('admin_comptes'))

# Webhook Facebook Messenger
@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        try:
            received_token = request.args.get('hub.verify_token')
            print(f"Received verify_token: {received_token}, Expected: {VERIFY_TOKEN}")
            if request.args.get('hub.mode') == 'subscribe' and received_token == VERIFY_TOKEN:
                return request.args.get('hub.challenge')
            return 'Verification token invalide', 403
        except Exception as e:
            print(f"Error in webhook GET: {e}")
            return 'Error', 500

    elif request.method == 'POST':
        try:
            data = request.get_json()
            print(f"Received POST data: {data}")
            for entry in data['entry']:
                for message in entry['messaging']:
                    if 'message' in message:
                        user_id = message['sender']['id']
                        user_message = message['message'].get('text')
                        print(f"User ID: {user_id}, Message: {user_message}")
                        if "emploi du temps" in user_message.lower():
                            send_message(user_id, "Veuillez entrer votre matricule pour accéder à votre emploi du temps.")
                            session[user_id] = {'step': 'matricule'}
                            return 'OK', 200
                        if user_id in session and session[user_id].get('step') == 'matricule':
                            matricule = user_message
                            session[user_id]['matricule'] = matricule
                            send_message(user_id, "Veuillez maintenant entrer votre mot de passe.")
                            session[user_id]['step'] = 'mot_de_passe'
                            return 'OK', 200
                        if user_id in session and session[user_id].get('step') == 'mot_de_passe':
                            mot_de_passe = user_message
                            matricule = session[user_id].get('matricule')
                            emploi_du_temps = obtenir_emploi_du_temps(matricule, mot_de_passe)
                            if emploi_du_temps:
                                send_message(user_id, f"Voici votre emploi du temps : {emploi_du_temps}")
                            else:
                                send_message(user_id, "Désolé, matricule ou mot de passe incorrect.")
                            session.pop(user_id, None)
                            return 'OK', 200
                        response = chercher_reponse(user_message, charger_donnees())
                        print(f"Sending response to {user_id}: {response}")
                        send_message(user_id, response)
            return 'OK', 200
        except Exception as e:
            print(f"Error processing POST: {e}")
            return 'ERROR', 500

def obtenir_emploi_du_temps(matricule, mot_de_passe):
    """Récupère l'emploi du temps pour un matricule et mot de passe"""
    try:
        emplois = charger_emplois()
        for emploi in emplois:
            if emploi['matricule'] == matricule and emploi['mot_de_passe'] == mot_de_passe:
                return emploi['emploi_du_temps']
        return None
    except Exception as e:
        print(f"Error in obtenir_emploi_du_temps: {e}")
        return None

def send_message(recipient_id, message_text):
    """Envoie un message via l'API Facebook"""
    url = f'https://graph.facebook.com/{FB_API_VERSION}/me/messages?access_token={PAGE_ACCESS_TOKEN}'
    headers = {'Content-Type': 'application/json'}
    data = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text}
    }
    try:
        response = requests.post(url, json=data, headers=headers)
        print(f"API Response: {response.status_code}, {response.json()}")
        return response
    except Exception as e:
        print(f"Error sending message: {e}")
        return None

if __name__ == '__main__':
    app.run(debug=True, port=5001)
