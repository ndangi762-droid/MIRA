from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
from dotenv import load_dotenv
import os

# Load API key
load_dotenv("backend/.env")

# Create FastAPI app
app = FastAPI(title="MIRA")

# Allow MIRA HTML interface to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Groq client
groq_client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)


@app.get("/")
def home():
    return {
        "assistant": "MIRA",
        "status": "ONLINE",
        "message": "Boss, MIRA ready hai."
    }


@app.get("/ask")
def ask(message: str = Query(...)):

    response = groq_client.chat.completions.create(

        model="qwen/qwen3.6-27b",

        messages=[
            {
                "role": "system",
                "content": (
    "Tum MIRA ho, Boss ki personal AI assistant. "
    "Tum female AI ho, isliye apne liye hamesha feminine Hindi forms use karo, "
    "jaise 'kar sakti hoon', 'bata sakti hoon', 'help kar sakti hoon'. "
    "Boss ko hamesha 'Boss' kehkar bulao. "
    "Roman Hindi aur natural English mix mein baat karo. "
    "Hindi natural, confident aur professional rakho. "
    "Short aur clear answers do. "
    "Kabhi bhi 'kar sakta hoon' ya masculine forms use mat karo."
)
            },
            {
                "role": "user",
                "content": message
            }
        ],

        temperature=0.7,

        reasoning_effort="none",

        max_tokens=150
    )

    return {
        "assistant": "MIRA",
        "response": response.choices[0].message.content
    }