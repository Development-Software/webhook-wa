import requests
import json
import os
import datetime
from rivescript import RiveScript
from .config import onedrive_config, connect_db


# from config import onedrive_config, connect_db


def update_file(config=onedrive_config):
    try:
        url = f"https://graph.microsoft.com/v1.0/users/{config['user_id']}/drive/root:/{config['path']}{config['file_name']}:/content"
        headers = {
            "Authorization": f"Bearer {get_access_token()}",
        }
        response = requests.request("GET", url, headers=headers)
        if os.getenv("DEBUG") == "True":
            print("[DEBUG] Status code file download: ", response.status_code)
            print("[DEBUG] File content: ", response.text)

        if response.status_code == 200:
            file_path = os.getcwd() + f"/functions/bot_files/{config['file_name']}"  # for linux
            # file_path = os.getcwd() + f"\\functions\\bot_files\\{config['file_name']}"
            if os.getenv("DEBUG") == "True":
                print("[DEBUG] File path: ", file_path)
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(response.text)
                if os.getenv("DEBUG") == "True":
                    print("[DEBUG] File updated")
    except Exception as ex:
        print("[ERROR] update_file")
        print("[ERROR] ", ex)


def bot_chat(message):
    try:
        update_file()
        bot = RiveScript()
        # bot.load_file(os.getcwd() + f"\\functions\\bot_files\\{onedrive_config['file_name']}")
        bot.load_file(os.getcwd() + f"/functions/bot_files/{onedrive_config['file_name']}")  # for linux
        bot.sort_replies()
        reply = bot.reply("localuser", message)
        reply = reply.replace("\\n", "\\\n")
        reply = reply.replace("\\", "")
        # reply.replace(".", "\n")
        # response = reply.replace("\\", "\n")
        return reply
    except Exception as ex:
        print("[ERROR] bot_chat")
        print("[ERROR] ", ex)


def send_response_bot(phone, response_in, preview_url, type, client, name):
    try:
        token = os.environ.get("TOKEN_WA")
        url = f"https://graph.facebook.com/v17.0/{os.getenv('ID_WA')}/messages"
        payload = json.dumps({
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": f"{phone}",
            "type": "text",
            "text": {
                "preview_url": preview_url,
                "body": f"{response_in}"
            }
        })
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }
        response = requests.request("POST", url, headers=headers, data=payload)
        if type == "admin_alert":
            response_text = json.loads(response.text)
            insert_message(client, str(name), str(response_in), "alerta_enviada", response_text["messages"][0]["id"],
                           datetime.datetime.now().timestamp(), 'alert')
        return response.status_code
    except Exception as ex:
        print("[ERROR] send_response")
        print("[ERROR] ", ex)


def get_access_token(config=onedrive_config):
    try:
        url = f"https://login.microsoftonline.com/{config['tenant_id']}/oauth2/v2.0/token"
        body = {
            "client_id": onedrive_config["client_id"],
            "scope": onedrive_config["scope"],
            "client_secret": onedrive_config["client_secret"],
            "grant_type": "client_credentials"
        }
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        response = requests.request("GET", url, headers=headers, data=body)
        token = response.json()["access_token"]
        return token
    except Exception as ex:
        print("[ERROR] get_access_token")
        print("[ERROR] ", ex)


def get_id_by_phone(phone):
    try:
        con = connect_db()
        cur = con.cursor()
        sql = f"SELECT id_guest FROM guests WHERE phone = '{phone}'"
        cur.execute(sql)
        id_guest = cur.fetchone()[0]
        con.close()
        return id_guest
    except Exception as ex:
        print("[ERROR] get_id_by_phone")
        print("[ERROR] ", ex)


def get_name_by_phone(phone):
    try:
        con = connect_db()
        cur = con.cursor()
        sql = f"SELECT name FROM guests WHERE phone = '{phone}'"
        cur.execute(sql)
        name = cur.fetchone()[0]
        con.close()
        return name
    except Exception as ex:
        print("[ERROR] get_name_by_phone")
        print("[ERROR] ", ex)


def get_guests_by_family(id_guest):
    try:
        con = connect_db()
        cur = con.cursor()
        sql = f"SELECT id_guest,adults+teenagers+kids total FROM guest_person WHERE id_guest='{id_guest}'"
        cur.execute(sql)
        result = cur.fetchone()
        con.close()
        return result
    except Exception as ex:
        print("[ERROR] get_guests_by_family")
        print("[ERROR] ", ex)


def log_record(json_data, wa_id):
    try:
        fecha_actual = datetime.datetime.now()
        formato = "%d_%m_%Y"
        fecha_formateada = fecha_actual.strftime(formato)
        path = os.getcwd() + f"/logs/{fecha_formateada}/"
        # path = os.getcwd() + f"\\logs\\{fecha_formateada}\\"
        if not os.path.exists(path):
            os.makedirs(path)
        file_path = path + wa_id + ".txt"
        if os.path.exists(file_path) and os.path.isfile(file_path):
            with open(file_path, "a") as file:
                file.write(
                    f"\n:::::::::::::::::::::::::::::::::::::::::::::::append message({datetime.datetime.now()}):::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::\n")
                file.write(json_data)
                file.close()
        else:
            with open(file_path, "w") as file:
                file.write(
                    f"\n:::::::::::::::::::::::::::::::::::::::::::::::create message({datetime.datetime.now()}):::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::\n")
                file.write(json_data)
                file.close()
    except Exception as ex:
        print("[ERROR] log_record")
        print("[ERROR] ", ex)


def insert_message(phone, name, message_in, message_out, wa_id, timestamp, type):
    try:
        con = connect_db()
        cur = con.cursor()
        message_out = message_out.replace("\n", "")
        cur.callproc('new_record', (phone, name, message_in, message_out, wa_id, timestamp, type))
        con.commit()
        con.close()
    except Exception as ex:
        print("[ERROR] insert_message")
        print("[ERROR] ", ex)


def insert_persons_confirm(id_guest, persons, id_confirm):
    try:
        if id_confirm == 1:
            status = 'unpaid'
        else:
            status = 'cancel'
        total = int(persons) * 250
        con = connect_db()
        cur = con.cursor()
        cur.callproc('confirm_food_persons', (id_guest, id_confirm, persons, total, status))
        con.commit()
        con.close()
    except Exception as ex:
        print("[ERROR] insert_persons_confirm")
        print("[ERROR] ", ex)


def payload_confirm(phone, name, response_client):
    try:
        if response_client == "Más información":
            message = f"_Que tal {name}!_\n\n" \
                      "_Es un placer proporcionarte más información y detalles sobre el desayuno especial en el que los hemos contemplado._\n\n" \
                      "_El desayuno incluirá:_\n\n" \
                      "_-Recepción con cervezas para comenzar el día. 🍻_\n" \
                      "_-Delicioso buffet de barbacoa y consomé.🌮_\n" \
                      "_-Variedad de refrescos, jugos y hielo para mantenernos frescos durante la celebración.🥤_\n\n" \
                      "_La cita es a las 11:00 am ⏰ y podremos disfrutar de ella hasta las 3:00 pm._\n\n" \
                      "_Para asegurarnos de que todos puedan disfrutar sin ningun inconveniente, se ha establecido un costo de *$250* por persona para aquellos mayores de 10 años. Agradecemos sinceramente tu comprensión y consideración en este aspecto.🙏🏽_"
            payload = json.dumps({
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": f"{phone}",
                "type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {
                        "text": f"{message}"
                    },
                    "action": {
                        "buttons": [
                            {
                                "type": "reply",
                                "reply": {
                                    "id": "confirm",
                                    "title": "✅ Confirmar"
                                }
                            },
                            {
                                "type": "reply",
                                "reply": {
                                    "id": "no_confirm",
                                    "title": "❌ Cancelar"
                                }
                            }
                        ]
                    }
                }
            })
            return payload
        elif response_client == "No puedo acompañarlos":
            message = f"_Que tal {name}!_\n\n" \
                      "_😔 Lamentamos que no puedan unirse al desayuno al día siguiente,pero lo entendemos perfectamente. Agradecemos nuevamente su confirmación para el evento principal 🍾 y esperamos disfrutar de una celebración inolvidable con ustedes._\n\n" \
                      "_Recuerden llevar con ustedes sus boletos digitales para el acceso y si tienen alguna duda con las instrucciones de la invitación o las opciones de hospedaje no duden en contactarnos 📱_"
            payload = json.dumps({
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": f"{phone}",
                "type": "text",
                "text": {
                    "preview_url": False,
                    "body": f"{message}"
                }
            })
            return payload
    except Exception as ex:
        print("[ERROR] payload_confirm")
        print("[ERROR] ", ex)


def payload_confirm_food(phone, name, response_client):
    try:
        if response_client == "confirm":
            message = "_Para que el proceso de confirmación sea sencillo, aquí te proporcionamos información importante ℹ️:_\n\n" \
                      "_*Cuenta bancaria para el pago:*💳_\n" \
                      "_Banco: BANAMEX_\n" \
                      "_CLABE: 002180701927919938_\n" \
                      "_Titular de la cuenta: Omar Martinez Jimenez_\n" \
                      "_Monto a pagar: $250 pesos por persona_\n" \
                      "_Concepto: Desayuno+tu nombre_\n\n" \
                      "_*Fecha límite de pago:* 27/10/2023 📆_\n\n" \
                      "_🙏🏽Te pedimos amablemente que realices el pago antes de la fecha límite mencionada para que podamos organizar todo de manera óptima._\n\n" \
                      "_Por último, necesitamos saber cuántas personas 👨‍👩‍👧‍👧 asistirán para el desayuno. Por favor, ten en cuenta que solo se consideran personas mayores de 10 años para este conteo._\n\n" \
                      "_Agradecemos tu apoyo y no dudes en comunicarte si tienes alguna pregunta o necesitas más detalles._❓"
            send_text = send_response_bot(phone, message, False, "message_text", phone, name)
            if send_text == 200:
                id_guest = get_id_by_phone(phone[3:])
                n = get_guests_by_family(id_guest)
                rows = []
                n_guests = n[1]
                for i in range(1, n_guests + 1):
                    row = {
                        "id": str(i),
                        "title": f"{i} persona{'s' if i > 1 else ''}"  # Ajustar el título según el número de personas
                    }
                    rows.append(row)
                rows_person = json.dumps(rows, indent=4)
                payload = json.dumps({
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": f"{phone}",
                    "type": "interactive",
                    "interactive": {
                        "type": "list",
                        "body": {
                            "text": f"¿Cuantas personas asistirán?"
                        },
                        "action": {
                            "button": "Opciones",
                            "sections": [
                                {
                                    "title": "Selecciona una opción",
                                    "rows": rows_person
                                }
                            ]
                        }
                    }

                })
                return payload
        elif response_client == "no_confirm":
            message = f"_😔 Lamentamos que no puedan unirse al desayuno al día siguiente,pero lo entendemos perfectamente. Agradecemos nuevamente su confirmación para el evento principal 🍾 y esperamos disfrutar de una celebración inolvidable con ustedes._\n\n" \
                      "_Recuerden llevar con ustedes sus boletos digitales para el acceso y si tienen alguna duda con las instrucciones de la invitación o las opciones de hospedaje no duden en contactarnos 📱_"
            payload = json.dumps({
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": f"{phone}",
                "type": "text",
                "text": {
                    "preview_url": False,
                    "body": f"{message}"
                }
            })
            return payload

    except Exception as ex:
        print("[ERROR] payload_confirm_food")
        print("[ERROR] ", ex)


def payload_persons_confirm(phone):
    try:
        message = f"_¡Gracias por tu apoyo! 🙌🏽_\n\n" \
                  "_Hemos registrado tu confirmación para el desayuno y esperamos que disfrutes de esta experiencia con nosotros._\n" \
                  "_Si tienes algun problema para realizar el pago o tienes alguna duda, no dudes en contactarnos. 📱_"
        payload = json.dumps({
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": f"{phone}",
            "type": "text",
            "text": {
                "preview_url": False,
                "body": f"{message}"
            }
        })
        return payload
    except Exception as ex:
        print("[ERROR] payload_persons_confirm")
        print("[ERROR] ", ex)


def payload_hotel_pay(phone):
    try:
        message = f"_¡Claro! Te compartimos los datos donde puedes realizar tu pago mediante una transferencia 💳_\n\n" \
                  "Datos Bancarios:\n" \
                  "_Banco: *BBVA*_\n" \
                  "_CLABE: *012180015323778093*_\n" \
                  "_Tarjeta: *4152313856454314*_\n" \
                  "_Titular de la cuenta: *Karla Ivone Lemus Segura*_\n\n" \
                  "_Nota: Te pedimos compartir tu comprobante de pago a en este chat o al numero 5539041134_\n" \
                  "_!Muchas gracias por tu apoyo!_"
        payload = json.dumps({
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": f"{phone}",
            "type": "text",
            "text": {
                "preview_url": False,
                "body": f"{message}"
            }
        })
        return payload
    except Exception as ex:
        print("[ERROR] payload_hotel_pay")
        print("[ERROR] ", ex)


def payload_others_message(phone, type):
    try:
        if type == "question":
            message = f"_Hemos registrado tu mensaje y nos pondremos en contacto contigo lo antes posible para resolver tus inquietudes._"
        else:
            message = f"_Hola! 👋🏽_\n\n" \
                      "_Esperamos que estés teniendo un grand día._\n" \
                      "_¡Al parecer tu mensaje no es una duda!,Si tienes alguna pregunta o inquietud, déjanos tu mensaje con el detalle. Estamos aquí para ayudarte._\n" \
                      "_Nos pondremos en contacto contigo a la brevedad posible para brindarte todas las respuestas que necesitas._\n " \
                      "_Saludos!!!_ 📱"
        payload = json.dumps({
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": f"{phone}",
            "type": "text",
            "text": {
                "preview_url": False,
                "body": f"{message}"
            }
        })
        return payload
    except Exception as ex:
        print("[ERROR] payload_others_message")
        print("[ERROR] ", ex)


def payload_doubt_message(phone, payload):
    try:
        if payload == "Aclarar una duda":
            message = f"_¡Con mucho gusto respondemos tus dudas! 🙌🏽_\n\n" \
                      "_Compártenos tu inquietud en un solo mensaje y trataremos re responderte lo mas pronto posible!_"
            payload = json.dumps({
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": f"{phone}",
                "type": "text",
                "text": {
                    "preview_url": False,
                    "body": f"{message}"
                }
            })
            return payload
        elif payload == "No tengo dudas":
            message = f"_Perfecto!_\n" \
                      "_Recuerden llevar con ustedes sus boletos digitales para el acceso y si tienen alguna duda mas adelante con las instrucciones de la invitación o las opciones de hospedaje no duden en contactarnos_📱"
            payload = json.dumps({
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": f"{phone}",
                "type": "text",
                "text": {
                    "preview_url": False,
                    "body": f"{message}"
                }
            })
            return payload
    except Exception as ex:
        print("[ERROR] payload_doubt_message")
        print("[ERROR] ", ex)


def send_response(payload_body):
    try:
        token = os.environ.get("TOKEN_WA")
        url = f"https://graph.facebook.com/v17.0/{os.getenv('ID_WA')}/messages"
        payload = payload_body
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }
        response = requests.request("POST", url, headers=headers, data=payload)
        test = response
    except Exception as ex:
        print("[ERROR] send_response")
        print("[ERROR] ", ex)


def response_button(phone, name, payload, wa_id, timestamp, type):
    try:
        message_out = ""
        if payload == "No puedo acompañarlos":
            message_out = "Despedida enviada"
        elif payload == "Más información":
            message_out = "Información enviada"
        elif payload == "confirm":
            message_out = "Datos enviados"
        elif payload == "no_confirm":
            message_out = "Despedida enviada"
        elif payload == "Aclarar una duda":
            message_out = "Mensaje respondido"
        elif payload == "No tengo dudas":
            message_out = "Despedida enviada"
        elif payload == "Datos de pago":
            message_out = "Datos enviados"

        if type == "confirm":
            insert_message(phone, str(name), str(payload), message_out, wa_id, timestamp, 'confirm')
            body = payload_confirm(phone, name, payload)
            send_response(body)
            return True
        elif type == "food_confirm":
            insert_message(phone, str(name), str(payload), message_out, wa_id, timestamp, 'food_confirm')
            body = payload_confirm_food(phone, str(name), payload)
            send_response(body)
            return True
        elif type == "persons_confirm":
            insert_message(phone, str(name), str(payload), message_out, wa_id, timestamp, 'persons_confirm')
            id_guest = get_id_by_phone(phone[3:])
            insert_persons_confirm(id_guest, str(payload), 1)
            body = payload_persons_confirm(phone)
            send_response(body)
            return True
        elif type == "doubt":
            insert_message(phone, str(name), str(payload), message_out, wa_id, timestamp, 'doubt')
            body = payload_doubt_message(phone, payload)
            send_response(body)
            return True
        elif type == "payment_hotel":
            insert_message(phone, str(name), str(payload), message_out, wa_id, timestamp, 'hotel_pay')
            body = payload_hotel_pay(phone)
            send_response(body)
            return True
    except Exception as ex:
        print("[ERROR] response_button")
        print("[ERROR] ", ex)
        return False


def alert_admin(phone, name, message, phone_client):
    try:
        token = os.environ.get("TOKEN_WA")
        url = f"https://graph.facebook.com/v17.0/{os.getenv('ID_WA')}/messages"
        payload = json.dumps(
            {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": f"{phone}",
                "type": "template",
                "template": {
                    "name": "alerta_de_mensaje",
                    "language": {"code": "es_MX"},
                    "components": [
                        {
                            "type": "body",
                            "parameters": [{"type": "text", "text": f"{name}"}, {"type": "text", "text": f"{message}"}],
                        },
                    ],
                },
            }
        )
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }
        response = requests.request("POST", url, headers=headers, data=payload)
        response_text = json.loads(response.text)
        insert_message(phone_client, str(name), str(message), "alerta_enviada", response_text["messages"][0]["id"],
                       datetime.datetime.now().timestamp(), 'alert')
        return response.status_code
    except Exception as ex:
        print("[ERROR] alert_admin")
        print("[ERROR] ", ex)
        return False


def response_text(sender_id, name, text, wa_id, timestamp):
    try:
        if name == "admin":
            message_admin = "Si deseas contestar a algún invitado, recuerda hacerlo como una respuesta a la conversación para saber el destinatario de tu mensaje"
            send_response_bot(sender_id, message_admin, False, "message_text", sender_id, str(name))
            return True
        else:
            response = bot_chat(text)
            if response != "":

                if response != "duda_invitado":
                    insert_message(sender_id, str(name), str(text), str(response), wa_id, timestamp, 'text')
                    send_response_bot(sender_id, str(response), False, "message_text", sender_id, str(name))
                else:
                    flag = get_flag_hrs(sender_id[3:])
                    insert_message(sender_id, str(name), str(text), str(response), wa_id, timestamp, 'text')
                    if flag == 1:
                        message_admin = f"*Mensaje de {name}*: {text}"
                        send_response_bot(os.getenv("ADMIN_PHONE"), str(message_admin), False, "admin_alert",
                                          sender_id,
                                          str(name))
                    elif flag == 0:
                        alert_admin(os.getenv("ADMIN_PHONE"), str(name), str(text), sender_id)
            return True

    except Exception as ex:
        print("[ERROR] response_text")
        print("[ERROR] ", ex)
        return False


def get_phone_id_wa(id_wa):
    try:
        conn = connect_db()
        cur = conn.cursor()
        sql = f"SELECT DISTINCT phone FROM contacts c INNER JOIN messages m ON m.contact_id= c.id WHERE m.id_wa = '{id_wa}'"
        cur.execute(sql)
        phone = cur.fetchone()[0]
        conn.close()
        return phone
    except Exception as ex:
        print("[ERROR] get_phone_id_wa")
        print("[ERROR] ", ex)
        return False


def get_flag_hrs(phone):
    try:
        conn = connect_db()
        cur = conn.cursor()
        sql = f"SELECT DISTINCT CASE WHEN TIMESTAMPDIFF(MINUTE, max(m.created_date), now()) < 1400 THEN 1 ELSE 0 END mark_type FROM contacts c INNER JOIN messages m ON m.contact_id = c.id WHERE phone like '%{phone}' and message_out='duda_invitado'"
        cur.execute(sql)
        flag = cur.fetchone()[0]
        conn.close()
        return flag
    except Exception as ex:
        print("[ERROR] get_flag_hrs")
        print("[ERROR] ", ex)
        return False


def response_admin(response_id_wa, message):
    phone = get_phone_id_wa(response_id_wa)
    try:
        send_response_bot(phone, str(message), False, "message_text", phone, get_name_by_phone(phone[3:]))
        return True
    except Exception as ex:
        print("[ERROR] response_admin")
        print("[ERROR] ", ex)
        return False


def response_media(phone, name, wa_id, text, timestamp, filename):
    try:
        flag = get_flag_hrs(phone[3:])

        if 'comprobante' in text.lower():
            media_id = text[text.find(':') + 1:]
            mime_type = get_mime_type(media_id)
            insert_message(phone, str(name), str(mime_type), str('enviado_admin'), wa_id, timestamp, 'media')
            message_admin = f"*Mensaje de {name}*: {mime_type}"
            send_response_bot(os.getenv("ADMIN_PHONE"), str(message_admin), False, "admin_alert", phone, str(name))
            response = send_response_media(os.getenv("ADMIN_PHONE"), mime_type, media_id, filename)
            if response == 200:
                return True
            else:
                return False
        else:
            if flag == 1:
                media_id=text
                mime_type = get_mime_type(media_id)
                message_admin = f"*Mensaje de {name}*: {mime_type}"
                send_response_bot(os.getenv("ADMIN_PHONE"), str(message_admin), False, "admin_alert", phone,
                                  str(name))
                response = send_response_media(os.getenv("ADMIN_PHONE"), mime_type, media_id, filename)
                if response != 200:
                    return False
                else:
                    return True
            elif flag == 0:
                media_id = text
                alert_admin(os.getenv("ADMIN_PHONE"), str(name), str('Comprobante:' + media_id), phone)
                return True
    except Exception as ex:
        print("[ERROR] response_media")
        print("[ERROR] ", ex)
        return False


def send_response_media(phone, mime_type, id, filename):
    try:
        token = os.environ.get("TOKEN_WA")
        url = f"https://graph.facebook.com/v17.0/{os.getenv('ID_WA')}/messages"
        payload = ""
        if mime_type == "image/jpeg":
            payload = json.dumps({
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": f"{phone}",
                "type": "image",
                "image": {
                    "id": f"{id}",
                }
            })
        elif mime_type == "application/pdf":
            payload = json.dumps({
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": f"{phone}",
                "type": "document",
                "document": {
                    "id": f"{id}",
                    "filename": f"{filename}"
                }
            })
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }
        response = requests.request("POST", url, headers=headers, data=payload)
        return response.status_code
    except Exception as ex:
        print("[ERROR] send_response_media")
        print("[ERROR] ", ex)
        return False


def get_mime_type(id):
    try:
        token = os.environ.get("TOKEN_WA")
        url = f"https://graph.facebook.com/v17.0/{int(id)}"
        payload = {}
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }
        response = requests.request("GET", url, headers=headers, data=payload)
        mime_type = response.json()["mime_type"]
        return mime_type
    except Exception as ex:
        print("[ERROR] get_mime_type")
        print("[ERROR] ", ex)
        return False

# if __name__ == "__main__":
#     response_media = get_media_url('1032020891477027')
#     url = response_media['url']
#     id = response_media['sha256']
#     media_type = response_media['mime_type']
#     get_media(url, id, media_type)
