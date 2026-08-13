from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth
import json
import os

# ============================================================
# BENPOPUP SERVER
# ============================================================
# Créé par :
# Abdallah Ben Ayed
# thebenayed@gmail.com
# Institut Bassora
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
    secret_key=SESSION_SECRET
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

FACEBOOK_CLIENT_ID = os.environ.get(
    "FACEBOOK_CLIENT_ID"
)

FACEBOOK_CLIENT_SECRET = os.environ.get(
    "FACEBOOK_CLIENT_SECRET"
)

if FACEBOOK_CLIENT_ID and FACEBOOK_CLIENT_SECRET:

    oauth.register(
        name="facebook",

        client_id=FACEBOOK_CLIENT_ID,

        client_secret=FACEBOOK_CLIENT_SECRET,

        authorize_url=
            "https://www.facebook.com/v24.0/dialog/oauth",

        access_token_url=
            "https://graph.facebook.com/v24.0/oauth/access_token",

        api_base_url=
            "https://graph.facebook.com/v24.0/",

       client_kwargs={
    "scope": "public_profile"
}
        }
    )

# ============================================================
# CLIENTS WINDOWS CONNECTÉS
# ============================================================

clients = {}

# ============================================================
# UTILISATEURS WEB CONNECTÉS
# ============================================================

utilisateurs = {}

# ============================================================
# PAGE PRINCIPALE
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
            "utilisateur": utilisateur,
            "clients": len(clients)
        }
    )

# ============================================================
# PAGE LOGIN
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
            "/dashboard"
        )

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "google_active":
                bool(
                    GOOGLE_CLIENT_ID
                    and
                    GOOGLE_CLIENT_SECRET
                ),

            "facebook_active":
                bool(
                    FACEBOOK_CLIENT_ID
                    and
                    FACEBOOK_CLIENT_SECRET
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
            <h1>Google n'est pas configuré.</h1>
            <p>Vérifie les variables Google dans Render.</p>
            <a href="/login">Retour</a>
            """,
            status_code=500
        )

    google = oauth.create_client(
        "google"
    )

    redirect_uri = request.url_for(
        "auth_google_callback"
    )

    return await google.authorize_redirect(
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

        google = oauth.create_client(
            "google"
        )

        token = await google.authorize_access_token(
            request
        )

        user_info = token.get(
            "userinfo"
        )

        if not user_info:

            user_info = await google.userinfo(
                token=token
            )

        email = user_info.get(
            "email",
            ""
        )

        nom = user_info.get(
            "name",
            "Utilisateur"
        )

        photo = user_info.get(
            "picture",
            ""
        )

        utilisateur = {

            "provider": "google",

            "id": user_info.get(
                "sub"
            ),

            "nom": nom,

            "email": email,

            "photo": photo
        }

        request.session[
            "utilisateur"
        ] = utilisateur

        utilisateurs[email] = utilisateur

        print(
            f"[GOOGLE] {email} connecté"
        )

        return RedirectResponse(
            "/dashboard"
        )

    except Exception as e:

        print(
            "[GOOGLE ERROR]",
            e
        )

        return HTMLResponse(
            f"""
            <h1>Erreur Google</h1>

            <p>{str(e)}</p>

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

    if not FACEBOOK_CLIENT_ID or not FACEBOOK_CLIENT_SECRET:

        return HTMLResponse(
            """
            <h1>Facebook n'est pas configuré.</h1>

            <p>
            Vérifie FACEBOOK_CLIENT_ID et
            FACEBOOK_CLIENT_SECRET dans Render.
            </p>

            <a href="/login">
                Retour
            </a>
            """,
            status_code=500
        )

    facebook = oauth.create_client(
        "facebook"
    )

    redirect_uri = request.url_for(
        "auth_facebook_callback"
    )

    return await facebook.authorize_redirect(
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

        facebook = oauth.create_client(
            "facebook"
        )

        token = await facebook.authorize_access_token(
            request
        )

        # ----------------------------------------------------
        # RÉCUPÉRATION DES INFORMATIONS FACEBOOK
        # ----------------------------------------------------

        response = await facebook.get(
            "me",
            token=token,
            params={
                "fields":
                    "id,name,email,picture.type(large)"
            }
        )

        user_info = response.json()

        facebook_id = user_info.get(
            "id"
        )

        nom = user_info.get(
            "name",
            "Utilisateur Facebook"
        )

        email = user_info.get(
            "email",
            ""
        )

        photo = ""

        picture = user_info.get(
            "picture"
        )

        if picture:

            picture_data = picture.get(
                "data"
            )

            if picture_data:

                photo = picture_data.get(
                    "url",
                    ""
                )

        # ----------------------------------------------------
        # IDENTIFIANT DE SESSION
        # ----------------------------------------------------

        identifiant = email

        if not identifiant:

            identifiant = (
                "facebook_"
                + str(facebook_id)
            )

        utilisateur = {

            "provider": "facebook",

            "id": facebook_id,

            "nom": nom,

            "email": email,

            "photo": photo
        }

        request.session[
            "utilisateur"
        ] = utilisateur

        utilisateurs[
            identifiant
        ] = utilisateur

        print(
            f"[FACEBOOK] {nom} connecté"
        )

        return RedirectResponse(
            "/dashboard"
        )

    except Exception as e:

        print(
            "[FACEBOOK ERROR]",
            e
        )

        return HTMLResponse(
            f"""
            <h1>Erreur Facebook</h1>

            <p>{str(e)}</p>

            <a href="/login">
                Retour
            </a>
            """,
            status_code=500
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
            "/login"
        )

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "utilisateur": utilisateur,
            "clients": len(clients)
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

    request.session.clear()

    return RedirectResponse(
        "/"
    )

# ============================================================
# STATUS
# ============================================================

@app.get(
    "/api/status"
)
async def status():

    return {

        "application":
            "BenPopup Server",

        "status":
            "online",

        "clients":
            len(clients),

        "utilisateurs":
            len(utilisateurs)
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

    try:

        # ----------------------------------------------------
        # PREMIER MESSAGE
        # ----------------------------------------------------

        premier_message = (
            await websocket.receive_text()
        )

        data = json.loads(
            premier_message
        )

        if data.get(
            "type"
        ) != "connexion":

            await websocket.close()

            return

        nom = data.get(
            "nom",
            ""
        ).strip()

        if not nom:

            nom = "Utilisateur"

        # ----------------------------------------------------
        # NOM DÉJÀ UTILISÉ
        # ----------------------------------------------------

        if nom in clients:

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

            await websocket.close()

            return

        # ----------------------------------------------------
        # AJOUT CLIENT
        # ----------------------------------------------------

        clients[nom] = websocket

        print(
            f"[+] {nom} connecté"
        )

        print(
            "    Utilisateurs :",
            list(clients.keys())
        )

        # ----------------------------------------------------
        # CONFIRMATION
        # ----------------------------------------------------

        await websocket.send_text(
            json.dumps(
                {
                    "type":
                        "connexion_ok",

                    "nom":
                        nom
                },
                ensure_ascii=False
            )
        )

        # ----------------------------------------------------
        # BOUCLE
        # ----------------------------------------------------

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

                expediteur = data.get(
                    "expediteur",
                    nom
                )

                if not destinataire:

                    continue

                if not message:

                    continue

                # ---------------------------------------------
                # DESTINATAIRE CONNECTÉ
                # ---------------------------------------------

                if destinataire in clients:

                    cible = clients[
                        destinataire
                    ]

                    await cible.send_text(
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

                del clients[
                    ancien_nom
                ]

                nom = nouveau_nom

                clients[
                    nom
                ] = websocket

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
    # DÉCONNEXION
    # ========================================================

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

            del clients[
                nom
            ]

            print(
                f"[-] {nom} supprimé"
            )

        print(
            "    Utilisateurs :",
            list(clients.keys())
        )
