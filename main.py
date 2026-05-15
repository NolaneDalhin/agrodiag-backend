from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import httpx
import base64
import re
import os

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

@app.post("/analyser")
async def analyser_plante(image: UploadFile = File(...)):
    try:
        contenu = await image.read()
        image_b64 = base64.b64encode(contenu).decode("utf-8")
        mime_type = image.content_type or "image/jpeg"

        payload = {
            "model": "meta-llama/llama-4-scout-17b-16e-instruct",
            "messages": [{
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": """Tu es un expert en maladies des plantes qui parle a des agriculteurs simples.
Reponds STRICTEMENT ainsi sans markdown et sans termes scientifiques:
MALADIE: [nom simple de la maladie ou Plante saine]
CONFIANCE: [pourcentage, exemple: 90%]
TRAITEMENT: [conseil simple en 1 phrase, avec des produits faciles a trouver]
AGENT: [OUI si la maladie est grave et necessite un specialiste, NON sinon]"""
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{image_b64}"
                        }
                    }
                ]
            }],
            "max_tokens": 200
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=60
            )
            result = response.json()

        print("GROQ RESULT:", result)
        text = result["choices"][0]["message"]["content"]
        print("GROQ TEXT:", text)

        maladie, confiance, traitement, agent = "Inconnu", "0%", "Aucun traitement trouvé", "NON"

        for line in text.strip().split("\n"):
            line = re.sub(r'\*+', '', line).strip()
            if re.search(r'MALADIE\s*:', line, re.IGNORECASE):
                maladie = re.split(r'MALADIE\s*:', line, flags=re.IGNORECASE)[-1].strip()
            elif re.search(r'CONFIANCE\s*:', line, re.IGNORECASE):
                confiance = re.split(r'CONFIANCE\s*:', line, flags=re.IGNORECASE)[-1].strip()
            elif re.search(r'TRAITEMENT\s*:', line, re.IGNORECASE):
                traitement = re.split(r'TRAITEMENT\s*:', line, flags=re.IGNORECASE)[-1].strip()
            elif re.search(r'AGENT\s*:', line, re.IGNORECASE):
                agent = re.split(r'AGENT\s*:', line, flags=re.IGNORECASE)[-1].strip()

        return {"maladie": maladie, "confiance": confiance, "traitement": traitement, "agent": agent}

    except Exception as e:
        print(f"ERREUR: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def root():
    return {"message": "AgroDiag AI Backend opérationnel"}