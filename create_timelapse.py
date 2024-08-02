import os
import cv2
from datetime import datetime


def create_timelapse(base_folder, output_video, fps=1, img_format='.jpg', codec='mp4v'):
    all_images = []
    subfolders = [f.path for f in os.scandir(base_folder) if f.is_dir()]
    for folder in subfolders:
        images = [img for img in os.listdir(folder) if img.endswith(img_format)]
        
        for image in images:
            image_path = os.path.join(folder, image)
            image_time = datetime.strptime(os.path.basename(image), f'%H-%M-%S{img_format}')
            folder_date = datetime.strptime(os.path.basename(folder), '%d-%m-%Y')
            combined_datetime = datetime.combine(folder_date, image_time.time())
            all_images.append((combined_datetime, image_path))
    
    # Sort by date and time
    all_images.sort()
    
    if not all_images:
        print('Images not found.')
        return
    
    # Get img shape
    first_image_path = all_images[0][1]
    frame = cv2.imread(first_image_path)
    height, width, _ = frame.shape
    
    fourcc = cv2.VideoWriter_fourcc(*codec)  # Select codec
    video = cv2.VideoWriter(output_video, fourcc, fps, (width, height))
    
    # Create video
    for _, image_path in all_images:
        frame = cv2.imread(image_path)
        video.write(frame)
    
    video.release()
    print(f'Video saved in {output_video}')



if __name__ == '__main__':
    BASE_FOLDER = './'
    OUTPUT_FILE_PATH = '19-07-2024_timelapse_video.mp4'
    TARGET_FPS = 1
    IMAGE_FORMAT = '.jpg'
    CODEC = 'mp4v'
    create_timelapse(BASE_FOLDER, OUTPUT_FILE_PATH, TARGET_FPS, IMAGE_FORMAT, CODEC)