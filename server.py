from flask import Flask, render_template, send_from_directory, request, redirect, url_for
from markupsafe import Markup
from datetime import datetime
import os
import re
import zipfile

from config import SAVE_DIR, LOGS_DIR

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FULL_SAVE_DIR = os.path.join(BASE_DIR, SAVE_DIR)
FULL_LOGS_DIR = os.path.join(BASE_DIR, LOGS_DIR)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/images')
def images():
    dates = []
    archived_dates = []

    date_pattern = re.compile(r'(\d{2})-(\d{2})-(\d{4})')

    for item in os.listdir(FULL_SAVE_DIR):
        item_path = os.path.join(FULL_SAVE_DIR, item)
        match = date_pattern.match(item)

        if match:
            day, month, year = match.groups()
            item_date = datetime(int(year), int(month), int(day))
            
            if os.path.isdir(item_path):
                dates.append((item_date, item))
            elif zipfile.is_zipfile(item_path):
                archived_dates.append((item_date, item.replace('.zip', '')))

    dates.sort(reverse=False, key=lambda x: x[0])
    archived_dates.sort(reverse=False, key=lambda x: x[0])
    sorted_dates = [date[1] for date in dates]
    sorted_archived_dates = [archived_date[1] for archived_date in archived_dates]
    return render_template('images.html', dates=sorted_dates, archived_dates=sorted_archived_dates)

@app.route('/images/<date>', methods=['GET', 'POST'])
def view_images(date):
    date_dir = os.path.join(FULL_SAVE_DIR, date)
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

@app.route('/images/<date>/<filename>')
def image_file(date, filename):
    date_dir = os.path.join(FULL_SAVE_DIR, date)
    if os.path.isdir(date_dir):
        return send_from_directory(date_dir, filename)
    elif zipfile.is_zipfile(date_dir + '.zip'):
        with zipfile.ZipFile(date_dir + '.zip', 'r') as zip_ref:
            file_data = zip_ref.read(filename)
            response = app.response_class(file_data, mimetype='image/jpeg')
            return response

@app.route('/logs')
def logs():
    logs = []
    log_files = [f for f in os.listdir(LOGS_DIR) if f.endswith('.log')]
    
    date_pattern = re.compile(r'log_(\d{2})-(\d{2})-(\d{4})\.log')
    
    for log_file in log_files:
        match = date_pattern.match(log_file)
        if match:
            day, month, year = match.groups()
            log_date = datetime(int(year), int(month), int(day))
            logs.append((log_date, log_file.replace('.log', '')))
    logs.sort(reverse=False, key=lambda x: x[0])
    log_names = [log[1] for log in logs]
    return render_template('logs.html', logs=log_names)

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

if __name__ == '__main__':
    app.run(debug=True)