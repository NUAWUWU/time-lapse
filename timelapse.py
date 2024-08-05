import cv2
import zipfile
import shutil
import os
import asyncio
import logging
from datetime import datetime
from utils.video_capture import VideoCaptureAsync
from utils.email_sender import send_email

class TimeLapse:
    def __init__(self, video_src, sender_email, smtp_password, receiver_email, save_dir='./images/', logs_dir='./logs/', output_img_shape=None, delay_sec=60):
        self.video_src = video_src
        self.save_dir = save_dir
        self.logs_dir = logs_dir
        self.output_img_shape = output_img_shape
        self.delay_sec = delay_sec
        self.video_cap = None
        self.sender_email = sender_email
        self.smtp_password = smtp_password
        self.receiver_email = receiver_email
        self.current_date = datetime.now().strftime("%d-%m-%Y")
        self.log_file_path = f'{logs_dir}log_{self.current_date}.log'
        self.is_running = False
        if not os.path.exists(self.logs_dir):
            os.makedirs(self.logs_dir)
        self.setup_logger(self.log_file_path, logging.DEBUG)

    def setup_logger(self, log_file_path, level=logging.DEBUG):
        logging.info(f'Logger save file has been changed, new file: {log_file_path}')
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        logging.basicConfig(filename=log_file_path,
                            level=level,
                            format='%(asctime)s - %(levelname)s - %(message)s')

    async def on_new_date_start(self, folder_path, output_zip_path, log_file_path):
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
                send_email(self.sender_email,
                        self.receiver_email,
                        subject=f'Daily Capture Summary: {image_count} Images Archived ({total_size_mb:.2f} MB)',
                        body=f"""
                        Image capture for the date {os.path.basename(folder_path)} has been successfully completed.
                        A total of {image_count} images, with a combined size of {total_size_mb:.2f} MB, have been archived and attached to this email.
                        Additionally, the log file for this day's activity is also attached. The log file contains detailed information about the capture process, including any errors or issues encountered.

                        Send by Automated System
                        """,
                        password=self.smtp_password,
                        file_paths=[output_zip_path, log_file_path])
                logging.info(f'Email sent to {self.receiver_email}.')
            except Exception as e:
                logging.error(f'Failed to send email: {e}')
        except Exception as e:
            logging.error(f'An error occurred during archiving or folder deletion: {e}')

    async def capture_images(self):
        while self.is_running:
            frame = self.video_cap.read()
            if frame is None:
                logging.warning('Frame is None')
                await asyncio.sleep(1)
                continue

            if self.output_img_shape:
                frame = cv2.resize(frame, self.output_img_shape)

            date_time = datetime.now()
            current_time = date_time.strftime("%H-%M-%S")
            current_date = date_time.strftime("%d-%m-%Y")

            new_dir_path = self.save_dir + current_date
            if not os.path.exists(new_dir_path):
                os.makedirs(new_dir_path)
                logging.info(f'Dir {new_dir_path} created')

            if current_date != self.current_date:
                old_dir_path = self.save_dir + self.current_date
                self.current_date = current_date

                logging.info(f'Ending the log for {old_dir_path}.')
                logging.shutdown()
                self.log_file_path = f'{self.logs_dir}log_{self.current_date}.log'
                self.setup_logger(self.log_file_path, logging.DEBUG)

                asyncio.create_task(self.on_new_date_start(old_dir_path, old_dir_path + '.zip', self.log_file_path))

            cv2.imwrite(f'{self.save_dir}{current_date}/{current_time}.jpg', frame)
            logging.info(f'{self.save_dir}{current_date}/{current_time}.jpg - Screenshot saved!')

            await asyncio.sleep(self.delay_sec)

    async def start(self):
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)
        if not os.path.exists(self.logs_dir):
            os.makedirs(self.logs_dir)

        self.is_running = True

        try:
            logging.info("Initializing video capture...")
            self.video_cap = VideoCaptureAsync(self.video_src).start()
            await self.capture_images()
        except RuntimeError as e:
            logging.error(e)
            self.stop()

    def stop(self):
        self.is_running = False
        if self.video_cap:
            self.video_cap.release()

    def send_daily_report(self):
        logs_folder = f'{self.logs_dir}log_{datetime.now().strftime("%d-%m-%Y")}.log'
        images_folder = self.save_dir + datetime.now().strftime("%d-%m-%Y")
        logging.shutdown()
        asyncio.run(self.on_new_date_start(images_folder,
                                           images_folder + '.zip',
                                           logs_folder))


if __name__ == "__main__":
    from config import *
    timelapse = TimeLapse(video_src=VIDEO_SRC,
                          sender_email=SENDER_EMAIL,
                          smtp_password=SMTP_PASSWORD,
                          receiver_email=RECEIVER_EMAIL,
                          save_dir=SAVE_DIR,
                          logs_dir=LOGS_DIR,
                          output_img_shape=OUTPUT_IMG_SHAPE,
                          delay_sec=DELAY_SEC)

    try:
        asyncio.run(timelapse.start())
    except KeyboardInterrupt:
        logging.critical('Shutdown initiated...')
        timelapse.stop()
        u = input('Would you like to send a daily report for today? (Y/N) ')
        if u.lower() == 'y':
            timelapse.send_daily_report()
        logging.critical('Shutdown complete.')