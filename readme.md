Pour installer les requirements : python -m pip install -r requirements.txt

Copiez `.env.example` vers `.env`, puis remplacez au minimum `SECRET_KEY` et `resend_api_key`.
Pour lancer le serveur : python -m uvicorn app.main:app --reload
Accedez a l'interface de test par le lien exact : http://127.0.0.1:8000/docs