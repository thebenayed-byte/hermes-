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
# CONFIGURATION SESSION
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
# ============================================================

clients = {}


# ============================================================
# UTILISATEURS WEB
# ============================================================

utilisateurs = {}


# ============================================================
# SESSIONS WEBSOCKET
# ============================================================

sessions_ws = {}


# ============================================================
# PAGE ACCUEIL
# ============================================================

@app.get(
    "/",
    response_class=HTMLResponse
)
async def accueil(request: Request):

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
async def login(request: Request):

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
async def auth_google(request: Request):

    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:

        return HTMLResponse(
            """
            <h1>Google OAuth non configuré</h1>

            <p>
            GOOGLE_CLIENT_ID et GOOGLE_CLIENT_SECRET
            sont absents des variables Render.
            </p>
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
                "Utilisateur Google"
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
async def auth_facebook(request: Request):

    if not FACEBOOK_APP_ID or not FACEBOOK_APP_SECRET:

        return HTMLResponse(
            """
            <h1>Facebook OAuth non configuré</h1>

            <p>
            FACEBOOK_APP_ID et FACEBOOK_APP_SECRET
            sont absents des variables Render.
            </p>
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
                "fields":
                "id,name,picture"
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
# CONNEXION INVITÉ
# ============================================================

@app.get(
    "/auth/guest"
)
async def auth_guest(
    request: Request
):

    utilisateur = {

        "provider":
        "guest",

        "id":
        "guest_" +
        secrets.token_hex(8),

        "nom":
        "Invité_" +
        secrets.token_hex(3),

        "email":
        "",

        "photo":
        ""
    }

    request.session[
        "utilisateur"
    ] = utilisateur

    print(
        "[GUEST LOGIN]",
        utilisateur
    )

    return RedirectResponse(
        "/dashboard",
        status_code=302
    )


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
# CREATION TOKEN WEBSOCKET
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
            None
        }

    nettoyer_tokens()

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

    return {

        "connecte":
        True,

        "token":
        token,

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
        )
    }


# ============================================================
# NETTOYAGE TOKENS
# ============================================================

def nettoyer_tokens():

    maintenant = time.time()

    expires = []

    for token, session in list(
        sessions_ws.items()
    ):

        created = session.get(
            "created",
            maintenant
        )

        if maintenant - created > 600:

            expires.append(
                token
            )

    for token in expires:

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
# STATUS
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

        # ----------------------------------------------------
        # POUR LA VERSION FINALE :
        # TOKEN OBLIGATOIRE
        # ----------------------------------------------------

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
        # VERIFICATION
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
        # IDENTITE
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
        # TOKEN UTILISÉ
        # ====================================================

        sessions_ws.pop(
            token,
            None
        )

        # ====================================================
        # COMPTE DEJA CONNECTE
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

        print(
            f"[+] {nom} connecté"
        )

        print(
            f"    Provider : {provider}"
        )

        print(
            f"    Email : {utilisateur_email}"
        )

        print(
            f"    Clients : {list(clients.keys())}"
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

            try:

                data = json.loads(
                    texte
                )

            except json.JSONDecodeError:

                await websocket.send_text(
                    json.dumps(
                        {
                            "type":
                            "erreur",

                            "message":
                            "Format JSON invalide."
                        },
                        ensure_ascii=False
                    )
                )

                continue

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

                # ---------------------------------------------
                # L'EXPEDITEUR EST TOUJOURS LE COMPTE AUTHENTIFIE
                # ---------------------------------------------

                expediteur = nom

                if not destinataire:

                    await websocket.send_text(
                        json.dumps(
                            {
                                "type":
                                "erreur",

                                "message":
                                "Destinataire manquant."
                            },
                            ensure_ascii=False
                        )
                    )

                    continue

                if not message:

                    await websocket.send_text(
                        json.dumps(
                            {
                                "type":
                                "erreur",

                                "message":
                                "Message vide."
                            },
                            ensure_ascii=False
                        )
                    )

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

                # ---------------------------------------------
                # DESTINATAIRE
                # ---------------------------------------------

                if destinataire in clients:

                    cible = clients[
                        destinataire
                    ]

                    websocket_cible = cible[
                        "websocket"
                    ]

                    try:

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

                        # -------------------------------------
                        # CONFIRMATION EXPEDITEUR
                        # -------------------------------------

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

                        print(
                            f"[MESSAGE] "
                            f"{expediteur} -> "
                            f"{destinataire} : "
                            f"{message}"
                        )

                    except Exception as e:

                        print(
                            "[ERREUR ENVOI]",
                            e
                        )

                        await websocket.send_text(
                            json.dumps(
                                {

                                    "type":
                                    "erreur",

                                    "message":
                                    "Impossible de contacter le destinataire."

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
                        }
                    )
                )

            # =================================================
            # CHANGEMENT DE NOM
            # =================================================

            elif type_message == "changer_nom":

                nouveau_nom = data.get(
                    "nouveau_nom"
                )

                if not nouveau_nom:

                    continue

                nouveau_nom = str(
                    nouveau_nom
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
                    nouveau_nom != nom
                    and nouveau_nom in clients
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

                informations = clients.pop(
                    ancien_nom
                )

                nom = nouveau_nom

                clients[nom] = informations

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

                print(
                    f"[NOM] {ancien_nom} -> {nom}"
                )

    except WebSocketDisconnect:

        print(
            f"[-] {nom} déconnecté"
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
            f"    Clients : {list(clients.keys())}"
        )


# ============================================================
# ABOUT
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
        "Institut Bassora"
    }
