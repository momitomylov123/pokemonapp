import os
import json
import uuid
from datetime import datetime
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import torch
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import io

# Rutas absolutas para evitar errores al ejecutar desde cualquier carpeta
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DECK_FILE = os.path.join(BASE_DIR, "deck.json")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI(title="PokeDraw AI Server")

# CORS: Permite que el celular y el navegador web se conecten
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cargar modelo CLIP al iniciar (CPU only para Arduino UNO Q)
print("Cargando modelo CLIP (descarga ~600MB la primera vez)...")
model_name = "openai/clip-vit-base-patch32"
processor = CLIPProcessor.from_pretrained(model_name)
model = CLIPModel.from_pretrained(model_name)
model.eval()
print("Modelo listo.")

# Base de conocimiento de Pokemon (descripciones para CLIP)
POKEMON_DATA = [
    {"name": "Pikachu", "desc": "yellow electric mouse pokemon with red cheeks and lightning bolt tail"},
    {"name": "Charmander", "desc": "orange lizard pokemon with flame on tail"},
    {"name": "Squirtle", "desc": "blue turtle pokemon with shell and water gun"},
    {"name": "Bulbasaur", "desc": "green dinosaur pokemon with plant bulb on back"},
    {"name": "Jigglypuff", "desc": "pink round balloon pokemon singing"},
    {"name": "Meowth", "desc": "yellow cat pokemon with coin on forehead"},
    {"name": "Psyduck", "desc": "yellow duck pokemon holding head in pain"},
    {"name": "Snorlax", "desc": "large blue sleeping pokemon"},
    {"name": "Eevee", "desc": "brown fox pokemon with fluffy collar"},
    {"name": "Mewtwo", "desc": "purple psychic pokemon with tail and tube"},
    {"name": "Charizard", "desc": "orange dragon pokemon breathing fire"},
    {"name": "Gengar", "desc": "purple ghost pokemon with sharp teeth"},
    {"name": "Machamp", "desc": "four armed fighting pokemon with belt"},
    {"name": "Alakazam", "desc": "yellow psychic pokemon holding spoons"},
    {"name": "Gyarados", "desc": "blue sea serpent pokemon with open mouth"},
]

# Pre-procesar los textos una sola vez (ahorra memoria y tiempo)
pokemon_texts = [p["desc"] for p in POKEMON_DATA]
text_inputs = processor(text=pokemon_texts, return_tensors="pt", padding=True)
with torch.no_grad():
    text_features = model.get_text_features(**text_inputs)
    text_features = text_features / text_features.norm(dim=-1, keepdim=True)


def load_deck():
    if not os.path.exists(DECK_FILE):
        return []
    with open(DECK_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_deck(deck):
    with open(DECK_FILE, "w", encoding="utf-8") as f:
        json.dump(deck, f, indent=2, ensure_ascii=False)


def get_rarity(similarity: float) -> dict:
    if similarity > 0.85:
        return {"label": "LEGENDARIO", "color": "#FFD700", "stars": 5}
    if similarity > 0.70:
        return {"label": "EPICO", "color": "#9C27B0", "stars": 4}
    if similarity > 0.50:
        return {"label": "RARO", "color": "#2196F3", "stars": 3}
    if similarity > 0.30:
        return {"label": "COMUN", "color": "#4CAF50", "stars": 2}
    return {"label": "BASICO", "color": "#9E9E9E", "stars": 1}


@app.get("/")
async def health():
    return {"status": "ok", "message": "PokeDraw AI Server funcionando"}


@app.post("/upload")
async def upload_drawing(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        img = Image.open(io.BytesIO(contents)).convert("RGB")
        img = img.resize((224, 224))

        image_inputs = processor(images=img, return_tensors="pt")

        with torch.no_grad():
            image_features = model.get_image_features(**image_inputs)
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            similarity_scores = (image_features @ text_features.T).squeeze()

        best_idx = similarity_scores.argmax().item()
        best_pokemon = POKEMON_DATA[best_idx]
        similarity = similarity_scores[best_idx].item()
        similarity_pct = max(0.0, min(1.0, (similarity + 1) / 2))

        hp = int(similarity_pct * 150 + 50)
        attack = int(similarity_pct * 120 + 30)
        rarity = get_rarity(similarity_pct)

        img_id = str(uuid.uuid4())[:8]
        img_path = os.path.join(UPLOAD_DIR, f"{img_id}.jpg")
        img.save(img_path)

        card = {
            "id": img_id,
            "pokemon": best_pokemon["name"],
            "hp": hp,
            "attack": attack,
            "similarity": round(similarity_pct, 4),
            "rarity": rarity,
            "image": f"{img_id}.jpg",
            "timestamp": datetime.now().isoformat(),
        }

        deck = load_deck()
        deck.append(card)
        save_deck(deck)

        return card

    except Exception as e:
        print(f"[ERROR SERVER] {e}")
        raise HTTPException(status_code=500, detail=f"Error procesando imagen: {str(e)}")


@app.get("/deck")
async def get_deck():
    return {"cards": load_deck()}


@app.get("/images/{filename}")
async def get_image(filename: str):
    path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Imagen no encontrada")
    return FileResponse(path)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
