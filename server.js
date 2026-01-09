const express = require("express");
const app = express();
const http = require("http").createServer(app);
const io = require("socket.io")(http);

app.use(express.static("public"));

let users = [];
let bannedNumbers = [];

// ---------- SOCKET.IO ----------
io.on("connection", socket => {
    console.log("Nouvelle connexion");

    // Demande d'accès — connexion directe
    socket.on("requestAccess", data => {
        if (bannedNumbers.includes(data.number)) {
            socket.emit("accessDenied", "Numéro banni");
            return;
        }
        users.push({ socketId: socket.id, pseudo: data.pseudo, number: data.number });
        socket.emit("userAccepted", data); // accès immédiat
        io.emit("users", users.map(u => u.pseudo));
    });

    // Login utilisateur
    socket.on("login", pseudo => {
        socket.pseudo = pseudo;
        io.emit("users", users.map(u => u.pseudo));
    });

    // Messages
    socket.on("message", data => {
        if (data.to) { // message privé
            const recipient = users.find(u => u.pseudo === data.to);
            if (recipient) io.to(recipient.socketId).emit("message", data);
        } else { // message groupe
            socket.broadcast.emit("message", data);
        }
        socket.emit("message", data); // envoyer à soi-même
    });

    // Déconnexion
    socket.on("disconnect", () => {
        users = users.filter(u => u.socketId !== socket.id);
        io.emit("users", users.map(u => u.pseudo));
    });
});

// ---------- PORT Render ----------
const PORT = process.env.PORT || 3000;
http.listen(PORT, () => console.log(`Serveur lancé sur le port ${PORT}`));
