import random
import sys
import time

print("Task API starting...")
time.sleep(1)

if random.random() < 0.3:
    print("ERROR: Random failure occurred!")
    sys.exit(1)

print("Task API started successfully!")
while True:
    time.sleep(10)