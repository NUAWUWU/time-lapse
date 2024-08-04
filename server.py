from flask import Flask, render_template, send_from_directory, request, redirect, url_for, flash
from markupsafe import Markup
import os
import re
import zipfile

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGES_DIR = os.path.join(BASE_DIR, 'images')
LOGS_DIR = os.path.join(BASE_DIR, 'logs')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/images')
def images():
    dates = []
    archived_dates = []
    for item in os.listdir(IMAGES_DIR):
        item_path = os.path.join(IMAGES_DIR, item)
        if os.path.isdir(item_path):
            dates.append(item)
        elif zipfile.is_zipfile(item_path):
            archived_dates.append(item.replace('.zip', ''))
    return render_template('images.html', dates=dates, archived_dates=archived_dates)

@app.route('/images/<date>', methods=['GET', 'POST'])
def view_images(date):
    date_dir = os.path.join(IMAGES_DIR, date)
    images = []

    if request.method == 'POST':
        if 'unzip' in request.form:
            zip_path = date_dir + '.zip'
            if zipfile.is_zipfile(zip_path):
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(date_dir)
                return redirect(url_for('view_images', date=date))

    if os.path.isdir(date_dir):
        images = os.listdir(date_dir)
    elif zipfile.is_zipfile(date_dir + '.zip'):
        images = zipfile.ZipFile(date_dir + '.zip', 'r').namelist()

    return render_template('view_images.html', date=date, images=images, archived=not os.path.isdir(date_dir))

@app.route('/logs')
def logs():
    logs = [f.replace('.log', '') for f in os.listdir(LOGS_DIR) if f.endswith('.log')]
    return render_template('logs.html', logs=logs)

@app.route('/log/<date>')
def log_detail(date):
    log_file = os.path.join(LOGS_DIR, f"{date}.log")
    with open(log_file, 'r') as file:
        log_content = file.read()

    log_content = re.sub(r'(\bINFO\b)', r'<span class="INFO">\1</span>', log_content)
    log_content = re.sub(r'(\bDEBUG\b)', r'<span class="DEBUG">\1</span>', log_content)
    log_content = re.sub(r'(\bERROR\b)', r'<span class="ERROR">\1</span>', log_content)
    log_content = re.sub(r'(\bCRITICAL\b)', r'<span class="CRITICAL">\1</span>', log_content)

    return render_template('log_detail.html', log_content=Markup(log_content), date=date)

@app.route('/updates')
def updates():
    return "Проверка обновлений (функция в разработке)"

@app.route('/images/<date>/<filename>')
def image_file(date, filename):
    date_dir = os.path.join(IMAGES_DIR, date)
    if os.path.isdir(date_dir):
        return send_from_directory(date_dir, filename)
    elif zipfile.is_zipfile(date_dir + '.zip'):
        with zipfile.ZipFile(date_dir + '.zip', 'r') as zip_ref:
            file_data = zip_ref.read(filename)
            response = app.response_class(file_data, mimetype='image/jpeg')
            return response

if __name__ == '__main__':
    app.run(debug=True)
