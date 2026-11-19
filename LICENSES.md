# Licences des dépendances

Versions des dépendances directes déclarées dans `requirements.txt`.
Vérifiées sur les métadonnées des versions épinglées ; les dépendances
transitives peuvent avoir leurs propres licences, à contrôler avant distribution.

| Dépendance | Version | Licence | Usage commercial en produit fermé | Rôle / remarque |
|---|---:|---|---|---|
| FastAPI | 0.115.12 | MIT | Oui | API HTTP |
| Uvicorn | 0.34.2 | BSD-3-Clause | Oui | Serveur ASGI |
| Requests | 2.32.3 | Apache-2.0 | Oui | API et téléchargement Drive |
| pypdf | 5.4.0 | BSD-3-Clause | Oui | Extraction PDF sans dépendance GPL |
| Pillow | 11.2.1 | HPND | Oui | Lecture des images |
| pytesseract | 0.3.13 | Apache-2.0 | Oui | Interface Python vers Tesseract |
| python-dotenv | 1.1.0 | BSD-3-Clause | Oui | Chargement local du fichier `.env` |
| httpx | 0.28.1 | BSD-3-Clause | Oui | Client utilisé par les tests FastAPI |
| pytest | 8.3.5 | MIT | Oui | Exécution des tests |
| Tesseract OCR | image système | Apache-2.0 | Oui | Moteur OCR fourni par Docker ; inclut les données de langue |
| Python | 3.11 | PSF-2.0 | Oui | Environnement d’exécution |

Ce POC n’intègre aucune dépendance GPL/AGPL. Le conteneur et les fichiers de
langue Tesseract sont distribués sous leurs licences respectives ; conserver
leurs notices en cas de redistribution. L’image de base Docker et les
dépendances transitives doivent également être auditées pour une distribution
commerciale.
