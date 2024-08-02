import cv2
import time
import zipfile
import logging
import threading
import shutil
import os
import asyncio

from datetime import datetime


class VideoCaptureAsync:
    def __init__(self, src):
        self.src = src
        self.cap = cv2.VideoCapture(self.src)
        if not self.cap.isOpened():
            raise RuntimeError(f"Cam {self.src} not found")
        self.frame = None
        self.stop_event = threading.Event()
        self.thread = None

    def start(self):
        if self.thread is None:
            self.thread = threading.Thread(target=self.update, args=())
            self.thread.start()
        return self

    def update(self):
        while not self.stop_event.is_set():
            if not self.cap.isOpened():
                logging.warning(f'Camera {self.src} lost connection. Trying to reconnect in 10 seconds...')
                time.sleep(10)
                self.cap.open(self.src)
                continue
            ret, frame = self.cap.read()
            if not ret:
                logging.warning(f'Failed to read frame from camera {self.src}. Reconnecting in 10 seconds...')
                self.cap.release()
                time.sleep(10)
                self.cap.open(self.src)
                continue
            self.frame = frame

    def read(self):
        return self.frame

    def release(self):
        self.stop_event.set()
        if self.thread is not None:
            self.thread.join()  # Ensure the thread has finished execution
        self.cap.release()
        self.thread = None


def compress_images_to_zip(folder_path, output_zip_path):
    with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    file_path = os.path.join(root, file)
                    zipf.write(file_path, os.path.relpath(file_path, folder_path))


async def main(video_cap):
    date_time = datetime.now()
    start_date = date_time.strftime("%d-%m-%Y")

    while True:
        frame = video_cap.read()
        if frame is None:
            logging.debug('frame is None')
            await asyncio.sleep(1)
            continue

        if OUTPUT_IMG_SHAPE:
            frame = cv2.resize(frame, OUTPUT_IMG_SHAPE)

        date_time = datetime.now()
        current_time = date_time.strftime("%H-%M-%S")
        current_date = date_time.strftime("%d-%m-%Y")

        new_dir_path = SAVE_DIR+current_date
        if not os.path.exists(new_dir_path):
            os.makedirs(new_dir_path)
            logging.debug(f'dir {new_dir_path} created')

        # if current_date != start_date:
            # old_dir_path = SAVE_DIR+start_date
            # start_date = current_date
            # archiving
            # compress_images_to_zip(old_dir_path, old_dir_path+'.zip')
            # delete old folder
            # shutil.rmtree(old_dir_path)

        cv2.imwrite(f'{SAVE_DIR}{current_date}/{current_time}.jpg', frame)
        logging.info(f'{SAVE_DIR}{current_date}/{current_time}.jpg - Screenshot saved!')

        await asyncio.sleep(DELAY_SEC)


if __name__ == "__main__":
    DELAY_SEC = 60
    SAVE_DIR = './images/'
    VIDEO_SRC = 'http://192.168.1.156:8080/video'
    OUTPUT_IMG_SHAPE = (1920, 1080) # (W, H) or None
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    try:
        logging.info(f"Initializing video capture...")
        video_capture = VideoCaptureAsync(VIDEO_SRC).start()
    except RuntimeError as e:
        logging.error(e)
        exit()
    
    if not os.path.exists(SAVE_DIR): 
        os.makedirs(SAVE_DIR)
    
    try:
        asyncio.run(main(video_capture))
    except KeyboardInterrupt:
        logging.critical('Shutdown initiated...')
    finally:
        video_capture.release()
        logging.critical('Shutdown complete.')