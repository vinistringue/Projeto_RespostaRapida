# app/services/openai_service.py

import os
import openai
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("API_KEY")

def gerar_pergunta():
    prompt = """
    Gere uma pergunta de conhecimentos gerais com:
    - enunciado
    - 4 alternativas (A, B, C, D)
    - identifique a correta
    - forneça 1 dica

    Responda em JSON no seguinte formato:
    {
        "question": "Qual é a capital da França?",
        "options": {
            "A": "Paris",
            "B": "Roma",
            "C": "Londres",
            "D": "Berlim"
        },
        "correct_option": "A",
        "tip": "É uma cidade conhecida como a cidade do amor."
    }
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.7
        )

        content = response.choices[0].message["content"]
        return eval(content)  # ou use json.loads() se garantir formato JSON puro

    except Exception as e:
        print("Erro ao gerar pergunta:", e)
        return None
