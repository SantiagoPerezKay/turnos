"""Lista los números de una cuenta de WhatsApp Business y su estado en Cloud API.

Usa WHATSAPP_TOKEN del .env (el token no se imprime).
Uso:  python -m scripts.wa_numeros [WABA_ID]   (por defecto WHATSAPP_WABA_ID)
"""

import asyncio
import sys

import httpx2

from app.config import get_settings

CAMPOS = "display_phone_number,verified_name,status,platform_type,quality_rating,name_status,code_verification_status"


async def main(waba_id: str) -> None:
    s = get_settings()
    if not s.whatsapp_token:
        sys.exit("Falta WHATSAPP_TOKEN en el .env")
    base = f"https://graph.facebook.com/{s.whatsapp_api_version}"
    headers = {"Authorization": f"Bearer {s.whatsapp_token}"}
    async with httpx2.AsyncClient(timeout=15, headers=headers) as client:
        r = await client.get(f"{base}/{waba_id}/phone_numbers", params={"fields": CAMPOS})
        if r.status_code >= 400:
            sys.exit(f"Error {r.status_code}: {r.json().get('error', {}).get('message', r.text)}")
        numeros = r.json().get("data", [])
        if not numeros:
            print("La cuenta no tiene números registrados.")
        for n in numeros:
            print(f"\n{n.get('display_phone_number')}  —  {n.get('verified_name')}")
            print(f"  Phone Number ID : {n['id']}   <- esto va en wa_phone_number_id")
            print(f"  Estado          : {n.get('status')}  (plataforma: {n.get('platform_type')})")
            print(f"  Calidad         : {n.get('quality_rating')}   Nombre: {n.get('name_status')}")

        r = await client.get(f"{base}/{waba_id}/subscribed_apps")
        if r.status_code < 400:
            apps = [a.get("whatsapp_business_api_data", {}).get("name") for a in r.json().get("data", [])]
            print(f"\nApps suscriptas a los webhooks de esta cuenta: {', '.join(filter(None, apps)) or 'ninguna'}")


if __name__ == "__main__":
    waba = sys.argv[1] if len(sys.argv) > 1 else get_settings().whatsapp_waba_id
    if not waba:
        sys.exit("Uso: python -m scripts.wa_numeros [WABA_ID]  (o definí WHATSAPP_WABA_ID en el .env)")
    asyncio.run(main(waba))
