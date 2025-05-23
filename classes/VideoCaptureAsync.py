import cv2
import time
import threading

from logger_config import logger


class VideoCaptureAsync:
    def __init__(self, src):
        self.src = src
        self.frame = None
        self.stop_event = threading.Event()
        self.thread = None

        self.cap = cv2.VideoCapture(self.src)
        if not self.cap.isOpened():
            raise RuntimeError(f"Cam {self.src} not found")
        
    def start(self):
        if self.thread is None:
            self.thread = threading.Thread(target=self.update, args=())
            self.thread.start()
        return self

    def update(self):
        while not self.stop_event.is_set():
            if not self.cap.isOpened():
                logger.warning(f'Camera {self.src} lost connection. Trying to reconnect in 10 seconds...')
                time.sleep(10)
                self.cap.open(self.src)
                continue
            ret, frame = self.cap.read()
            if not ret:
                logger.warning(f'Failed to read frame from camera {self.src}. Reconnecting in 10 seconds...')
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

    def __del__(self):
        self.release()
