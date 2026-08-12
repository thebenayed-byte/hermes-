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
# SESSIONS
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
# GOOGLE OAUTH
# ============================================================

oauth = OAuth()


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
# CLIENTS CONNECTÉS
# ============================================================

clients = {}


# ============================================================
# UTILISATEURS CONNECTÉS AU SITE
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
        "index.html",
        {
            "request": request,
            "utilisateur": utilisateur,
            "clients": len(clients)
        }
    )


# ============================================================
# PAGE CONNEXION
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
        "login.html",
        {
            "request": request,
            "google_active":
                bool(
                    GOOGLE_CLIENT_ID
                    and
                    GOOGLE_CLIENT_SECRET
                )
        }
    )


# ============================================================
# CONNEXION GOOGLE
# ============================================================

@app.get(
    "/auth/google"
)
async def auth_google(request: Request):

    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:

        return HTMLResponse(
            """
            <h1>Google OAuth n'est pas configuré.</h1>
            <p>Ajoute GOOGLE_CLIENT_ID et GOOGLE_CLIENT_SECRET dans Render.</p>
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
# CALLBACK GOOGLE
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
            "id": user_info.get("sub"),
            "nom": nom,
            "email": email,
            "photo": photo
        }

        request.session["utilisateur"] = utilisateur

        utilisateurs[email] = utilisateur

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
            <h1>Erreur de connexion Google</h1>
            <p>{e}</p>
            <a href="/login">Retour</a>
            """,
            status_code=500
        )


# ============================================================
# TABLEAU DE BORD
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
        "dashboard.html",
        {
            "request": request,
            "utilisateur": utilisateur,
            "clients": len(clients)
        }
    )


# ============================================================
# DECONNEXION
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
# API INFORMATIONS SERVEUR
# ============================================================

@app.get(
    "/api/status"
)
async def status():

    return {
        "application": "BenPopup Server",
        "status": "online",
        "clients": len(clients),
        "utilisateurs": len(utilisateurs)
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
        # PREMIER MESSAGE = CONNEXION
        # ----------------------------------------------------

        premier_message = await websocket.receive_text()

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
        # NOM DEJA UTILISE
        # ----------------------------------------------------

        if nom in clients:

            await websocket.send_text(
                json.dumps(
                    {
                        "type": "erreur",
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
            f"    Utilisateurs : "
            f"{list(clients.keys())}"
        )

        # ----------------------------------------------------
        # CONFIRMATION
        # ----------------------------------------------------

        await websocket.send_text(
            json.dumps(
                {
                    "type": "connexion_ok",
                    "nom": nom
                },
                ensure_ascii=False
            )
        )

        # ----------------------------------------------------
        # BOUCLE
        # ----------------------------------------------------

        while True:

            texte = await websocket.receive_text()

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
                # DESTINATAIRE CONNECTÉ ?
                # ---------------------------------------------

                if destinataire in clients:

                    cible = clients[
                        destinataire
                    ]

                    await cible.send_text(
                        json.dumps(
                            {
                                "type": "message",
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
                                "type": "erreur",
                                "message":
                                    f"{destinataire} "
                                    f"n'est pas connecté."
                            },
                            ensure_ascii=False
                        )
                    )

            # =================================================
            # LISTE UTILISATEURS
            # =================================================

            elif type_message == "liste":

                liste = list(
                    clients.keys()
                )

                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "liste",
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
                                "type": "erreur",
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
                                "type": "erreur",
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
    # DECONNEXION
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
            f"    Utilisateurs : "
            f"{list(clients.keys())}"
        )
