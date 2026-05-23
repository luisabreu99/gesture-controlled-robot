import socket          # Comunicação entre cliente e servidor
import threading       # Permite executar várias tarefas ao mesmo tempo
import serial          # Comunicação serial com os motores
import cv2             # OpenCV para processamento de imagem
import mediapipe as mp # Deteção e tracking das mãos
import time            # Gestão de tempo e cooldowns
import joblib          # Carregar modelos de Machine Learning

# -----------------------------
# GLOBAL
# -----------------------------

# Inicializa a captura da câmara
capture = cv2.VideoCapture(0)

# Verifica se a câmara abriu corretamente
if not capture.isOpened():

    print("Erro camera")

# Contador usado no gesto AVANÇAR
forward_counter = 0

# Variável para terminar o servidor
endServer = False

# Lock para evitar conflitos na comunicação serial
serial_lock = threading.Lock()

# Modelo ML responsável pelo gesto STOP
stop_model = joblib.load(
    "stop_model.pkl"
)

# Modelo ML responsável pelo gesto RIGHT
right_model = joblib.load(
    "right_model.pkl"
)

# Velocidade normal do robô
ROBOT_SPEED = 6

# Velocidade usada nas rotações
TURN_SPEED = 4

# Ativa apenas debug dos gestos sem mover motores
DEBUG_GESTURES_ONLY = True

# Guarda o último gesto enviado aos motores
last_motor_gesture = None

# Conta frames sem deteção de gesto
no_gesture_counter = 0

# Número máximo de frames sem gesto antes de reset
MAX_NO_GESTURE_FRAMES = 15

# Inicializa o módulo de mãos do MediaPipe
mp_hands = mp.solutions.hands

# Estado atual do gesto AVANÇAR
forward_state = "IDLE"

# Tempo do último gesto detetado
last_gesture_time = 5

# Contador usado para confirmar o gesto AVANÇAR
forward_counter = 0

# Estado anterior do gesto RIGHT
last_right_state = False

# Estado anterior do gesto LEFT
last_right_state = False

# Estado anterior do gesto STOP
last_stop_state = False

# Estado anterior do gesto AVANÇAR
last_forward_state = False

# Tempo do último movimento AVANÇAR
last_forward_time = 0

# Variáveis reservadas para futura gestão de gestos
#last_gesture
#last_gesture_time

current_gesture = "NENHUM"

# Estado atual do gesto STOP
stop_state = "IDLE"

# Número de frames confirmados do STOP
stop_frames = 0

# Tempo do último STOP detetado
last_stop_time = 0

# Configuração principal do MediaPipe Hands
hands = mp_hands.Hands(

    # Número máximo de mãos detetadas
    max_num_hands=2,

    # Confiança mínima para detetar mão
    min_detection_confidence=0.7,

    # Confiança mínima para tracking contínuo
    min_tracking_confidence=0.7
)

# Utilitário para desenhar landmarks na imagem
mp_draw = mp.solutions.drawing_utils
# -----------------------------
# COMMAND CLASS
# -----------------------------

# Classe usada para guardar comandos enviados ao robô
class Command:

    def __init__(self):

        # Tipo de comando
        self.cmd = 0

        # Movimento horizontal
        self.vx = 0

        # Movimento vertical
        self.vy = 0

        # Rotação/inclinação
        self.pitch = 0


# -----------------------------
# SERIAL
# -----------------------------

# Informa no terminal a configuração da serial
print("Setting serial port serial0 to 115200")

try:

    # Inicializa comunicação serial com a controladora
    ser = serial.Serial(

        # Porta serial da Raspberry Pi
        '/dev/ttyAMA0',

        # Velocidade de comunicação
        115200,

        # Tempo máximo de espera
        timeout=1
    )

    print("Serial OK")

# Caso exista erro ao abrir a serial
except Exception as e:

    print("Erro serial:", e)

    ser = None


# -----------------------------
# LEITURA DE CORRENTE
# -----------------------------

# Lê valor de corrente enviado pela controladora
def motorReadCurrent():

    # Verifica se a serial está disponível
    if ser is None:
        return 0

    # Buffer temporário para guardar dados recebidos
    buf = ""

    # Procura início da mensagem
    while True:

        c = ser.read(1).decode(errors="ignore")

        if c == "":
            return 0

        # Início do pacote
        if c == "<":
            break

    # Lê conteúdo até encontrar fim da mensagem
    while True:

        c = ser.read(1).decode(errors="ignore")

        if c == "":
            return 0

        # Fim do pacote
        if c == ">":
            break

        # Guarda caracteres recebidos
        buf += c

    # Mostra buffer recebido no terminal
    print("buffer =", buf)

    # Tenta converter valor para inteiro
    try:

        return int(buf)

    # Caso o valor recebido seja inválido
    except ValueError:

        return 0

# -----------------------------
# CONFIRMAÇÃO ACK
# -----------------------------

# Verifica se a controladora respondeu corretamente
def get_ack(msg):

    # Verifica se a serial está disponível
    if ser is None:
        return False

    # Buffer usado para guardar resposta recebida
    buf = ""

    # Procura início da mensagem
    while True:

        c = ser.read(1).decode(errors="ignore")

        # Caso não receba dados
        if c == "":
            return False

        # Início do pacote
        if c == "<":
            break

    # Lê conteúdo da mensagem
    while True:

        c = ser.read(1).decode(errors="ignore")

        # Caso não receba dados
        if c == "":
            return False

        # Fim do pacote
        if c == ">":
            break

        # Guarda caracteres recebidos
        buf += c

    # Adiciona identificador inicial
    buf = "#" + buf

    # Mostra ACK recebido no terminal
    print("ACK =", buf)

    # Verifica se resposta corresponde à mensagem enviada
    return buf[:7] == msg[:7]


# -----------------------------
# ENVIO DE COMANDOS
# -----------------------------

# Envia comando para a controladora dos motores
def motorCmdWrite(msg):

    # Verifica se a serial está disponível
    if ser is None:

        print("Serial indisponivel")

        return False

    # Evita conflitos entre várias threads
    with serial_lock:

        # Mostra comando enviado no terminal
        print("A enviar:", repr(msg))

        # Envia mensagem pela serial
        ser.write(msg.encode("ascii"))

        # Força envio imediato dos dados
        ser.flush()

        # Aguarda confirmação da controladora
        return get_ack(msg)


# -----------------------------
# LIMITADOR DE VELOCIDADE
# -----------------------------

# Limita os valores máximos e mínimos da velocidade
def clamp_speed(value):

    # Converte valor para inteiro
    value = int(value)

    # Garante que o valor fica entre -10 e 10
    return max(-10, min(10, value))

# -----------------------------
# MOVIMENTO DO ROBÔ
# -----------------------------

# Envia velocidades para os motores esquerdo e direito
def moveRobot(vx, vy):

    # Limita velocidade máxima dos motores
    vx = max(-9, min(9, vx))
    vy = max(-9, min(9, vy))

    # Cria comando do motor esquerdo
    M1 = f"#ML{'+' if vx >= 0 else '-'}00{abs(vx)}\r"

    # Cria comando do motor direito
    M2 = f"#MR{'+' if vy >= 0 else '-'}00{abs(vy)}\r"

    # Mostra comandos no terminal
    print(repr(M1))
    print(repr(M2))

    # Envia comando para motor esquerdo
    motorCmdWrite(M1)

    # Envia comando para motor direito
    motorCmdWrite(M2)

# -----------------------------
# EXECUÇÃO DE GESTOS
# -----------------------------

# Executa movimentos do robô com base no gesto detetado
def execute_gesture_command(gesture):

    global last_motor_gesture
    global no_gesture_counter
    global current_gesture
    # Modo de debug sem mover motores
    if DEBUG_GESTURES_ONLY:
        '''
        print(
            "DEBUG GESTURE:",
            gesture
        )
        '''

        if gesture is not None:

            with open(
                "/home/abreu/Projetos/robo/gesture.txt",
                "w"
            ) as f:

                f.write(gesture)

                print(
                    "GESTO GUARDADO:",
                    gesture
                )

        return

    # Caso nenhum gesto seja detetado
    if gesture is None:

        # Incrementa contador de frames sem gesto
        no_gesture_counter += 1

        # Ativa paragem de segurança
        if no_gesture_counter >= MAX_NO_GESTURE_FRAMES:

            if last_motor_gesture != "PARAR":

                print("Sem gesto: STOP de seguranca")

                # Para o robô
                moveRobot(0, 0)

                last_motor_gesture = "PARAR"

        return

    # Reset do contador ao detetar gesto
    no_gesture_counter = 0

    # Evita enviar o mesmo comando repetidamente
    if gesture == last_motor_gesture:
        return

    # -----------------------------
    # PARAR
    # -----------------------------

    if gesture == "PARAR":

        moveRobot(0, 0)

    # -----------------------------
    # AVANÇAR
    # -----------------------------

    elif gesture == "AVANCAR":

        moveRobot(
            ROBOT_SPEED,
            ROBOT_SPEED
        )

    # -----------------------------
    # VIRAR ESQUERDA
    # -----------------------------

    elif gesture == "VIRAR ESQUERDA":

        moveRobot(
            -TURN_SPEED,
            TURN_SPEED
        )

    # -----------------------------
    # VIRAR DIREITA
    # -----------------------------

    elif gesture == "VIRAR DIREITA":

        moveRobot(
            TURN_SPEED,
            -TURN_SPEED
        )

    # Caso gesto não exista
    else:

        return

    # Guarda último gesto enviado aos motores
    last_motor_gesture = gesture
    current_gesture = gesture

    
def get_motors_current():
    M1 = "#AL+000\r"
    M2 = "#AR+000\r"

    motorCmdWrite(M1)
    current1 = motorReadCurrent()

    motorCmdWrite(M2)
    current2 = motorReadCurrent()

    return f"{current1} , {current2}"


def get_motors_max_current():
    M1 = "#XL+000\r"
    M2 = "#XR+000\r"

    motorCmdWrite(M1)
    current1 = motorReadCurrent()

    motorCmdWrite(M2)
    current2 = motorReadCurrent()

    return f"{current1} , {current2}"

def sendData(sock, msg):

    sock.sendall(
        msg.encode()
    )



def sendImgData(sock, image):

    _, buffer = cv2.imencode(
        '.jpg',
        image
    )

    sock.sendall(
        buffer.tobytes()
    )
    
def detect_stop_ml(
    landmarks
    ):
    global last_stop_state
    row = []

    for lm in landmarks:

        row.extend([
            lm.x,
            lm.y,
            lm.z
        ])

    prediction = stop_model.predict(
        [row]
    )[0]
    '''
    print(
        "STOP ML:",
        prediction
    )
    '''
    if prediction == "STOP":

        if not last_stop_state:

            last_stop_state = True

            return "PARAR"

    else:

        last_stop_state = False

    return None    
def detect_stop(
    landmarks,
    palm_front
    ):

    global stop_state
    global stop_frames
    global last_stop_time

    current_time = time.time()

    cooldown = (
        current_time -
        last_stop_time
    )

    # -------------------------
    # DEDOS ABERTOS
    # -------------------------

    index_open = (

        abs(
            landmarks[8].y -
            landmarks[5].y
        ) > 0.25
    )

    middle_open = (

        abs(
            landmarks[12].y -
            landmarks[9].y
        ) > 0.25
    )

    ring_open = (

        abs(
            landmarks[16].y -
            landmarks[13].y
        ) > 0.25
    )

    pinky_open = (

        abs(
            landmarks[20].y -
            landmarks[17].y
        ) > 0.20
    )


    # -------------------------
    # STOP DETECTADO
    # -------------------------

    stop_detected = (

        palm_front and
        
        index_open and
        middle_open and
        ring_open and
        pinky_open
        
    )

    # -------------------------
    # COOLDOWN
    # -------------------------

    if cooldown < 1:

        return None

    # -------------------------
    # IDLE
    # -------------------------

    if stop_state == "IDLE":

        if stop_detected:

            stop_state = "DETECTING"

            stop_frames = 1

    # -------------------------
    # DETECTING
    # -------------------------

    elif stop_state == "DETECTING":

        if stop_detected:

            stop_frames += 1

            print(
                "STOP FRAMES:",
                stop_frames
            )

        else:

            stop_state = "IDLE"

            stop_frames = 0

    # -------------------------
    # CONFIRMAÇÃO
    # -------------------------

    if stop_frames >= 10:

        stop_state = "IDLE"

        stop_frames = 0

        last_stop_time = time.time()

        return "PARAR"

    # -------------------------
    # RESET
    # -------------------------

    if not stop_detected:

        stop_state = "IDLE"

    return None

def detect_left(
    landmarks,
    hand_label,
    back_hand
    ):
    global last_left_state
    # -------------------------
    # DEDO INDICADOR ABERTO
    # -------------------------

    index_open = (

        abs(
            landmarks[8].x -
            landmarks[5].x
        ) > 0.20
    )

    # -------------------------
    # POLEGAR PARA CIMA
    # -------------------------

    thumb_up = (
        landmarks[4].y <
        landmarks[3].y
    )

    # -------------------------
    # POLEGAR AFASTADO
    # -------------------------

    thumb_far = (
        abs(
            landmarks[4].x -
            landmarks[8].x
        ) > 0.15
    )
    index_direction = (

    landmarks[8].x <
    landmarks[5].x
    )
    # -------------------------
    # DEDOS FECHADOS
    # -------------------------

    middle_closed = (

    abs(
        landmarks[12].x -
        landmarks[9].x
    ) < 0.10
    )

    ring_closed = (

        abs(
            landmarks[16].x -
            landmarks[13].x
        ) < 0.10
    )

    pinky_closed = (

        abs(
            landmarks[20].x -
            landmarks[17].x
        ) < 0.10
    )
    # -------------------------
    # INDICADOR VERTICAL
    # -------------------------

    index_horizontal = (

    abs(
        landmarks[8].y -
        landmarks[5].y
    ) < 0.10
    )

    # -------------------------
    # LEFT DETECTADO
    # -------------------------

    left_detected = (

       
        back_hand and

        thumb_up and
        thumb_far and

        index_open and
        index_horizontal and

        middle_closed and
        ring_closed and
        pinky_closed and
        index_direction
    )

    # -------------------------
    # RESULTADO
    # -------------------------

    if left_detected:

        if not last_left_state:

            last_left_state = True

            return "VIRAR ESQUERDA"

    else:

        last_left_state = False

    return None
def detect_right(
    landmarks,
    hand_label,
    back_hand
    ):
    global last_right_state
    # -------------------------
    # DEDO INDICADOR ABERTO
    # -------------------------

    index_open = (

        abs(
            landmarks[8].x -
            landmarks[5].x
        ) > 0.20
    )

    # -------------------------
    # POLEGAR PARA CIMA
    # -------------------------

    thumb_up = (
        landmarks[4].y <
        landmarks[3].y
    )

    # -----------------S--------
    # POLEGAR AFASTADO
    # -------------------------

    index_direction = (

    landmarks[8].x >
    landmarks[5].x
    )
    thumb_far = (
        abs(
            landmarks[4].x -
            landmarks[8].x
        ) > 0.15
    )

    # -------------------------
    # DEDOS FECHADOS
    # -------------------------

    middle_closed = (

    abs(
        landmarks[12].x -
        landmarks[9].x
    ) < 0.10
    )

    ring_closed = (

        abs(
            landmarks[16].x -
            landmarks[13].x
        ) < 0.10
    )

    pinky_closed = (

        abs(
            landmarks[20].x -
            landmarks[17].x
        ) < 0.10
    )

    # -------------------------
    # INDICADOR VERTICAL
    # -------------------------

    index_horizontal = (

    abs(
        landmarks[8].y -
        landmarks[5].y
    ) < 0.18
    )

    # -------------------------
    # RIGHT DETECTADO
    # -------------------------

    right_detected = (

       

        back_hand and

        thumb_up and
        thumb_far and

        index_open and
        index_horizontal and

        middle_closed and
        ring_closed and
        pinky_closed and
        index_direction
    )

    # -------------------------
    # RESULTADO
    # -------------------------

    if right_detected:

        if not last_right_state:

            last_right_state = True

            return "VIRAR DIREITA"

    else:

        last_right_state = False

    return None
def detect_forward(
    landmarks,
    back_hand
    ):

    global forward_state
    global forward_counter
    global last_forward_time
    global last_forward_state

    current_time = time.time()

    cooldown = (
        current_time -
        last_forward_time
    )

    # -------------------------
    # COOLDOWN
    # -------------------------

    if cooldown < 1:

        return None

    # -------------------------
    # DEDOS ABERTOS
    # -------------------------

    index_open = (

        abs(
            landmarks[8].y -
            landmarks[5].y
        ) > 0.25
    )

    middle_open = (

        abs(
            landmarks[12].y -
            landmarks[9].y
        ) > 0.25
    )

    ring_open = (

        abs(
            landmarks[16].y -
            landmarks[13].y
        ) > 0.25
    )

    pinky_open = (

        abs(
            landmarks[20].y -
            landmarks[17].y
        ) > 0.20
    )

    fingers_open = (

        index_open and
        middle_open and
        ring_open and
        pinky_open
    )

    # -------------------------
    # DEDOS FECHADOS
    # -------------------------

    fingers_closed = (

        landmarks[8].y >
        landmarks[6].y and

        landmarks[12].y >
        landmarks[10].y and

        landmarks[16].y >
        landmarks[14].y and

        landmarks[20].y >
        landmarks[18].y
    )

    # -------------------------
    # POLEGAR NORMAL
    # -------------------------

    thumb_ok = (

        abs(
            landmarks[4].x -
            landmarks[3].x
        ) < 0.05
    )

    # -------------------------
    # IDLE
    # -------------------------

    if forward_state == "IDLE":

        if (
            back_hand and
            fingers_open and
            thumb_ok
        ):

            forward_state = "READY"

            print("FORWARD READY")

    # -------------------------
    # READY
    # -------------------------

    elif forward_state == "READY":

        if (
            back_hand and
            fingers_closed and
            thumb_ok
        ):

            forward_counter += 1

            print(
                "FORWARD COUNT:",
                forward_counter
            )

            forward_state = "CLOSED"

    # -------------------------
    # CLOSED
    # -------------------------

    elif forward_state == "CLOSED":

        if (
            back_hand and
            fingers_open and
            thumb_ok
        ):

            forward_state = "READY"

    # -------------------------
    # RESET
    # -------------------------

    if not back_hand:

        forward_state = "IDLE"

        forward_counter = 0

    # -------------------------
    # CONFIRMAÇÃO
    # -------------------------

    if forward_counter >= 1:

        if not last_forward_state:

            last_forward_state = True

            forward_ready = False

            forward_counter = 0

            return "AVANCAR"

    else:

        last_forward_state = False

    return None
def detect_gesture(
    hand_landmarks,
    hand_label
    ):

    landmarks = hand_landmarks.landmark

    # -------------------------
    # VALIDAR LANDMARKS
    # -------------------------

    for lm in landmarks:

        if (
            lm.x < 0.05 or
            lm.x > 0.95 or
            lm.y < 0.05 or
            lm.y > 0.95
        ):

            return None

    # -------------------------
    # PALMA
    # -------------------------

    if hand_label == "Right":

        palm_front = (
            landmarks[4].x <
            landmarks[20].x
        )

    else:

        palm_front = (
            landmarks[4].x >
            landmarks[20].x
        )

    back_hand = not palm_front

    # -------------------------
    # STOP
    # -------------------------
    vertical_fingers = (

    abs(
        landmarks[8].x -
        landmarks[5].x
    ) < 0.12 and

    landmarks[8].y <
    landmarks[5].y and

    abs(
        landmarks[12].x -
        landmarks[9].x
    ) < 0.12 and

    landmarks[12].y <
    landmarks[9].y and

    abs(
        landmarks[16].x -
        landmarks[13].x
    ) < 0.12 and

    landmarks[16].y <
    landmarks[13].y and

    abs(
        landmarks[20].x -
        landmarks[17].x
    ) < 0.12 and

    landmarks[20].y <
    landmarks[17].y
    )
    fingers_open = (

    abs(
        landmarks[8].y -
        landmarks[5].y
    ) > 0.25 and

    abs(
        landmarks[12].y -
        landmarks[9].y
    ) > 0.25 and

    abs(
        landmarks[16].y -
        landmarks[13].y
    ) > 0.25 and

    abs(
        landmarks[20].y -
        landmarks[17].y
    ) > 0.20
    )
    if (
        palm_front and
        fingers_open and
        vertical_fingers
    ):

        gesture = detect_stop(
            landmarks,
            palm_front
    )

        if gesture:

            return gesture

    # -------------------------
    # LEFT
    # -------------------------

    gesture = detect_left(
        landmarks,
        hand_label,
        back_hand
    )

    if gesture:

        return gesture

    # -------------------------
    # RIGHT
    # -------------------------

    if back_hand:
       
    

        gesture = detect_right(
            landmarks,
            hand_label,
            back_hand
        )

        if gesture:

            return gesture

    # -------------------------
    # FORWARD
    # -------------------------

    gesture = detect_forward(
        landmarks,
        back_hand
    )

    if gesture:

        return gesture

    return None
def camera_loop():

    while True:

        ret, image = capture.read()

        if not ret:

            print("Erro frame")

            continue

        rgb = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2RGB
        )

        results = hands.process(rgb)
        frame_gesture = None
        
        if results.multi_hand_landmarks:

            for hand_landmarks, handedness in zip(
                results.multi_hand_landmarks,
                results.multi_handedness
            ):

                hand_label = handedness.classification[0].label



                mp_draw.draw_landmarks(
                    image,
                    hand_landmarks,
                    mp_hands.HAND_CONNECTIONS
                )

                gesture = detect_gesture(
                    hand_landmarks,
                    hand_label
                )

                if gesture is not None and frame_gesture is None:
                    frame_gesture = gesture
                
                
                for idx, lm in enumerate(hand_landmarks.landmark):

                    h, w, c = image.shape

                    cx = int(lm.x * w)

                    cy = int(lm.y * h)

                    cv2.putText(
                        image,
                        str(idx),
                        (cx, cy),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (255,0,0),
                        1
                    )
            execute_gesture_command(frame_gesture)
        else:
            execute_gesture_command(None)
        cv2.imwrite(
            "img.jpg",
            image
        )
    
        cv2.imshow(
            "HAND TRACKING",
            image
        )       

        if cv2.waitKey(1) == 27:
            break


# -----------------------------
# TASK THREAD
# -----------------------------

def task_code(client_socket):

    global endServer

    print("Nova thread cliente")

    while True:

        try:

            data = client_socket.recv(1024)

            if not data:
                break

            msg = data.decode().strip()

            print("Recebido:", msg)

            parts = msg.split(",")

            cmd = int(parts[0])

            # -------------------------
            # CMD 1
            # -------------------------

            if cmd == 1:

                break

            # -------------------------
            # CMD 2
            # -------------------------

            elif cmd == 2:

                endServer = True

                break

            # -------------------------
            # CMD 3
            # -------------------------
            elif cmd == 3:
                vx = int(parts[1])
                vy = int(parts[2])

                result = moveRobot(vx, vy)

                sendData(client_socket, result)




        except Exception as e:

            print("Erro cliente:", e)

            break

    client_socket.close()

    print("Cliente desligado")

# -----------------------------
# MAIN
# -----------------------------

HOST = "0.0.0.0"
PORT = 8085

print(f"using port #{PORT}")

sockfd = socket.socket(
    socket.AF_INET,
    socket.SOCK_STREAM
)
sockfd.setsockopt(
    socket.SOL_SOCKET,
    socket.SO_REUSEADDR,
    1
)
sockfd.bind((HOST, PORT))

sockfd.listen(5)

clientID = 0
camera_thread = threading.Thread(
    target=camera_loop
)

camera_thread.daemon = True

camera_thread.start()
while True:

    print(f"\nwaiting for new client... {clientID}")

    newsockfd, addr = sockfd.accept()

    print("Cliente ligado:", addr)

    thread = threading.Thread(
        target=task_code,
        args=(newsockfd,)
    )
    thread.daemon = True
    thread.start()

    clientID += 1

    if endServer:
        break

sockfd.close()

if ser:
    ser.close()

