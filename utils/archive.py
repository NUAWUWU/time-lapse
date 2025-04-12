import zipfile
import shutil
import os


from logger_config import logger


def archive_images(folder_path, output_zip_path, delete_folder=False):
    logger.info(f'Starting to archive images from {folder_path} to {output_zip_path}.')

    total_size = 0
    image_count = 0
    
    try:
        with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            logger.debug(f'Creating zip archive {output_zip_path}.')
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):   
                        file_path = os.path.join(root, file)
                        zipf.write(file_path, os.path.relpath(file_path, folder_path))
                        file_size = os.path.getsize(file_path)
                        total_size += file_size
                        image_count += 1
                        logger.debug(f'Added {file_path} to archive ({file_size / 1024:.2f} KB).')

        total_size_mb = total_size / (1024 * 1024)
        logger.info(f'Archive {output_zip_path} created successfully with {image_count} images, total size {total_size_mb:.2f} MB.')
        
        if delete_folder:
            logger.debug(f'Deleting original folder {folder_path}.')
            shutil.rmtree(folder_path)
            logger.info(f'Folder {folder_path} deleted.')
    except Exception as e:
        logger.error(f'An error occurred during archiving or folder deletion: {e}')
    return total_size_mb, image_count
