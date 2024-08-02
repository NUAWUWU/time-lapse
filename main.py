import cv2
import time
from datetime import datetime
import threading
import os

DELAY_SEC = 60
SAVE_DIR = './images/'
VIDEO_SRC = ''  #''
# OUTPUT_IMG_SHAPE = (1920, 1080)

if not os.path.exists(SAVE_DIR): 
    os.makedirs(SAVE_DIR)

class VideoCaptureAsync:
    def __init__(self, src):
        self.src = src
        self.cap = cv2.VideoCapture(self.src)
        self.frame = None
        self.stop_event = threading.Event()
        self.read_lock = threading.Lock()
        if not self.cap.isOpened():
            raise ValueError(f"Cannot open video source {self.src}")

    def start(self):
        self.thread = threading.Thread(target=self.update, args=())
        self.thread.start()
        return self

    def update(self):
        while not self.stop_event.is_set():
            if not self.cap.isOpened():
                self.cap.open(self.src)
            ret, frame = self.cap.read()
            if not ret:
                print('Warning!: Frame is not read')
                with self.read_lock:
                    self.frame = None
                self.stop_event.wait(1)  # Wait a bit before retrying
                continue
            with self.read_lock:
                self.frame = frame

    def read(self):
        with self.read_lock:
            return self.frame
    
    def release(self):
        self.stop_event.set()
        self.thread.join()
        self.cap.release()


try:
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
