import os
import requests
from dotenv import load_dotenv
from google import genai
from google.genai.errors import ClientError

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY não encontrada no .env")

client = genai.Client(api_key=API_KEY)

print(f"API KEY carregada: {API_KEY[:10]}...\n")


print("=== 1. MODELOS DISPONÍVEIS ===\n")

model_names = []

try:
    models = client.models.list()

    for model in models:
        model_names.append(model.name.replace("models/", ""))

        print(f"Nome: {model.name}")
        print(f"Display: {getattr(model, 'display_name', None)}")
        print("-" * 80)

except Exception as e:
    print("Erro ao listar modelos:")
    print(repr(e))


print("\n=== 2. HEADERS / POSSÍVEIS LIMITES DA API ===\n")

try:
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}"
    response = requests.get(url, timeout=30)

    print("Status:", response.status_code)

    found = False

    for k, v in response.headers.items():
        if "rate" in k.lower() or "limit" in k.lower() or "quota" in k.lower():
            print(f"{k}: {v}")
            found = True

    if not found:
        print("Nenhum header de rate limit/quota foi retornado pela API.")

except Exception as e:
    print("Erro ao consultar headers:")
    print(repr(e))


print("\n=== 3. TESTE PRÁTICO DOS PRINCIPAIS MODELOS ===\n")

test_models = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.5-pro",
    "gemini-pro-latest",
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
]

for model_name in test_models:
    print(f"\nTestando: {model_name}")

    if model_name not in model_names:
        print("STATUS: não apareceu na lista de modelos disponíveis")
        continue

    try:
        response = client.models.generate_content(
            model=model_name,
            contents="Responda apenas: OK"
        )

        print("STATUS: FUNCIONANDO")
        print("Resposta:", response.text)

    except ClientError as e:
        print("STATUS: ERRO DA API")

        try:
            print("Código:", e.code)
        except Exception:
            pass

        print("Erro completo:")
        print(e)

    except Exception as e:
        print("STATUS: ERRO INESPERADO")
        print(repr(e))


print("\n=== 4. RESUMO ===\n")
print("Se apareceu 429 RESOURCE_EXHAUSTED, é limite/quota.")
print("Se apareceu 403, pode ser permissão/API key/modelo bloqueado.")
print("Se apareceu 404, o nome do modelo não está disponível para uso.")
print("A API Gemini não costuma retornar 'interações restantes' diretamente pelo SDK.")