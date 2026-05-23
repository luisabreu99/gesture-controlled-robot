import cv2
import mediapipe as mp
import csv

mp_hands = mp.solutions.hands

hands = mp_hands.Hands(
    max_num_hands=1
)

capture = cv2.VideoCapture(0)

# -------------------------
# LABEL
# -------------------------

label = "RIGHT"

# -------------------------
# CSV
# -------------------------

with open(
    "gestures.csv",
    "a",
    newline=""
) as f:

    writer = csv.writer(f)

    while True:

        ret, frame = capture.read()

        if not ret:
            continue

        rgb = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        results = hands.process(rgb)

        if results.multi_hand_landmarks:

            for hand_landmarks in (
                results.multi_hand_landmarks
            ):

                row = []

                for lm in (
                    hand_landmarks.landmark
                ):

                    row.extend([
                        lm.x,
                        lm.y,
                        lm.z
                    ])

                row.append(label)

                writer.writerow(row)

                print("RIGHT GUARDADO")

        cv2.imshow(
            "COLLECT RIGHT",
            frame
        )

        key = cv2.waitKey(1)

        if key == 27:
            break

capture.release()

cv2.destroyAllWindows()