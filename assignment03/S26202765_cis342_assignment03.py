import cv2
import numpy as np
import os
import sys

face_cascade = cv2.CascadeClassifier(
    os.path.join(cv2.data.haarcascades, 'haarcascade_frontalface_alt.xml') # type: ignore
)

if face_cascade.empty():
    print("error：Can't load cascade file.")
    sys.exit(1)

cap = cv2.VideoCapture(1)

if not cap.isOpened():
    print("error：Can't turn on cam.")
    sys.exit(1)

scaling_factor = 0.5
while cap.isOpened():
  ret, frame = cap.read()

  if not ret or frame is None:
        print("warn：Frame stream ended.")
        break

  frame = cv2.resize(
     frame,
     None,
     fx=scaling_factor,fy=scaling_factor,
     interpolation=cv2.INTER_AREA
     )
  gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
  face_rects = face_cascade.detectMultiScale(gray, 1.3, 5)

  for (x,y,w,h) in face_rects:
    cv2.rectangle(frame, (x,y), (x+w,y+h), (0,255,0), 3)

  cv2.imshow('Face Detector', frame)

  c = cv2.waitKey(1)
  if c == 27:
   break
cap.release()
cv2.destroyAllWindows()