import cv2
import time
from datetime import datetime
import logging
import threading
import os

DELAY_SEC = 60
SAVE_DIR = './images/'
VIDEO_SRC = ''  #''
# OUTPUT_IMG_SHAPE = (1920, 1080)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


class VideoCaptureAsync:
    def __init__(self, sr):
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
            if not self.q.full():
                self.frame = frame
            else:
                time.sleep(0.1)  # Wait a bit if the queue is full

    def read(self):
        return self.frame

    def release(self):
        self.stop_event.set()
        if self.thread is not None:
            self.thread.join()  # Ensure the thread has finished execution
        self.cap.release()
        self.thread = None


try:
    if not os.path.exists(SAVE_DIR): 
        os.makedirs(SAVE_DIR)
    cap = VideoCaptureAsync(VIDEO_SRC)
    cap.start()
    
    while True:
        frame = cap.read()
        if frame is None:
            time.sleep(1)
            continue

        date_time = datetime.now()
        current_time = date_time.strftime("%H-%M-%S")
        current_date = date_time.strftime("%d-%m-%Y")

        # frame = cv2.resize(frame, OUTPUT_IMG_SHAPE)

        if not os.path.exists(SAVE_DIR+current_date): 
            os.makedirs(SAVE_DIR+current_date)

        cv2.imwrite(f'{SAVE_DIR}{current_date}/{current_time}.jpg', frame)
        print(f"{current_date}/{current_time}.jpg - Screenshot saved")

        time.sleep(DELAY_SEC)
except KeyboardInterrupt:
    cap.release()
    print('Interrupted by user. Exiting...')
