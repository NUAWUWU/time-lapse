import os
import cv2
import asyncio

from datetime import datetime

from classes.Email import Email
from classes.VideoCaptureAsync import VideoCaptureAsync
from utils.archive import archive_images
from logger_config import logger


class TimeLapse:
    def __init__(self,
                 video_cap: VideoCaptureAsync,
                 email: Email = None,
                 save_dir='images/',
                 logs_dir='logs/',
                 output_img_shape=None,
                 delay_sec=60):
        self.video_cap = video_cap
        self.email = email
        self.save_dir = save_dir
        self.logs_dir = logs_dir
        self.output_img_shape = output_img_shape
        self.delay_sec = delay_sec
        self.current_date = datetime.now().strftime("%Y_%m_%d")
        self.is_running = False

    async def start(self):
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)
        if not os.path.exists(self.logs_dir):
            os.makedirs(self.logs_dir)

        self.is_running = True

        try:
            logger.info("Initializing video capture...")
            self.video_cap.start()
            await self._capture_images()
        except RuntimeError as e:
            logger.error(e)
            self.stop()

    def stop(self):
        self.is_running = False
        if self.video_cap:
            self.video_cap.release()

    def send_daily_report(self):
        current_date = datetime.now().strftime("%Y_%m_%d")
        asyncio.run(self.__on_new_date_start(self.save_dir + self.current_date, self.save_dir + self.current_date + '.zip', self.logs_dir + f'log_{current_date}'))

    async def _capture_images(self):
        while self.is_running:
            frame = self.video_cap.read()
            if frame is None:
                logger.warning('Frame is None')
                await asyncio.sleep(1)
                continue

            if self.output_img_shape:
                frame = cv2.resize(frame, self.output_img_shape)

            date_time = datetime.now()
            current_time = date_time.strftime("%H_%M_%S")
            current_date = date_time.strftime("%Y_%m_%d")

            new_dir_path = self.save_dir + current_date
            if not os.path.exists(new_dir_path):
                os.makedirs(new_dir_path)
                logger.debug(f'Dir {new_dir_path} created')

            if current_date != self.current_date:
                old_dir_path = self.save_dir + self.current_date
                asyncio.create_task(self.__on_new_date_start(old_dir_path, old_dir_path + '.zip', self.logs_dir + f'log_{self.current_date}.log'))
                self.current_date = current_date

            cv2.imwrite(f'{self.save_dir}{current_date}/{current_time}.jpg', frame)
            logger.info(f'{self.save_dir}{current_date}/{current_time}.jpg - Screenshot saved!')

            await asyncio.sleep(self.delay_sec)

    async def __on_new_date_start(self, folder_path, output_zip_path, log_file_path):
            total_size_mb, image_count = archive_images(folder_path, output_zip_path, delete_folder=True)

            subject=f'Daily Capture Summary: {image_count} Images Archived ({total_size_mb:.2f} MB)'
            body=f"""
            Image capture for the date {os.path.basename(folder_path)} has been successfully completed.
            A total of {image_count} images, with a combined size of {total_size_mb:.2f} MB, have been archived and attached to this email.
            Additionally, the log file for this day's activity is also attached. The log file contains detailed information about the capture process, including any errors or issues encountered.

            Send by Automated System
            """

            if self.email:
                self.email.send_file([output_zip_path, log_file_path], subject, body)
