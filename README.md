# Gesture Controlled Robot 🤖✋

Sistema de controlo de um robô móvel através de reconhecimento de gestos da mão em tempo real, utilizando visão computacional, MediaPipe Hands e Machine Learning.

O projeto foi desenvolvido para correr numa Raspberry Pi e permite controlar motores através de comunicação serial, enquanto uma dashboard web apresenta vídeo em tempo real e o gesto atualmente detetado.

---

# 🚀 Funcionalidades

- Deteção de mãos em tempo real com MediaPipe
- Reconhecimento de gestos personalizados
- Controlo de motores via serial UART
- Dashboard Web em Flask
- Streaming MJPEG da câmara
- Sistema de segurança sem gesto detetado
- Suporte para Machine Learning
- Modelos `.pkl` treinados localmente
- Compatível com Raspberry Pi
- Compatível com C++
- Compatível com CMake

---

# 🖐️ Gestos Implementados

| Gesto | Função |
|---|---|
| Palma aberta | PARAR |
| Fechar mão e abrir | AVANÇAR |
| Indicador esquerda | VIRAR ESQUERDA |
| Indicador direita | VIRAR DIREITA |

---

# 🧠 Tecnologias Utilizadas

- Python
- OpenCV
- MediaPipe
- Flask
- Scikit-Learn
- UART Serial
- C++
- CMake

---

# 📂 Estrutura do Projeto

```text
.
├── .qtcreator/               # Configurações Qt Creator
├── build/                    # Build CMake
├── models/                   # Modelos ONNX e ML
├── static/                   # Ficheiros estáticos dashboard
├── templates/                # Templates HTML Flask
├── multiServer_01.py         # Sistema principal Python
├── multiServer_02.cpp        # Implementação C++
├── web_dashboard.py          # Dashboard Web
├── collect_stop_data.py      # Recolha de dataset
├── train_stop_model.py       # Treino modelo STOP
├── stop_model.pkl            # Modelo STOP treinado
├── right_model.pkl           # Modelo RIGHT treinado
├── gestures.csv              # Dataset de gestos
├── TESTE_SERIAL.py           # Testes comunicação serial
├── CMakeLists.txt            # Configuração CMake
└── README.md
```
# ⚙️ Arquitetura do Sistema

O sistema é dividido em vários módulos.

## 🔹 Visão Computacional

Responsável pela deteção da mão e extração dos landmarks utilizando MediaPipe Hands.

## 🔹 Reconhecimento de Gestos

Sistema híbrido composto por:

- regras geométricas
- Machine Learning
- gestão de estados
- cooldowns
- edge detection

## 🔹 Controlo dos Motores

Comunicação serial UART entre Raspberry Pi e controladora dos motores.

## 🔹 Dashboard Web

Interface Flask com:

- vídeo em tempo real
- estado do robô
- gesto atual
- telemetria

---

# 🧠 Machine Learning

O projeto inclui scripts para:

- recolha de dados
- treino de modelos
- exportação de datasets
- utilização de modelos treinados

Os modelos atuais utilizam landmarks do MediaPipe como input.

---

# 🖥️ Dashboard Web

A dashboard permite:

- visualizar a câmara em tempo real
- acompanhar gestos detetados
- monitorizar o estado do robô
- aceder remotamente através da rede local

---

# 🔌 Comunicação Serial

A comunicação serial é realizada através da porta:

```bash
/dev/ttyAMA0
```
Com baudrate:

```bash
115200
```

---

# 🛠️ Compilação C++

O projeto inclui suporte para C++ e CMake.

## Compilar

```bash
mkdir build
cd build
cmake ..
make
```

---

# ▶️ Executar Projeto

## Criar ambiente virtual

```bash
python3 -m venv venv
source venv/bin/activate
```

## Instalar dependências

```bash
pip install -r requirements.txt
```

## Executar sistema principal

```bash
python3 multiServer_01.py
```

## Executar dashboard

```bash
python3 web_dashboard.py
```

---

# 🌐 Acesso Dashboard

```text
http://IP_DA_RASPBERRY:5000
```

---

# 📌 Objetivo

Este projeto foi desenvolvido com foco em:

- robótica
- visão computacional
- interação humano-máquina
- controlo gestual
- sistemas embebidos

---

# 📷 Demonstração

*(Adicionar imagens ou vídeos futuramente)*

---

# 👨‍💻 Autor

Luis Abreu & Adulai Robalo
