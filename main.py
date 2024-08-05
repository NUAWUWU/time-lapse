import cv2
import zipfile
import shutil
import os
import asyncio
import logging

from datetime import datetime
from utils.video_capture import VideoCaptureAsync
from utils.email_sender import send_email
from config import *

def setup_logger(log_file_path, level=logging.DEBUG):
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    logging.basicConfig(filename=log_file_path,
                        level=level,
                        format='%(asctime)s - %(levelname)s - %(message)s')


async def on_new_date_start(folder_path, output_zip_path, log_file_path):
    logging.info(f'Starting to archive images from {folder_path} to {output_zip_path}.')

    total_size = 0
    image_count = 0
    
    try:
        with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            logging.debug(f'Creating zip archive {output_zip_path}.')
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):   
                        file_path = os.path.join(root, file)
                        zipf.write(file_path, os.path.relpath(file_path, folder_path))
                        file_size = os.path.getsize(file_path)
                        total_size += file_size
                        image_count += 1
                        logging.debug(f'Added {file_path} to archive ({file_size / 1024:.2f} KB).')

        total_size_mb = total_size / (1024 * 1024)
        logging.info(f'Archive {output_zip_path} created successfully with {image_count} images, total size {total_size_mb:.2f} MB.')
        
        logging.debug(f'Deleting original folder {folder_path}.')
        shutil.rmtree(folder_path)
        logging.info(f'Folder {folder_path} deleted.')

        logging.info(f'Sending email to {RECEIVER_EMAIL}.')
        try:
            send_email(SENDER_EMAIL,
                    RECEIVER_EMAIL,
                    subject=f'Daily Capture Summary: {image_count} Images Archived ({total_size_mb:.2f} MB)',
                    body=f"""
                    Image capture for the date {os.path.basename(folder_path)} has been successfully completed.
                    A total of {image_count} images, with a combined size of {total_size_mb:.2f} MB, have been archived and attached to this email.
                    Additionally, the log file for this day's activity is also attached. The log file contains detailed information about the capture process, including any errors or issues encountered.

                    Send by Automated System
                    """,
                    password=SMTP_PASSWORD,
                    file_paths=[output_zip_path, log_file_path])
            logging.info(f'Email sent to {RECEIVER_EMAIL}.')
        except Exception as e:
            logging.error(f'Failed to send email: {e}')
    except Exception as e:
        logging.error(f'An error occurred during archiving or folder deletion: {e}')


async def main(video_cap):
    date_time = datetime.now()
    start_date = date_time.strftime("%d-%m-%Y")
    start_log_file_path = f'{LOGS_DIR}log_{start_date}.log'

    setup_logger(start_log_file_path, logging.DEBUG)
    logging.info('Logger initialized.')

    while True:
        frame = video_cap.read()
        if frame is None:
            logging.debug('Frame is None')
            await asyncio.sleep(1)
            continue

        if OUTPUT_IMG_SHAPE:
            frame = cv2.resize(frame, OUTPUT_IMG_SHAPE)

        date_time = datetime.now()
        current_time = date_time.strftime("%H-%M-%S")
        current_date = date_time.strftime("%d-%m-%Y")

        new_dir_path = SAVE_DIR + current_date
        if not os.path.exists(new_dir_path):
            os.makedirs(new_dir_path)
            logging.info(f'Dir {new_dir_path} created')

        if current_date != start_date:
            old_dir_path = SAVE_DIR + start_date
            start_date = current_date

            logging.info(f'Ending the log for {old_dir_path}.')
            logging.shutdown()
            new_log_file_path = f'{LOGS_DIR}log_{start_date}.log'
            setup_logger(new_log_file_path, logging.DEBUG)
            logging.info(f'Starting new log file: {new_log_file_path}')

            asyncio.create_task(on_new_date_start(old_dir_path, old_dir_path + '.zip', start_log_file_path))
            start_log_file_path = new_log_file_path

        cv2.imwrite(f'{SAVE_DIR}{current_date}/{current_time}.jpg', frame)
        logging.info(f'{SAVE_DIR}{current_date}/{current_time}.jpg - Screenshot saved!')

        await asyncio.sleep(DELAY_SEC)



if __name__ == "__main__":

    if not os.path.exists(SAVE_DIR):
        os.makedirs(SAVE_DIR)
    if not os.path.exists(LOGS_DIR):
        os.makedirs(LOGS_DIR)

    initial_log_file_path = f'{LOGS_DIR}log_{datetime.now().strftime("%d-%m-%Y")}.log'
    setup_logger(initial_log_file_path, logging.DEBUG)
    print(f'Logger setup complete. Logs save to {LOGS_DIR}')

    try:
        logging.info("Initializing video capture...")
        video_capture = VideoCaptureAsync(VIDEO_SRC).start()
    except RuntimeError as e:
        logging.error(e)
        exit()

    try:
        asyncio.run(main(video_capture))
    except KeyboardInterrupt:
        logging.critical('Shutdown initiated...')
    finally:
        video_capture.release()
        u = input('Would you like to send a daily report for today? (Y/N) ')
        if u.lower() == 'y':
            logs_folder = f'{LOGS_DIR}log_{datetime.now().strftime("%d-%m-%Y")}.log'
            images_folder = SAVE_DIR + datetime.now().strftime("%d-%m-%Y")
            logging.info(f'Ending the log for {logs_folder}.')
            logging.shutdown()
            asyncio.run(on_new_date_start(images_folder,
                                          images_folder + '.zip',
                                          f'{LOGS_DIR}log_{datetime.now().strftime("%d-%m-%Y")}.log'))
        logging.critical('Shutdown complete.')