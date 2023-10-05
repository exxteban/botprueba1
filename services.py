# -*- coding: utf-8 -*-
import requests
import sett
import json
import time
import openai
import csv
import os
from datetime import datetime
import spacy
from spacy.matcher import Matcher

contexto = []


def obtener_Mensaje_whatsapp(message):
    if 'type' not in message:
        text = 'mensaje no reconocido'
        return text

    typeMessage = message['type']
    if typeMessage == 'text':
        text = message['text']['body']
    elif typeMessage == 'button':
        text = message['button']['text']
    elif typeMessage == 'interactive' and message['interactive']['type'] == 'list_reply':
        text = message['interactive']['list_reply']['title']
    elif typeMessage == 'interactive' and message['interactive']['type'] == 'button_reply':
        text = message['interactive']['button_reply']['title']
    else:
        text = 'mensaje no procesado'

    return text


def enviar_Mensaje_whatsapp(data):
    try:
        whatsapp_token = sett.whatsapp_token
        whatsapp_url = sett.whatsapp_url
        headers = {'Content-Type': 'application/json',
                   'Authorization': 'Bearer ' + whatsapp_token}
        print("se envia ", data)
        response = requests.post(whatsapp_url,
                                 headers=headers,
                                 data=data)

        if response.status_code == 200:
            return 'mensaje enviado', 200
        else:
            return 'error al enviar mensaje', response.status_code
    except Exception as e:
        return e, 403


def text_Message(number, text):
    data = json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": number,
            "type": "text",
            "text": {
                    "body": text
            }
        }
    )
    return data


def buttonReply_Message(number, options, body, footer, sedd, messageId):
    buttons = []
    for i, option in enumerate(options):
        buttons.append(
            {
                "type": "reply",
                "reply": {
                    "id": sedd + "_btn_" + str(i+1),
                    "title": option
                }
            }
        )

    data = json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": number,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {
                    "text": body
                },
                "footer": {
                    "text": footer
                },
                "action": {
                    "buttons": buttons
                }
            }
        }
    )
    return data


def listReply_Message(number, options, body, footer, sedd, messageId):
    rows = []
    for i, option in enumerate(options):
        rows.append(
            {
                "id": sedd + "_row_" + str(i+1),
                "title": option,
                "description": ""
            }
        )

    data = json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": number,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {
                    "text": body
                },
                "footer": {
                    "text": footer
                },
                "action": {
                    "button": "Ver Opciones",
                    "sections": [
                        {
                            "title": "Secciones",
                            "rows": rows
                        }
                    ]
                }
            }
        }
    )
    return data


def document_Message(number, url, caption, filename):
    data = json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": number,
            "type": "document",
            "document": {
                "link": url,
                "caption": caption,
                "filename": filename
            }
        }
    )
    return data


def sticker_Message(number, sticker_id):
    data = json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": number,
            "type": "sticker",
            "sticker": {
                "id": sticker_id
            }
        }
    )
    return data


def get_media_id(media_name, media_type):
    media_id = ""
    if media_type == "sticker":
        media_id = sett.stickers.get(media_name, None)
    elif media_type == "image":
        media_id = sett.images.get(media_name, None)
    elif media_type == "video":
        media_id = sett.videos.get(media_name, None)
    elif media_type == "audio":
        media_id = sett.audio.get(media_name, None)
    return media_id  # en el otro se comenta casi todo


def replyReaction_Message(number, messageId, emoji):
    data = json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": number,
            "type": "reaction",
            "reaction": {
                "message_id": messageId,
                "emoji": emoji
            }
        }
    )
    return data


def replyText_Message(number, messageId, text):
    data = json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": number,
            "context": {"message_id": messageId},
            "type": "text",
            "text": {
                "body": text
            }
        }
    )
    return data


def markRead_Message(messageId):
    data = json.dumps(
        {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id":  messageId
        }
    )
    return data

# services.py


# Diccionario global para almacenar los mensajes en memoria
conversations_in_memory = {}


def add_message_to_memory(number, user_msg, bot_msg):
    if number not in conversations_in_memory:
        conversations_in_memory[number] = []
    conversations_in_memory[number].append(
        {'role': 'user', 'content': user_msg})
    conversations_in_memory[number].append(
        {'role': 'assistant', 'content': bot_msg})


def get_messages_from_memory(number, max_messages=10):
    """
    Esta función extraerá los últimos `max_messages` mensajes de la conversación 
    asociada con un número de teléfono específico desde la memoria.
    """
    if number in conversations_in_memory:
        # Si hay demasiados mensajes, solo conserva los más recientes
        return conversations_in_memory[number][-2*max_messages:]
    return []

# ... Resto del código ...


def administrar_chatbot(text, number, messageId, name, contexto=None):
    text = text.lower()  # mensaje que envía el usuario
    list_respuestas = []  # Lista para almacenar las respuestas

    markRead = markRead_Message(messageId)
    list_respuestas.append(markRead)
    time.sleep(2)

    # Llama a la función generar_respuesta_chatgpt para obtener la respuesta de ChatGPT
    respuesta_chatgpt = generar_respuesta_chatgpt(
        text, number, contexto=contexto)

    # Crea un mensaje de texto con la respuesta de ChatGPT
    textMessage = text_Message(number, respuesta_chatgpt)
    list_respuestas.append(textMessage)

    # Añade el mensaje del usuario y la respuesta del bot a la memoria
    add_message_to_memory(number, text, respuesta_chatgpt)

    # Envía todas las respuestas almacenadas en list_respuestas
    for respuesta in list_respuestas:
        enviar_Mensaje_whatsapp(respuesta)


# chatgpt
openai.api_key = sett.openai_key


def generar_respuesta_chatgpt(user_message, number, espedido=False, contexto=None):

    print('generar_respuesta_chatgpt espedido true')
    messages = [
        {
            'role': 'system',
            'content': "Eres BotPedido, un servicio automatizado para recoger pedidos para un restaurante de comida. \
                    "
        },
        {
            'role': 'system',
            'content': "Los pedidos pueden ser para recoger del local de comida o para hacer delivery"
        },
        {
            'role': 'system',
            'content': "Primero empieza la conversación saludando al cliente una sola vez, luego tomas el pedido, \
                    y luego preguntas si es para recoger del restaurant o para entregar por delivery. \
                    Esperas a tomar todo el pedido, luego lo resúmenes y verificas por última \
                    vez si el cliente quiere agregar algo más. \
                    Si es una entrega, pides una dirección. \
                    Finalmente recoges el pago.\
                    Asegúrate de aclarar todas las opciones, entradas, bebidas y tamaños para identificar \
                    de forma única el artículo del menú.\
                    Respondes de manera corta, precisa, muy conversacional y amigable."
        },
        {
            'role': 'system',
            'content': "El menú incluye \
                    Ceviche  10 35 soles \
                    Lomo saltado 12 28 soles \
                    Arroz con pollo  11 26 soles \
                    Entradas: \
                    Tamales  10 soles \
                    Anticuchos  22 soles \
                    Papa rellena  15 soles \
                    Bebidas: \
                    Chicha Morada  6 soles \
                    Inca Kola  5 soles \
                    Agua embotellada  4 soles."
        }
    ]

    historial = get_messages_from_memory(number)
    messages.extend(historial)
    print('message:', messages)

    messages.append({'role': 'user', 'content': user_message})
    print('generar_respuesta_chatgpt')
    if espedido:
        print('generar_respuesta_chatgpt espedido true')
        messages.append(
            {'role': 'system', 'content': 'Crea un resumen del pedido anterior en formato JSON. \
                        Primero analiza el menu del restaurante ingresado al inicio \
                        contexto inicial y compara con el pedido del usuario y solo cuando hayas analizado  \
                        el pedido completo del usuario,  categorizalo en lista plato principal, lista de entradas, lista de bebidas.  \
                        luego actualizar el precio total del pedido una vez hayas listado cada item. \
                        Los campos del json deben ser  \
                        1) lista plato principal  con atributos de nombre , tamaño , cantidad precio, \
                        2) lista de entradas con atributos de nombre, cantidad y precio, \
                        3) lista de bebidas con atributos de nombre, cantidad y precio,  \
                        4) precio total.'},
        )
    # Configura el número máximo de tokens permitidos en la respuesta
    max_tokens = 1000  # Cambia este valor según tus necesidades

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0,
        max_tokens=max_tokens
    )
    print(response)
    return response.choices[0].message["content"]


def generar_respuesta_chatgpt2(prompt, number, espedido=False):
    return 'respuesta del asistente'


def guardar_conversacion(conversation_id, number, name, user_msg, timestamp, bot_msg=''):
    try:
        conversations = []
        conversation = [conversation_id, number, name,
                        user_msg, bot_msg, datetime.fromtimestamp(timestamp)]
        print('inicio')
        # Guardar las conversaciones en el archivo CSV
        with open('conversaciones.csv', 'a', newline='') as csv_file:
            print('guardar conversacion')
            data = csv.writer(csv_file, delimiter=',')
            data.writerow(conversation)

        messages = get_chat_from_csv(number)
        print('mensajes del usuario: ', messages)
    except Exception as e:
        print(e)
        return e, 403


def get_chat_from_csv(number):
    messages = []
    print('get_chat_from_csv')
    with open('conversaciones.csv') as file:
        reader = csv.DictReader(file)
        print('conversaciones.csv')
        for row in reader:
            if row['number'] == number:
                print('number')
                user_msg = {'role': 'user', 'content': row['user_msg']}
                bot_msg = {'role': 'assistant', 'content': row['bot_msg']}
                messages.append(user_msg)
                messages.append(bot_msg)
    return messages


def guardar_pedido(jsonPedido, number):
    # Eliminar el texto que sigue al JSON
    print('guardar perdido')
    start_index = jsonPedido.find("{")
    end_index = jsonPedido.rfind("}")

    # Extrae la cadena JSON de la respuesta
    json_str = jsonPedido[start_index:end_index+1]

    # Convierte la cadena JSON en un objeto de Python
    pedido = json.loads(json_str)

    # Ahora puedes usar 'pedido' como un objeto de Python
    print('pedido', pedido)
    with open('pedidos.csv', 'a', newline='') as file:
        writer = csv.writer(file, delimiter=',')
        print('pedidos.csv')
        platos_principales = [
            f"{plato['cantidad']}  {plato['nombre']} - {plato['precio']} soles" for plato in pedido['plato_principal']]
        entradas = [
            f"{entrada['cantidad']} {entrada['nombre']} - {entrada['precio']} soles" for entrada in pedido['entradas']]
        bebidas = [
            f"{bebida['cantidad']} {bebida['nombre']} - {bebida['precio']} soles" for bebida in pedido['bebidas']]

        writer.writerow([number,
                         ', '.join(platos_principales),
                         ', '.join(entradas),
                         ', '.join(bebidas),
                         pedido['precio_total'],
                         datetime.now().strftime("%Y-%m-%d %H:%M:%S")])


def replace_start(s):
    if s.startswith("549"):
        return "54" + s[3:]
    else:
        return s
