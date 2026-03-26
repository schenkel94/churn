# 1. Use uma imagem Python oficial leve
FROM python:3.9-slim

# 2. Defina o diretório de trabalho dentro do container
WORKDIR /app

# 3. Instale dependências do sistema necessárias para algumas bibliotecas de dados
# (Como você usa CSVs simples, pode não precisar de muito, mas isso garante compatibilidade)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 4. Copie o requirements.txt primeiro para aproveitar o cache do Docker
COPY requirements.txt .

# 5. Instale as dependências do Python
# Usamos o pip pré-instalado na imagem leve
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 6. Copie todo o restante dos arquivos do projeto (incluindo CSVs, PNG, assets)
COPY . .

# 7. Exponha a porta padrão que o Dash/Flask usa (8050)
EXPOSE 8050

# 8. Comando para rodar a aplicação
# O Hugging Face espera que a aplicação escute em 0.0.0.0:8050
CMD ["python", "app.py"]
