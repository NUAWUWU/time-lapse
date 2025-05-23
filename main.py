import asyncio
import traceback

from classes.TimeLapse import TimeLapse
from classes.VideoCaptureAsync import VideoCaptureAsync
from classes.Email import Email
from logger_config import logger, setup_logger_from_config
from configs import CONFIG


if __name__ == "__main__":
    timelapse_config = CONFIG["timelapse_config"]

    setup_logger_from_config(
        timelapse_config["CONSOLE_LOG_LEVEL"],
        timelapse_config["FILE_LOG_LEVEL"],
        timelapse_config["LOG_DIR"])

    email_config = CONFIG["email_config"]

    video_cap = VideoCaptureAsync(timelapse_config["VIDEO_SRC"])

    email = Email(
        sender_email=email_config["SENDER_EMAIL"],
        smtp_password=email_config["SMTP_PASSWORD"],
        receiver_emails=email_config["RECEIVER_EMAILS"],
    )

    timelapse = TimeLapse(video_cap=video_cap,
                          email=email,
                          save_dir=timelapse_config["SAVE_DIR"],
                          logs_dir=timelapse_config["LOG_DIR"],
                          output_img_shape=timelapse_config["OUTPUT_IMG_SHAPE"],
                          delay_sec=timelapse_config["DELAY_SEC"],
                          days_to_keep=timelapse_config["DAYS_TO_KEEP_IMAGES"]
                          )

    try:
        asyncio.run(timelapse.start())
    except KeyboardInterrupt:
        logger.critical('Shutdown initiated...')
        timelapse.stop()
        u = input('Would you like to send a daily report for today? (Y/N) ')
        if u.lower() == 'y':
            logger.info('Send daily report initialized')
            timelapse.send_daily_report()
        logger.critical('Shutdown complete.')
    except Exception as e:
        if timelapse_config['DETAILED_ERROR_REPORT']:
            logger.critical(f'An exception occurred: {e}')
            logger.critical(f'Traceback: {traceback.format_exc()}')
        else:
            logger.critical(e)
        timelapse.stop()
