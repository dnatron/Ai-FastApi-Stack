#!/bin/bash

# Tento skript stahuje LLM modely do Ollama
echo "Stahuji LLM modely do Ollama..."
echo "Nejprve zkontrolujeme dostupné modely..."
curl -s http://localhost:11434/api/tags

echo -e "\n\nStahuji model llama3.2:1b (výchozí model)..."
curl -X POST http://localhost:11434/api/pull -d '{"name":"llama3.2:1b"}'

echo -e "\n\nStahuji model qwen2.5-coder:1.5b (model optimalizovaný pro programování)..."
curl -X POST http://localhost:11434/api/pull -d '{"name":"qwen2.5-coder:1.5b"}'

echo -e "\n\nStahování modelů bylo zahájeno. Tento proces může trvat několik minut v závislosti na rychlosti vašeho připojení a hardwaru."
echo "Stav stahování můžete zkontrolovat příkazem: curl http://localhost:11434/api/status"
echo -e "\nPo dokončení stahování můžete spustit aplikaci příkazem: python main.py"
