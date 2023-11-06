import json
import os

from fastapi import HTTPException, Query
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.functions.bot_functions import log_record, get_name_by_phone, response_button, response_text, response_admin, \
    response_media

router = APIRouter()


@router.get("/")
async def verify_webhook(hub_mode: str = Query(None, alias="hub.mode"),
                         hub_challenge: int = Query(None, alias="hub.challenge"),
                         hub_verify_token: str = Query(None, alias="hub.verify_token")):
    if hub_verify_token == "bWF0dGlsZGEtYm90":
        return hub_challenge
    else:
        raise HTTPException(status_code=403, detail="Error de autenticación.")


@router.post("/")
async def receive_webhook(data: dict = None):
    try:
        if data is not None:
            response_wa = False
            json_data = json.dumps(data, indent=4)
            print("DEBUG: ", json_data)
            log_record(json_data, "webhook_log")
            data = json.loads(json_data)
            object_type = data["object"]
            entry = data["entry"][0]
            id = entry["id"]
            changes = entry["changes"][0]
            value = changes["value"]
            if "messages" in value:
                messages = value["messages"]
                for message in messages:
                    sender_id = message["from"]
                    name = get_name_by_phone(sender_id[3:])
                    wa_id = message["id"]
                    timestamp = message["timestamp"]
                    message_type = message["type"]
                    log_record(json_data, sender_id)
                    if message_type == "text":
                        text = message["text"]["body"]
                        if sender_id[3:] == os.getenv("ADMIN_PHONE"):
                            if "context" in message:
                                response_id_wa = message["context"]["id"]
                                response_wa = response_admin(response_id_wa, text)
                            elif 'comprobante' in text.lower():
                                response_media(sender_id, name, wa_id, text, timestamp, "image")
                            else:
                                response_wa = response_text(sender_id, "admin", "admin_message", wa_id, timestamp)
                        else:
                            response_wa = response_text(sender_id, name, text, wa_id, timestamp)
                    elif message_type == "button":
                        button_payload = message["button"]["payload"]
                        if button_payload == "No puedo acompañarlos" or button_payload == "Más información":
                            response_wa = response_button(sender_id, name, button_payload, wa_id, timestamp, "confirm")
                        elif button_payload == "Aclarar una duda" or button_payload == "No tengo dudas":
                            response_wa = response_button(sender_id, name, button_payload, wa_id, timestamp, "doubt")
                        elif button_payload == "Datos de pago":
                            response_wa = response_button(sender_id, name, button_payload, wa_id, timestamp,
                                                          "payment_hotel")
                        elif button_payload == "Me interesa" or button_payload == 'No, gracias':
                            response_wa = response_button(sender_id, name, button_payload, wa_id, timestamp,
                                                          "hotel_option")
                    elif message_type == "interactive":
                        if message["interactive"]["type"] == "button_reply":
                            interactive_payload = message["interactive"]["button_reply"]["id"]
                            if interactive_payload=="Reservar" or interactive_payload=="No, gracias":
                                response_wa = response_button(sender_id, name, interactive_payload, wa_id, timestamp,"hotel_appointment")
                            else:
                                response_wa = response_button(sender_id, name, interactive_payload, wa_id, timestamp,
                                                          "food_confirm")
                        elif message["interactive"]["type"] == "list_reply":
                            interactive_payload = message["interactive"]["list_reply"]["id"]
                            response_wa = response_button(sender_id, name, interactive_payload, wa_id, timestamp,
                                                          "persons_confirm")
                    elif message_type == 'image' and sender_id[3:] != os.getenv("ADMIN_PHONE"):
                        mime_type = message["image"]["mime_type"]
                        id = message["image"]["id"]
                        response_wa = response_media(sender_id, name, wa_id, id, timestamp, "image")
                    elif message_type == 'document' and sender_id[3:] != os.getenv("ADMIN_PHONE"):
                        mime_type = message["document"]["mime_type"]
                        id = message["document"]["id"]
                        filename = message["document"]["filename"]
                        response_wa = response_media(sender_id, name, wa_id, id, timestamp, filename)
                if response_wa:
                    return JSONResponse(content={"status": "mensaje recibido"}, status_code=200)
                else:
                    return JSONResponse(content={"status": "error al recibir el mensaje"}, status_code=400)
            elif "statuses" in value:
                statuses = value["statuses"]
                for status in statuses:
                    sender_id = status["recipient_id"]
                    estatus = status["status"]
                    wa_id = status["id"]
                    print("DEBUG: ", sender_id, estatus, wa_id)
                    log_record(estatus, "webhook_log")
        else:
            raise HTTPException(status_code=400, detail="No data received")
    except Exception as ex:
        print("[ERROR] receive_webhook")
        print("[ERROR] ", ex)
        return JSONResponse(content={"status": "error al recibir el mensaje"}, status_code=400)
