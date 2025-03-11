# AiCoder - Chatovací aplikace s lokálními LLM modely

Moderní webová aplikace postavená na FastAPI, která umožňuje komunikaci s lokálními LLM modely prostřednictvím Ollama. Aplikace využívá Jinja2 šablony, HTMX pro dynamické interakce a Bootstrap pro stylování.

## Technologický Stack a jeho výhody

- **FastAPI**: Moderní, rychlý (vysoce výkonný) webový framework pro Python. Poskytuje automatickou dokumentaci API, validaci dat a asynchronní podporu.
- **Ollama**: Nástroj pro spouštění lokálních LLM modelů bez nutnosti cloudových služeb, což zajišťuje soukromí dat a nižší latenci.
- **HTMX**: Umožňuje vytvářet moderní uživatelské rozhraní přímo z HTML, bez nutnosti psát JavaScript. Zjednodušuje vývoj interaktivních prvků.
- **Bootstrap 5**: CSS framework poskytující responzivní design a moderní komponenty UI, což urychluje vývoj front-endu.
- **Jinja2**: Výkonný šablonovací systém pro Python, který umožňuje oddělení logiky aplikace od prezentační vrstvy.
- **SSE (Server-Sent Events)**: Technologie pro streamování dat ze serveru do prohlížeče v reálném čase, ideální pro postupné generování odpovědí LLM.
- **Docker Compose**: Nástroj pro definici a spouštění více-kontejnerových Docker aplikací, který zajišťuje konzistentní prostředí napříč různými systémy.

## Funkce

- Integrace s Ollama pro spouštění lokálních LLM modelů
- Možnost výběru různých modelů (llama3.2:1b, qwen2.5-coder:1.5b, atd.)
- Streamování odpovědí v reálném čase
- Responzivní design pro mobilní i desktopové zařízení
- Jednoduchý a intuitivní uživatelský interface

## Instalace

### Požadavky

- Python 3.8+
- [Ollama](https://ollama.ai/) nainstalovaná a běžící na portu 11434
- Docker a Docker Compose (volitelně pro kontejnerizované nasazení)

### Kroky instalace

1. Naklonujte tento repozitář
2. Vytvořte virtuální prostředí:

```bash
python3 -m venv venv
```

3. Aktivujte virtuální prostředí:

```bash
# Na macOS/Linux
source venv/bin/activate

# Na Windows
venv\Scripts\activate
```

4. Nainstalujte závislosti:

```bash
pip install fastapi uvicorn httpx jinja2 python-multipart sse-starlette pydantic
```

5. Stáhněte potřebné modely pomocí Ollama:

```bash
# Stáhnout llama3.2 1B model
curl -X POST http://localhost:11434/api/pull -d '{"name":"llama3.2:1b"}'

# Stáhnout qwen2.5-coder 1.5B model
curl -X POST http://localhost:11434/api/pull -d '{"name":"qwen2.5-coder:1.5b"}'
```

## Spuštění aplikace

Aktivujte virtuální prostředí a spusťte vývojový server:

```bash
source venv/bin/activate  # Na macOS/Linux
python main.py
```

Nebo použijte uvicorn přímo:

```bash
uvicorn main:app --reload
```

Aplikace bude dostupná na adrese http://localhost:8000

## Spuštění s Docker Compose

Alternativně můžete spustit Ollama službu pomocí Docker Compose:

1. Ujistěte se, že máte nainstalovaný Docker a Docker Compose
2. Spusťte Ollama službu:

```bash
docker-compose up -d
```

3. Stáhněte potřebné modely:

```bash
# Stáhnout llama3.2 1B model
curl -X POST http://localhost:11434/api/pull -d '{"name":"llama3.2:1b"}'

# Stáhnout qwen2.5-coder 1.5B model
curl -X POST http://localhost:11434/api/pull -d '{"name":"qwen2.5-coder:1.5b"}'
```

4. Spusťte aplikaci podle pokynů v sekci "Spuštění aplikace"

### Poznámky k Docker konfiguraci

Docker Compose konfigurační soubor (`docker-compose.yml`) nastavuje:
- Ollama službu na portu 11434
- Perzistentní úložiště pro modely pomocí Docker volume
- Automatický restart služby v případě selhání

Pro uživatele s NVIDIA GPU je v konfiguračním souboru připraven zakomentovaný kód pro aktivaci GPU akcelerace.

## Struktura projektu

```
/
├── main.py              # Vstupní bod FastAPI aplikace
├── ollama_client.py     # Klient pro komunikaci s Ollama API
├── static/              # Statické soubory
│   ├── css/             # CSS styly
│   │   └── styles.css   # Vlastní CSS
│   └── js/              # JavaScript soubory
│       └── main.js      # Vlastní JavaScript
└── templates/           # Jinja2 šablony
    ├── index.html       # Hlavní šablona stránky
    └── partials/        # Částečné šablony
        ├── message.html         # Šablona pro zprávy
        ├── messages.html        # Šablona pro seznam zpráv
        └── model_selector.html  # Šablona pro výběr modelu
```

## Použití aplikace

1. Otevřete aplikaci v prohlížeči na adrese http://localhost:8000
2. Vyberte LLM model z rozbalovacího seznamu
3. Zadejte zprávu do textového pole a odešlete
4. Sledujte, jak model generuje odpověď v reálném čase

## Řešení problémů

- Ujistěte se, že Ollama běží na portu 11434
- Pokud dochází k chybám s pamětí, zkuste použít menší model (např. llama3.2:1b)
- Pro lepší výkon při programovacích úlohách doporučujeme model qwen2.5-coder:1.5b

## Správa ML modelů v Ollama

### Zobrazení dostupných modelů

Pro zobrazení všech nainstalovaných modelů:

```bash
curl http://localhost:11434/api/tags
```

Nebo pomocí Ollama CLI:

```bash
ollama list
```

### Přidání nového modelu

Pro stažení a instalaci nového modelu:

```bash
# Obecný formát
curl -X POST http://localhost:11434/api/pull -d '{"name":"jméno_modelu:tag"}'

# Příklad: Stažení modelu Mistral 7B
curl -X POST http://localhost:11434/api/pull -d '{"name":"mistral:7b"}'

# Příklad: Stažení modelu CodeLlama 7B
curl -X POST http://localhost:11434/api/pull -d '{"name":"codellama:7b"}'
```

### Odebrání modelu

Pro odstranění modelu, který již nepotřebujete:

```bash
# Obecný formát
curl -X DELETE http://localhost:11434/api/delete -d '{"name":"jméno_modelu:tag"}'

# Příklad: Odstranění modelu llama2
curl -X DELETE http://localhost:11434/api/delete -d '{"name":"llama2:latest"}'
```

### Aktualizace aplikace pro použití nového modelu

Po přidání nového modelu můžete upravit soubor `main.py` a změnit výchozí model:

```python
# Změňte tuto řádku
DEFAULT_MODEL = "llama3.2:1b"
# Na nový model
DEFAULT_MODEL = "jméno_nového_modelu:tag"
```

Nový model se také automaticky objeví v rozbalovacím seznamu modelů v uživatelském rozhraní aplikace.

## Licence

MIT
