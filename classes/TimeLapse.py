import os
import cv2
import asyncio

from datetime import datetime, timedelta

from classes.Email import Email
from classes.VideoCaptureAsync import VideoCaptureAsync
from utils.archive import archive_images, split_zip_file
from logger_config import logger


class TimeLapse:
    def __init__(self,
                 video_cap: VideoCaptureAsync,
                 email: Email = None,
                 max_size_mb=24,
                 save_dir='images/',
                 logs_dir='logs/',
                 output_img_shape=None,
                 delay_sec=60,
                 days_to_keep=7):
        self.video_cap = video_cap
        self.email = email
        self.max_size_mb = max_size_mb
        self.save_dir = save_dir
        self.send_logfile = os.path.join(self.save_dir, 'send_logs.txt')
        self.logs_dir = logs_dir
        self.output_img_shape = output_img_shape
        self.delay_sec = delay_sec
        self.days_to_keep = days_to_keep
        self.current_date = datetime.now().strftime("%Y_%m_%d")
        self.is_running = False

        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)
        if not os.path.exists(self.logs_dir):
            os.makedirs(self.logs_dir)

        self.entries = self.__read_entries()
        self.unprocessed = self.__find_unprocessed_items(self.entries)
        if self.unprocessed:
            logger.info(f'Found {len(self.unprocessed)} unprocessed items')
            for item in self.unprocessed:
                logger.debug(f'Found unprocessed item: {item}')
                asyncio.run(self.__process_item(item))


    async def start(self):
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
                current_date_path = self.save_dir + self.current_date
                asyncio.create_task(self.__process_item(current_date_path))
                self.current_date = current_date

            cv2.imwrite(f'{self.save_dir}{current_date}/{current_time}.jpg', frame)
            logger.info(f'{self.save_dir}{current_date}/{current_time}.jpg - Screenshot saved!')

            await asyncio.sleep(self.delay_sec)
    

    def __read_entries(self):
        # Чтение записей
        entries = []
        if os.path.exists(self.send_logfile):
            entries = []
            with open(self.send_logfile, 'r') as f:
                for line in f:
                    zip_path, log_path = line.strip().split('|')
                    entries.append((zip_path, log_path))
        logger.debug(f'Found {len(entries)} entries')

        # Удаление старых записей и файлов
        cutoff_date = datetime.now() - timedelta(days=self.days_to_keep)
        new_entries = []
        
        for zip_path, log_path in entries:
            try:
                filename = os.path.basename(zip_path)
                date_str = filename.split('.')[0]
                file_date = datetime.strptime(date_str, "%Y_%m_%d")
                
                if file_date > cutoff_date:
                    new_entries.append((zip_path, log_path))
                else:
                    logger.info(f'Delete old entries {file_date}')
                    if os.path.exists(zip_path):
                        os.remove(zip_path)
                    if os.path.exists(log_path):
                        os.remove(log_path)
            except Exception as e:
                logger.error(f'Error while delete {zip_path}: {e}')
                new_entries.append((zip_path, log_path))

        with open(self.send_logfile, 'w') as f:
            for zip_path, log_path in new_entries:
                f.write(f"{zip_path}|{log_path}\n")
            logger.debug(f'Write {len(new_entries)} entries')
        return new_entries



    def __find_unprocessed_items(self, processed_entries):
        processed_items = set()
        
        # Собираем все обработанные имена (без путей и расширений)
        for zip_path, _ in processed_entries:
            filename = os.path.basename(zip_path)
            item_name = filename.split('.')[0]  # Удаляем расширение .zip
            processed_items.add(item_name)
        
        today_str = datetime.now().strftime("%Y_%m_%d")
        unprocessed = []
        
        # Проверяем все элементы в базовой директории
        for item in os.listdir(self.save_dir):
            item_path = os.path.join(self.save_dir, item)
            if item == today_str:
                continue
            
            try:
                datetime.strptime(item.split('.')[0], "%Y_%m_%d")
            except ValueError:
                continue

            if (os.path.isdir(item_path) or item.endswith('.zip')) and item.split('.')[0] not in processed_items:
                unprocessed.append(item_path)
        return unprocessed


    async def __process_item(self, item):
        if item.endswith('.zip'):
            total_size_mb = os.path.getsize(item) / (1024 * 1024)
            image_count = '???'
            date = os.path.basename(item).split('.')[0]
            log_file_path = os.path.join(self.logs_dir, date + '.log')
        else:
            date = os.path.basename(item)
            log_file_path = os.path.join(self.logs_dir, date + '.log')
            total_size_mb, image_count, resp = archive_images(item, item + '.zip', delete_folder=True)
            if not resp:
                return
            item += '.zip'

        if not os.path.exists(log_file_path):
            logger.warning(f'Not found log file of {date}')
            log_file = None
        else:
            log_file = log_file_path

        if total_size_mb > self.max_size_mb:
            part_files = split_zip_file(item, max_size_mb=self.max_size_mb)

            if self.email:
                for i, part_file in enumerate(part_files, start=1):
                    subject = f"Part {i}/{len(part_files)}: Daily Capture {date}"
                    body = (
                        f"This is part {i} of {len(part_files)} of the archive for {date}.\n"
                        f"Part size: {os.path.getsize(part_file) / (1024 * 1024):.2f} MB\n\n"
                        f"Send by Automated System"
                    )
                    files_to_send = [part_file]
                    if i == 1 and log_file:
                        files_to_send.append(log_file)

                    success = self.email.send_file(files_to_send, subject, body)
                    if success:
                        os.remove(part_file)
                        logger.info(f"Sent and removed part {i}: {part_file}")
                    else:
                        logger.error(f"Failed to send part {i}: {part_file}")
                        return

        else:
            files_to_send = [item]
            if log_file:
                files_to_send.append(log_file)
            if self.email:
                subject = f'Daily Capture Summary: {image_count} Images Archived ({total_size_mb:.2f} MB)'
                body = (
                    f"Image capture for {date} has been completed.\n"
                    f"Total: {image_count} images, {total_size_mb:.2f} MB.\n"
                    f"Log file is attached.\n\nSend by Automated System"
                )
                success = self.email.send_file(files_to_send, subject, body)
                if not success:
                    return

        with open(self.send_logfile, 'a') as file:
            file.write(f"{item}|{log_file_path}\n")
