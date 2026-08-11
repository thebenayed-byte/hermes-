from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import json

app = FastAPI()

# ============================================================
# CLIENTS CONNECTÉS
# ============================================================

clients = {}


# ============================================================
# PAGE PRINCIPALE
# ============================================================

@app.get("/")
async def accueil():

    return {
        "application": "BenPopup Server",
        "status": "online",
        "clients": len(clients)
    }


# ============================================================
# WEBSOCKET
# ============================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):

    await websocket.accept()

    nom = None

    try:

        # ----------------------------------------------------
        # PREMIER MESSAGE = CONNEXION
        # ----------------------------------------------------

        premier_message = await websocket.receive_text()

        data = json.loads(premier_message)

        if data.get("type") != "connexion":

            await websocket.close()

            return

        nom = data.get("nom", "").strip()

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
                        "message": "Ce nom est déjà utilisé."
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
            f"    Utilisateurs : {list(clients.keys())}"
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

            data = json.loads(texte)

            type_message = data.get("type")

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
                                "expediteur": expediteur,
                                "message": message
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
                            "utilisateurs": liste
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

                # ---------------------------------------------
                # NOM DEJA PRIS
                # ---------------------------------------------

                if (
                    nouveau_nom in clients
                    and nouveau_nom != nom
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

                # ---------------------------------------------
                # CHANGEMENT
                # ---------------------------------------------

                ancien_nom = nom

                del clients[ancien_nom]

                nom = nouveau_nom

                clients[nom] = websocket

                print(
                    f"[NOM] "
                    f"{ancien_nom} -> "
                    f"{nom}"
                )

                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "nom_modifie",
                            "nom": nom
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

            del clients[nom]

            print(
                f"[-] {nom} supprimé"
            )

        print(
            f"    Utilisateurs : {list(clients.keys())}"
        )