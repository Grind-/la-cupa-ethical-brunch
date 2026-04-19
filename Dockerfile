# Verwende das Node.js 14-Alpine-Image als Basis
FROM node:14-alpine

# Arbeitsverzeichnis erstellen
WORKDIR /app

# Abhängigkeiten installieren
COPY package*.json ./
RUN npm install

# App-Code kopieren
COPY . .

# Port, auf dem die App läuft
EXPOSE 3000

# Startbefehl
CMD ["node", "app.js"]