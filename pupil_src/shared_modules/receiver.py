import win32com.client
import os
import asyncio
from threading import Thread

from concurrent.futures import ThreadPoolExecutor

queue_info = win32com.client.Dispatch("MSMQ.MSMQQueueInfo")
computer_name = os.getenv('COMPUTERNAME')

queue_name = 'eeg'


def receive_messages():

    queue_info.FormatName = f'direct=os:{computer_name}\\PRIVATE$\\{queue_name}'
    queue = None

    try:
        queue = queue_info.Open(1, 0)

        while True:
            msg = queue.Receive()
            print(f'Got Message from {queue_name}: {msg.Label} - {msg.Body}')

    except Exception as e:
        print(f'Error! {e}')

    finally:
        queue.Close()


def receive():
    receiver_thread = Thread(target=receive_messages())
    receiver_thread.setDaemon(True)
    receiver_thread.start()

