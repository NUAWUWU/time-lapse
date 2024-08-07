from flask import Flask, render_template, send_from_directory, request, redirect, url_for
from markupsafe import Markup
from datetime import datetime
import os
import re
import zipfile
import asyncio
import threading
import logging
import psutil

from config import *
from timelapse import TimeLapse

app = Flask(__name__)

timelapse = TimeLapse(video_src=VIDEO_SRC,
                      save_dir=SAVE_DIR,
                      sender_email=SENDER_EMAIL,
                      smtp_password=SMTP_PASSWORD,
                      receiver_email=RECEIVER_EMAIL,
                      logs_dir=LOGS_DIR,
                      output_img_shape=OUTPUT_IMG_SHAPE,
                      delay_sec=DELAY_SEC)

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/images')
def images():
    dates = []
    archived_dates = []

    date_pattern = re.compile(r'(\d{2})-(\d{2})-(\d{4})')

    for item in os.listdir(timelapse.save_dir):
        item_path = os.path.join(timelapse.save_dir, item)
        match = date_pattern.match(item)

        if match:
            day, month, year = match.groups()
            item_date = datetime(int(year), int(month), int(day))
            
            if os.path.isdir(item_path):
                dates.append((item_date, item))
            elif zipfile.is_zipfile(item_path):
                archived_dates.append((item_date, item.replace('.zip', '')))

    dates.sort(key=lambda x: x[0])
    archived_dates.sort(key=lambda x: x[0])

    sorted_dates = [date[1] for date in dates]
    sorted_archived_dates = [archived_date[1] for archived_date in archived_dates]
    return render_template('images.html', dates=sorted_dates, archived_dates=sorted_archived_dates)

@app.route('/images/<date>', methods=['GET', 'POST'])
def view_images(date):
    date_dir = os.path.join(timelapse.save_dir, date)
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
    images.sort()
    return render_template('view_images.html', date=date, images=images, archived=not os.path.isdir(date_dir))

@app.route('/images/<date>/<filename>')
def image_file(date, filename):
    date_dir = os.path.join(timelapse.save_dir, date)
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
    log_files = [f for f in os.listdir(timelapse.logs_dir) if f.endswith('.log')]
    
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
    log_file = os.path.join(timelapse.logs_dir, f"{date}.log")
    with open(log_file, 'r') as file:
        log_content = file.read()

    log_content = re.sub(r'(\bINFO\b)', r'<span class="INFO">\1</span>', log_content)
    log_content = re.sub(r'(\bDEBUG\b)', r'<span class="DEBUG">\1</span>', log_content)
    log_content = re.sub(r'(\bERROR\b)', r'<span class="ERROR">\1</span>', log_content)
    log_content = re.sub(r'(\bWARNING\b)', r'<span class="WARNING">\1</span>', log_content)
    log_content = re.sub(r'(\bCRITICAL\b)', r'<span class="CRITICAL">\1</span>', log_content)

    return render_template('log_detail.html', log_content=Markup(log_content), date=date)


@app.route('/config', methods=['GET', 'POST'])
def config():
    if request.method == 'POST' and not timelapse.is_running:
        timelapse.delay_sec = int(request.form['DELAY_SEC'])
        timelapse.save_dir = request.form['SAVE_DIR']
        timelapse.logs_dir = request.form['LOGS_DIR']
        timelapse.video_src = request.form['VIDEO_SRC']
        timelapse.output_img_shape = tuple(map(int, request.form['OUTPUT_IMG_SHAPE'].split(','))) if request.form['OUTPUT_IMG_SHAPE'] else None
        timelapse.sender_email = request.form['SENDER_EMAIL']
        timelapse.receiver_email = request.form['RECEIVER_EMAIL']
        timelapse.smtp_password = request.form['SMTP_PASSWORD']

        new_config = {
            "DELAY_SEC": timelapse.delay_sec,
            "SAVE_DIR": timelapse.save_dir,
            "LOGS_DIR": timelapse.logs_dir,
            "VIDEO_SRC": timelapse.video_src,
            "OUTPUT_IMG_SHAPE": timelapse.output_img_shape,
            "SENDER_EMAIL": timelapse.sender_email,
            "RECEIVER_EMAIL": timelapse.receiver_email,
            "SMTP_PASSWORD": timelapse.smtp_password,
            "SERVER_PORT": int(request.form['SERVER_PORT']),
        }
        with open('config.py', 'w') as config_file:
            for key, value in new_config.items():
                config_file.write(f"{key} = {repr(value)}\n")
        return redirect(url_for('config'))

    current_config = {
        "DELAY_SEC": timelapse.delay_sec,
        "SAVE_DIR": timelapse.save_dir,
        "LOGS_DIR": timelapse.logs_dir,
        "VIDEO_SRC": timelapse.video_src,
        "OUTPUT_IMG_SHAPE": timelapse.output_img_shape,
        "SENDER_EMAIL": timelapse.sender_email,
        "RECEIVER_EMAIL": timelapse.receiver_email,
        "SMTP_PASSWORD": timelapse.smtp_password,
        "SERVER_PORT": SERVER_PORT,
    }

    memory_info = psutil.virtual_memory()
    memory_used_mb = memory_info.used / (1024 * 1024)
    memory_usage_percent = memory_info.percent
    cpu_usage = psutil.cpu_percent(interval=1)

    return render_template('config.html', is_running=timelapse.is_running,
                           config=current_config,
                           memory_used_mb=memory_used_mb,
                           memory_usage_percent=memory_usage_percent,
                           cpu_usage=cpu_usage)

@app.route('/toggle-timelapse', methods=['POST'])
def toggle_timelapse():
    if timelapse.is_running:
        timelapse.stop()
    else:
        thread = threading.Thread(target=asyncio.run, args=(timelapse.start(),))
        thread.start()
    return redirect(url_for('config'))


@app.route('/updates')
def updates():
    return "Проверка обновлений (функция в разработке)"


if __name__ == '__main__':
    logging.info(f'Start server: 0.0.0.0:{SERVER_PORT}')

    app.run(host='0.0.0.0', port=SERVER_PORT, debug=False)

    logging.critical('Shutdown server...')
    timelapse.stop()
    u = input('Would you like to send a daily report for today? (Y/N) ')
    if u.lower() == 'y':
        logging.info('Send daily report initialized')
        timelapse.send_daily_report()
    logging.critical('Shutdown complete.')