import logging
from watchdog.events import LoggingEventHandler, FileSystemEventHandler
from watchdog import observers
import time

class MyEventHandler(FileSystemEventHandler):
    def on_any_event(self, event):
        print('Event captured. Event type:{}, src_path:{}'.format(event.event_type, event.src_path))

def main():
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    event_handler = MyEventHandler()#LoggingEventHandler()
    observer = observers.Observer()
    observer.schedule(event_handler, '/home/subhadip/gdrive-sync/', recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == '__main__':
    main()