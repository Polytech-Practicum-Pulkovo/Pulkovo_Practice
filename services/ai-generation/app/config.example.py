# --- GigaChat API ---
CLIENT_ID = "your-client-id"
CLIENT_SECRET = "your-client-secret"

AUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
CHAT_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"

MODEL = "GigaChat-2-Pro"
SCOPE = "GIGACHAT_API_B2B"

# Отключать проверку SSL сертификата (в проде лучше выставить False
# и настроить доверенный сертификат Минцифры)
VERIFY_SSL = False

# --- База данных ---
DB_HOST = "bd"
DB_PORT = "5432"
DB_NAME = "pulkovo"
DB_USER = "postgres"
DB_PASSWORD = "12358"
