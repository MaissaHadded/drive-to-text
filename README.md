# Drive-to-Text

POC web pour lister les PDF et images d’un dossier Google Drive public, en
extraire le texte avec le moteur adapté, puis exporter les résultats en JSON.

## Architecture

- `app/drive.py` valide les liens, interroge l’API Google Drive v3 sans OAuth,
  filtre les formats supportés et télécharge les fichiers avec une limite de taille.
- `app/extract.py` utilise pypdf pour les PDF natifs et Tesseract OCR pour les
  images PNG/JPG/JPEG.
- `app/main.py` expose l’API FastAPI. Les lots sont traités en arrière-plan avec
  un état indépendant par document ; une erreur n’interrompt pas les autres.
- `app/static/` contient l’interface responsive sans étape de compilation.

FastAPI et Python offrent une API locale simple et testable. pypdf est retenu
pour éviter une dépendance PDF AGPL ; Tesseract est auto-hébergeable et prend
en charge le français, l’anglais et l’arabe.

## Prérequis

- Python 3.11+
- Une clé API Google Cloud avec l’API Google Drive activée
- Tesseract OCR installé localement avec les données de langue voulues, ou Docker

La clé API est utilisée uniquement côté serveur pour lire les métadonnées et
télécharger les fichiers publics. Aucun accès OAuth ni document privé n’est pris
en charge. Une clé API Google Cloud est généralement soumise aux conditions
d’utilisation de Google ; configurez des restrictions adaptées dans Google Cloud
Console.

## Lancement local

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Renseignez `GOOGLE_DRIVE_API_KEY` dans `.env`, puis lancez le serveur :

```powershell
python -m uvicorn app.main:app --reload
```

Ouvrez <http://127.0.0.1:8000>. Les petites images sont agrandies avant OCR.
Pour OCR hors Docker, installez Tesseract et les données de langue `fra` et `eng`
pour le français, `eng` pour l’anglais, ou `ara` et `eng` pour l’arabe.

## Docker

Après avoir renseigné la clé dans `.env` :

```powershell
docker compose up --build
```

L’application est disponible sur <http://localhost:8000>. L’image installe
Tesseract et les langues françaises, anglaises et arabes.

## Tests

```powershell
python -m pytest -q
```

## Format de sortie

Un export représentatif est fourni dans [`sample-output.json`](sample-output.json).
Chaque entrée contient les métadonnées du fichier, un statut (`pending`,
`processing`, `done` ou `failed`), la méthode d’extraction, le texte ou une
erreur.

## Limites et suites possibles

- Google Drive peut refuser l’accès si le dossier n’est pas publiquement lisible,
  si la clé API est absente/mal configurée, ou si les quotas sont dépassés.
- Les fichiers de plus de 20 Mo sont refusés par défaut (`MAX_FILE_SIZE_MB`).
- Les PDF sans couche texte sont signalés en échec ; l’OCR des pages PDF scannées
  n’est pas inclus dans ce POC.
- Les états de lots sont conservés en mémoire : un redémarrage du serveur les efface.
- Pour la production : stockage durable des lots, authentification, quotas,
  antivirus, limitation de débit et traitement PDF scanné isolé.

## Licence

Le projet est publié sous MIT. Les principales dépendances et leurs licences
sont répertoriées dans [`LICENSES.md`](LICENSES.md).
