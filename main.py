from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth

import json
import os
import secrets
import time


# ============================================================
# BENPOPUP SERVER
# ============================================================
#
# Créé par :
# Abdallah Ben Ayed
# thebenayed@gmail.com
# Institut Bassora
#
# ============================================================

app = FastAPI(
    title="BenPopup Server"
)


# ============================================================
# SESSION
# ============================================================

SESSION_SECRET = os.environ.get(
    "SESSION_SECRET",
    "CHANGE-ME-IN-RENDER"
)

app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    session_cookie="benpopup_session",
    max_age=60 * 60 * 24 * 30,
    https_only=True,
    same_site="lax"
)


# ============================================================
# TEMPLATES
# ============================================================

templates = Jinja2Templates(
    directory="templates"
)


# ============================================================
# OAUTH
# ============================================================

oauth = OAuth()


# ============================================================
# GOOGLE
# ============================================================

GOOGLE_CLIENT_ID = os.environ.get(
    "GOOGLE_CLIENT_ID"
)

GOOGLE_CLIENT_SECRET = os.environ.get(
    "GOOGLE_CLIENT_SECRET"
)


if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:

    oauth.register(
        name="google",

        client_id=GOOGLE_CLIENT_ID,

        client_secret=GOOGLE_CLIENT_SECRET,

        server_metadata_url=
            "https://accounts.google.com/.well-known/openid-configuration",

        client_kwargs={
            "scope": "openid email profile"
        }
    )


# ============================================================
# FACEBOOK
# ============================================================

FACEBOOK_APP_ID = os.environ.get(
    "FACEBOOK_APP_ID"
)

FACEBOOK_APP_SECRET = os.environ.get(
    "FACEBOOK_APP_SECRET"
)


if FACEBOOK_APP_ID and FACEBOOK_APP_SECRET:

    oauth.register(
        name="facebook",

        client_id=FACEBOOK_APP_ID,

        client_secret=FACEBOOK_APP_SECRET,

        authorize_url=
            "https://www.facebook.com/v23.0/dialog/oauth",

        access_token_url=
            "https://graph.facebook.com/v23.0/oauth/access_token",

        api_base_url=
            "https://graph.facebook.com/v23.0/",

        client_kwargs={
            "scope": "public_profile"
        }
    )


# ============================================================
# CLIENTS CONNECTÉS
#
# Structure :
#
# clients = {
#     "Abdallah": {
#         "websocket": websocket,
#         "id": "...",
#         "email": "...",
#         "provider": "google"
#     }
# }
#
# ============================================================

clients = {}


# ============================================================
# UTILISATEURS WEB CONNECTÉS
# ============================================================

utilisateurs = {}


# ============================================================
# TOKENS WEBSOCKET
# ============================================================

sessions_ws = {}


# ============================================================
# PAGE PRINCIPALE
# ============================================================

@app.get(
    "/",
    response_class=HTMLResponse
)
async def accueil(
    request: Request
):

    utilisateur = request.session.get(
        "utilisateur"
    )

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "request": request,
            "utilisateur": utilisateur,
            "clients": len(clients)
        }
    )


# ============================================================
# LOGIN
# ============================================================

@app.get(
    "/login",
    response_class=HTMLResponse
)
async def login(
    request: Request
):

    utilisateur = request.session.get(
        "utilisateur"
    )

    if utilisateur:

        return RedirectResponse(
            "/dashboard",
            status_code=302
        )

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "request": request,

            "google_active":
                bool(
                    GOOGLE_CLIENT_ID
                    and GOOGLE_CLIENT_SECRET
                ),

            "facebook_active":
                bool(
                    FACEBOOK_APP_ID
                    and FACEBOOK_APP_SECRET
                )
        }
    )


# ============================================================
# GOOGLE LOGIN
# ============================================================

@app.get(
    "/auth/google"
)
async def auth_google(
    request: Request
):

    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:

        return HTMLResponse(
            """
            <h1>Google OAuth non configuré</h1>

            <p>
            GOOGLE_CLIENT_ID ou
            GOOGLE_CLIENT_SECRET est manquant.
            </p>

            <a href="/login">
                Retour
            </a>
            """,
            status_code=500
        )

    redirect_uri = request.url_for(
        "auth_google_callback"
    )

    return await oauth.google.authorize_redirect(
        request,
        redirect_uri
    )


# ============================================================
# GOOGLE CALLBACK
# ============================================================

@app.get(
    "/auth/google/callback",
    name="auth_google_callback"
)
async def auth_google_callback(
    request: Request
):

    try:

        token = await oauth.google.authorize_access_token(
            request
        )

        user_info = token.get(
            "userinfo"
        )

        if not user_info:

            user_info = await oauth.google.userinfo(
                token=token
            )

        utilisateur = {

            "provider":
                "google",

            "id":
                user_info.get(
                    "sub"
                ),

            "nom":
                user_info.get(
                    "name",
                    "Utilisateur"
                ),

            "email":
                user_info.get(
                    "email",
                    ""
                ),

            "photo":
                user_info.get(
                    "picture",
                    ""
                )
        }

        request.session[
            "utilisateur"
        ] = utilisateur

        email = utilisateur.get(
            "email"
        )

        if email:

            utilisateurs[email] = utilisateur

        print(
            "[GOOGLE LOGIN]",
            utilisateur
        )

        return RedirectResponse(
            "/dashboard",
            status_code=302
        )

    except Exception as e:

        print(
            "[GOOGLE ERROR]",
            e
        )

        return HTMLResponse(
            f"""
            <h1>Erreur Google</h1>

            <p>{e}</p>

            <a href="/login">
                Retour
            </a>
            """,
            status_code=500
        )


# ============================================================
# FACEBOOK LOGIN
# ============================================================

@app.get(
    "/auth/facebook"
)
async def auth_facebook(
    request: Request
):

    if not FACEBOOK_APP_ID or not FACEBOOK_APP_SECRET:

        return HTMLResponse(
            """
            <h1>Facebook OAuth non configuré</h1>

            <p>
            FACEBOOK_APP_ID ou
            FACEBOOK_APP_SECRET est manquant.
            </p>

            <a href="/login">
                Retour
            </a>
            """,
            status_code=500
        )

    redirect_uri = request.url_for(
        "auth_facebook_callback"
    )

    return await oauth.facebook.authorize_redirect(
        request,
        redirect_uri
    )


# ============================================================
# FACEBOOK CALLBACK
# ============================================================

@app.get(
    "/auth/facebook/callback",
    name="auth_facebook_callback"
)
async def auth_facebook_callback(
    request: Request
):

    try:

        token = await oauth.facebook.authorize_access_token(
            request
        )

        response = await oauth.facebook.get(
            "me",
            token=token,
            params={
                "fields": "id,name,picture"
            }
        )

        user_info = response.json()

        photo = ""

        try:

            photo = (
                user_info
                .get("picture", {})
                .get("data", {})
                .get("url", "")
            )

        except Exception:

            photo = ""

        utilisateur = {

            "provider":
                "facebook",

            "id":
                user_info.get(
                    "id"
                ),

            "nom":
                user_info.get(
                    "name",
                    "Utilisateur Facebook"
                ),

            "email":
                "",

            "photo":
                photo
        }

        request.session[
            "utilisateur"
        ] = utilisateur

        print(
            "[FACEBOOK LOGIN]",
            utilisateur
        )

        return RedirectResponse(
            "/dashboard",
            status_code=302
        )

    except Exception as e:

        print(
            "[FACEBOOK ERROR]",
            e
        )

        return HTMLResponse(
            f"""
            <h1>Erreur Facebook</h1>

            <p>{e}</p>

            <a href="/login">
                Retour
            </a>
            """,
            status_code=500
        )


# ============================================================
# CONNEXION TEMPORAIRE PAR PSEUDO
#
# CETTE ROUTE EST POUR LES TESTS.
#
# Exemple :
#
# /api/test-login?pseudo=Abdallah
#
# ============================================================

@app.get(
    "/api/test-login"
)
async def test_login(
    request: Request,
    pseudo: str
):

    pseudo = pseudo.strip()

    # --------------------------------------------------------
    # Vérification
    # --------------------------------------------------------

    if not pseudo:

        return {
            "connecte": False,
            "message": "Pseudo obligatoire"
        }

    if len(pseudo) > 30:

        return {
            "connecte": False,
            "message": "Pseudo trop long"
        }

    # --------------------------------------------------------
    # Identifiant temporaire
    # --------------------------------------------------------

    utilisateur_id = (
        "test_"
        + secrets.token_hex(8)
    )

    utilisateur = {

        "provider":
            "test",

        "id":
            utilisateur_id,

        "nom":
            pseudo,

        "email":
            "",

        "photo":
            ""
    }

    # --------------------------------------------------------
    # Session navigateur
    # --------------------------------------------------------

    request.session[
        "utilisateur"
    ] = utilisateur

    print(
        "[TEST LOGIN]",
        utilisateur
    )

    return {

        "connecte":
            True,

        "message":
            "Connexion test réussie",

        "utilisateur":
            utilisateur
    }


# ============================================================
# API UTILISATEUR
# ============================================================

@app.get(
    "/api/me"
)
async def api_me(
    request: Request
):

    utilisateur = request.session.get(
        "utilisateur"
    )

    if not utilisateur:

        return {
            "connecte": False
        }

    return {

        "connecte":
            True,

        "id":
            utilisateur.get(
                "id"
            ),

        "nom":
            utilisateur.get(
                "nom"
            ),

        "email":
            utilisateur.get(
                "email"
            ),

        "provider":
            utilisateur.get(
                "provider"
            ),

        "photo":
            utilisateur.get(
                "photo",
                ""
            )
    }


# ============================================================
# CRÉER TOKEN WEBSOCKET
# ============================================================

@app.get(
    "/api/ws-token"
)
async def creer_ws_token(
    request: Request
):

    utilisateur = request.session.get(
        "utilisateur"
    )

    if not utilisateur:

        return {

            "connecte":
                False,

            "token":
                None,

            "message":
                "Utilisateur non connecté"
        }

    # --------------------------------------------------------
    # Nettoyage
    # --------------------------------------------------------

    nettoyer_tokens()

    # --------------------------------------------------------
    # Nouveau token
    # --------------------------------------------------------

    token = secrets.token_urlsafe(
        32
    )

    sessions_ws[token] = {

        "id":
            utilisateur.get(
                "id"
            ),

        "nom":
            utilisateur.get(
                "nom"
            ),

        "email":
            utilisateur.get(
                "email"
            ),

        "provider":
            utilisateur.get(
                "provider"
            ),

        "photo":
            utilisateur.get(
                "photo",
                ""
            ),

        "created":
            time.time()
    }

    print(
        "[WS TOKEN]",
        utilisateur.get("nom"),
        utilisateur.get("provider")
    )

    return {

        "connecte":
            True,

        "token":
            token,

        "nom":
            utilisateur.get(
                "nom"
            ),

        "email":
            utilisateur.get(
                "email"
            ),

        "provider":
            utilisateur.get(
                "provider"
            )
    }


# ============================================================
# NETTOYER TOKENS
# ============================================================

def nettoyer_tokens():

    maintenant = time.time()

    tokens_expires = []

    for token, session in list(
        sessions_ws.items()
    ):

        created = session.get(
            "created",
            maintenant
        )

        # Token valable 10 minutes

        if maintenant - created > 600:

            tokens_expires.append(
                token
            )

    for token in tokens_expires:

        sessions_ws.pop(
            token,
            None
        )


# ============================================================
# DASHBOARD
# ============================================================

@app.get(
    "/dashboard",
    response_class=HTMLResponse
)
async def dashboard(
    request: Request
):

    utilisateur = request.session.get(
        "utilisateur"
    )

    if not utilisateur:

        return RedirectResponse(
            "/login",
            status_code=302
        )

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={

            "request":
                request,

            "utilisateur":
                utilisateur,

            "clients":
                len(clients)
        }
    )


# ============================================================
# LOGOUT
# ============================================================

@app.get(
    "/logout"
)
async def logout(
    request: Request
):

    utilisateur = request.session.get(
        "utilisateur"
    )

    if utilisateur:

        email = utilisateur.get(
            "email"
        )

        if email:

            utilisateurs.pop(
                email,
                None
            )

    request.session.clear()

    return RedirectResponse(
        "/",
        status_code=302
    )


# ============================================================
# API STATUS
# ============================================================

@app.get(
    "/api/status"
)
async def status():

    nettoyer_tokens()

    return {

        "application":
            "BenPopup Server",

        "status":
            "online",

        "clients":
            len(clients),

        "utilisateurs":
            len(utilisateurs),

        "sessions_websocket":
            len(sessions_ws)
    }


# ============================================================
# WEBSOCKET
# ============================================================

@app.websocket(
    "/ws"
)
async def websocket_endpoint(
    websocket: WebSocket
):

    await websocket.accept()

    nom = None

    utilisateur_id = None
    utilisateur_email = None
    provider = None

    try:

        # ====================================================
        # PREMIER MESSAGE
        # ====================================================

        premier_message = (
            await websocket.receive_text()
        )

        data = json.loads(
            premier_message
        )

        if data.get(
            "type"
        ) != "connexion":

            await websocket.send_text(
                json.dumps(
                    {
                        "type":
                            "erreur",

                        "message":
                            "Connexion invalide."
                    },
                    ensure_ascii=False
                )
            )

            await websocket.close()

            return

        # ====================================================
        # TOKEN
        # ====================================================

        token = data.get(
            "token"
        )

        if not token:

            await websocket.send_text(
                json.dumps(
                    {
                        "type":
                            "erreur",

                        "message":
                            "Authentification requise."
                    },
                    ensure_ascii=False
                )
            )

            await websocket.close()

            return

        # ====================================================
        # NETTOYAGE
        # ====================================================

        nettoyer_tokens()

        # ====================================================
        # VERIFICATION TOKEN
        # ====================================================

        utilisateur = sessions_ws.get(
            token
        )

        if not utilisateur:

            await websocket.send_text(
                json.dumps(
                    {
                        "type":
                            "erreur",

                        "message":
                            "Session invalide ou expirée."
                    },
                    ensure_ascii=False
                )
            )

            await websocket.close()

            return

        # ====================================================
        # IDENTITÉ
        # ====================================================

        utilisateur_id = utilisateur.get(
            "id"
        )

        utilisateur_email = utilisateur.get(
            "email"
        )

        provider = utilisateur.get(
            "provider"
        )

        nom = utilisateur.get(
            "nom",
            "Utilisateur"
        )

        if not nom:

            nom = "Utilisateur"

        # ====================================================
        # TOKEN À USAGE UNIQUE
        # ====================================================

        sessions_ws.pop(
            token,
            None
        )

        # ====================================================
        # COMPTE DÉJÀ CONNECTÉ
        # ====================================================

        if nom in clients:

            await websocket.send_text(
                json.dumps(
                    {
                        "type":
                            "erreur",

                        "message":
                            "Ce compte est déjà connecté."
                    },
                    ensure_ascii=False
                )
            )

            await websocket.close()

            return

        # ====================================================
        # AJOUT CLIENT
        # ====================================================

        clients[nom] = {

            "websocket":
                websocket,

            "id":
                utilisateur_id,

            "email":
                utilisateur_email,

            "provider":
                provider
        }

        print()
        print(
            "========================================"
        )

        print(
            "[+] CLIENT CONNECTÉ"
        )

        print(
            "Nom :",
            nom
        )

        print(
            "ID :",
            utilisateur_id
        )

        print(
            "Provider :",
            provider
        )

        print(
            "Email :",
            utilisateur_email
        )

        print(
            "Clients :",
            list(clients.keys())
        )

        print(
            "========================================"
        )

        # ====================================================
        # CONFIRMATION
        # ====================================================

        await websocket.send_text(
            json.dumps(
                {
                    "type":
                        "connexion_ok",

                    "nom":
                        nom,

                    "id":
                        utilisateur_id,

                    "email":
                        utilisateur_email,

                    "provider":
                        provider
                },
                ensure_ascii=False
            )
        )

        # ====================================================
        # BOUCLE MESSAGES
        # ====================================================

        while True:

            texte = (
                await websocket.receive_text()
            )

            data = json.loads(
                texte
            )

            type_message = data.get(
                "type"
            )

            # =================================================
            # MESSAGE
            # =================================================

            if type_message == "message":

                destinataire = data.get(
                    "destinataire"
                )

                message = data.get(
                    "message"
                )

                # ------------------------------------------------
                # L'expéditeur vient TOUJOURS du serveur.
                # ------------------------------------------------

                expediteur = nom

                if not destinataire:

                    continue

                if not message:

                    continue

                message = str(
                    message
                ).strip()

                if not message:

                    continue

                if len(message) > 5000:

                    await websocket.send_text(
                        json.dumps(
                            {
                                "type":
                                    "erreur",

                                "message":
                                    "Message trop long."
                            },
                            ensure_ascii=False
                        )
                    )

                    continue

                # ------------------------------------------------
                # DESTINATAIRE CONNECTÉ
                # ------------------------------------------------

                if destinataire in clients:

                    cible = clients[
                        destinataire
                    ]

                    websocket_cible = cible[
                        "websocket"
                    ]

                    await websocket_cible.send_text(
                        json.dumps(
                            {
                                "type":
                                    "message",

                                "expediteur":
                                    expediteur,

                                "message":
                                    message
                            },
                            ensure_ascii=False
                        )
                    )

                    print(
                        f"[MESSAGE] "
                        f"{expediteur} -> "
                        f"{destinataire} : "
                        f"{message}"
                    )

                    # ------------------------------------------------
                    # Confirmation à l'expéditeur
                    # ------------------------------------------------

                    await websocket.send_text(
                        json.dumps(
                            {
                                "type":
                                    "message_envoye",

                                "destinataire":
                                    destinataire,

                                "message":
                                    message
                            },
                            ensure_ascii=False
                        )
                    )

                else:

                    await websocket.send_text(
                        json.dumps(
                            {
                                "type":
                                    "erreur",

                                "message":
                                    f"{destinataire} "
                                    f"n'est pas connecté."
                            },
                            ensure_ascii=False
                        )
                    )

            # =================================================
            # LISTE
            # =================================================

            elif type_message == "liste":

                liste = list(
                    clients.keys()
                )

                await websocket.send_text(
                    json.dumps(
                        {
                            "type":
                                "liste",

                            "utilisateurs":
                                liste
                        },
                        ensure_ascii=False
                    )
                )

            # =================================================
            # PING
            # =================================================

            elif type_message == "ping":

                await websocket.send_text(
                    json.dumps(
                        {
                            "type":
                                "pong"
                        },
                        ensure_ascii=False
                    )
                )

            # =================================================
            # CHANGER NOM
            # =================================================

            elif type_message == "changer_nom":

                nouveau_nom = data.get(
                    "nouveau_nom",
                    ""
                ).strip()

                if not nouveau_nom:

                    continue

                if len(nouveau_nom) > 30:

                    await websocket.send_text(
                        json.dumps(
                            {
                                "type":
                                    "erreur",

                                "message":
                                    "Nom trop long."
                            },
                            ensure_ascii=False
                        )
                    )

                    continue

                if (
                    nouveau_nom in clients
                    and
                    nouveau_nom != nom
                ):

                    await websocket.send_text(
                        json.dumps(
                            {
                                "type":
                                    "erreur",

                                "message":
                                    "Ce nom est déjà utilisé."
                            },
                            ensure_ascii=False
                        )
                    )

                    continue

                ancien_nom = nom

                client_data = clients.pop(
                    ancien_nom
                )

                nom = nouveau_nom

                clients[nom] = client_data

                print(
                    f"[NOM] "
                    f"{ancien_nom} -> "
                    f"{nom}"
                )

                await websocket.send_text(
                    json.dumps(
                        {
                            "type":
                                "nom_modifie",

                            "nom":
                                nom
                        },
                        ensure_ascii=False
                    )
                )


    # ========================================================
    # DÉCONNEXION WEBSOCKET
    # ========================================================

    except WebSocketDisconnect:

        print(
            f"[-] {nom} déconnecté"
        )

    except json.JSONDecodeError:

        print(
            f"[ERREUR JSON] {nom}"
        )

    except Exception as e:

        print(
            f"[ERREUR] {nom} : {e}"
        )

    finally:

        if nom and nom in clients:

            clients.pop(
                nom,
                None
            )

            print(
                f"[-] {nom} supprimé"
            )

        print(
            "Clients actuellement connectés :",
            list(clients.keys())
        )


# ============================================================
# API ABOUT
# ============================================================

@app.get(
    "/api/about"
)
async def about():

    return {

        "application":
            "BenPopup",

        "createur":
            "Abdallah Ben Ayed",

        "email":
            "thebenayed@gmail.com",

        "organisation":
            "Institut Bassora",

        "version":
            "1.0"
    }
