from flask import Flask
from flask import render_template
import cv2
import socket
from flask import Response
import time
app = Flask(__name__)

s = socket.socket(
    socket.AF_INET,
    socket.SOCK_DGRAM
)

s.connect(("8.8.8.8", 80))

local_ip = s.getsockname()[0]

s.close()
@app.route("/")
def home():

    try:

        with open(
            "/home/abreu/Projetos/robo/gesture.txt",
            "r"
        ) as f:

            current_gesture = (
                f.read().strip()
            )

    except:

        current_gesture = "NENHUM"

    return render_template(

        "index.html",

        ip=local_ip,

        gesture=current_gesture
    )
def generate_frames():

    while True:

        frame = cv2.imread(
            "img.jpg"
        )

        if frame is None:
            continue

        _, buffer = cv2.imencode(
            '.jpg',
            frame
        )

        frame = buffer.tobytes()
        time.sleep(0.03)
        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n'
            + frame +
            b'\r\n'
        )
@app.route('/video')
def video():

    return Response(
        generate_frames(),
        mimetype=
        'multipart/x-mixed-replace; boundary=frame'
    )
@app.route("/gesture")
def get_gesture():

    try:

        with open(
            "/home/abreu/Projetos/robo/gesture.txt",
            "r"
        ) as f:

            gesture = (
                f.read().strip()
            )

    except:

        gesture = "NENHUM"

    return gesture
app.run(
    host="0.0.0.0",
    port=5000,
    debug=False
)
