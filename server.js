const express = require("express");
const http = require("http");
const fs = require("fs");
const { Server } = require("socket.io");

const app = express();
const server = http.createServer(app);
const io = new Server(server);

app.use(express.static("public"));

let users = {};
const MESSAGES_FILE = "messages.json";
let messagesDB = {};

if (fs.existsSync(MESSAGES_FILE)) {
    messagesDB = JSON.parse(fs.readFileSync(MESSAGES_FILE));
}

function saveMessages() {
    fs.writeFileSync(MESSAGES_FILE, JSON.stringify(messagesDB, null, 2));
}

io.on("connection", (socket) => {

    socket.on("login", (username) => {
        socket.username = username;
        users[username] = socket.id;
        io.emit("updateUsers", Object.keys(users));
    });

    socket.on("joinRoom", (target) => {
        if (!socket.username || !target) return;
        const room = [socket.username, target].sort().join("_");
        socket.join(room);
        socket.room = room;
        socket.target = target;

        if (messagesDB[room]) {
            socket.emit("loadMessages", messagesDB[room]);
        } else {
            messagesDB[room] = [];
        }
    });

    socket.on("privateMessage", (msg) => {
        if (!socket.room) return;
        const now = new Date();
        const hours = now.getHours().toString().padStart(2,"0");
        const minutes = now.getMinutes().toString().padStart(2,"0");
        const time = `${hours}:${minutes}`;

        const messageObj = { user: socket.username, message: msg, time };
        messagesDB[socket.room].push(messageObj);
        saveMessages();
        io.to(socket.room).emit("privateMessage", messageObj);
    });

    socket.on("disconnect", () => {
        if (socket.username) delete users[socket.username];
        io.emit("updateUsers", Object.keys(users));
    });
});

server.listen(3000, () => console.log("Serveur Hermès Messenger sur http://localhost:3000"));
