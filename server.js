const express = require('express');
const bodyParser = require('body-parser');
const app = express();
const http = require('http').createServer(app);
const io = require('socket.io')(http);
const fs = require('fs');

const PORT = 3000;
const ADMIN_PASSWORD = "Hermes123"; // mot de passe admin

app.use(bodyParser.urlencoded({ extended: true }));
app.use(express.static('public'));

// Admin login sécurisé
app.post('/admin-login', (req, res) => {
    const password = req.body.password;
    if(password === ADMIN_PASSWORD){
        res.redirect('/admin.html'); // accès à l'interface admin
    } else {
        res.send("<h2>Mot de passe incorrect pour accéder à l'admin</h2>");
    }
});

// Stockage utilisateurs
let users = {};
let bannedUsers = [];

// Stats
let stats = { day: 0, month: 0 };

// Messages persistants
let messages = { public: [], private: {} };

// Charger messages depuis fichier
function loadMessages() {
    if (fs.existsSync('messages.json')) {
        messages = JSON.parse(fs.readFileSync('messages.json'));
    }
}

// Sauvegarder messages
function saveMessages() {
    fs.writeFileSync('messages.json', JSON.stringify(messages, null, 2));
}

loadMessages();

// Socket.io
io.on('connection', (socket) => {
    console.log('Utilisateur connecté:', socket.id);

    socket.on('login', (pseudo, callback) => {
        if (bannedUsers.includes(pseudo)) {
            callback({ success: false, message: "Vous êtes banni" });
            return;
        }

        users[socket.id] = { pseudo, unread: {} };
        callback({ success: true });

        stats.day++;
        stats.month++;

        // Envoyer historique
        socket.emit('loadPublicMessages', messages.public);
        socket.emit('loadPrivateMessages', messages.private[pseudo] || []);

        io.emit('updateUsers', getUserList());
        io.emit('stats', stats);
        io.emit('userConnected', pseudo);
    });

    socket.on('publicMessage', (msg) => {
        if(!users[socket.id]) return;
        const pseudo = users[socket.id].pseudo;
        const time = getTime();
        const m = { pseudo, msg, time };
        messages.public.push(m);
        saveMessages();
        io.emit('publicMessage', m);
    });

    socket.on('privateMessage', ({ to, msg }) => {
        if(!users[socket.id]) return;
        const from = users[socket.id].pseudo;
        const time = getTime();
        if(!messages.private[to]) messages.private[to] = [];
        messages.private[to].push({ from, msg, time });
        saveMessages();

        const toSocketId = Object.keys(users).find(id => users[id].pseudo === to);
        if(toSocketId){
            io.to(toSocketId).emit('privateMessage', { from, msg, time });
            users[toSocketId].unread[from] = (users[toSocketId].unread[from] || 0) + 1;
            io.emit('updateUsers', getUserList());
        }
    });

    socket.on('banUser', (pseudo) => {
        bannedUsers.push(pseudo);
        const banSocketId = Object.keys(users).find(id => users[id].pseudo === pseudo);
        if(banSocketId){
            io.to(banSocketId).emit('banned');
            delete users[banSocketId];
        }
        io.emit('updateUsers', getUserList());
        io.emit('userBanned', pseudo);
    });

    socket.on('getStats', () => {
        socket.emit('stats', stats);
    });

    socket.on('disconnect', () => {
        if(users[socket.id]){
            const pseudo = users[socket.id].pseudo;
            delete users[socket.id];
            io.emit('updateUsers', getUserList());
            io.emit('userDisconnected', pseudo);
        }
    });
});

// Helper
function getUserList() {
    return Object.values(users).map(u => {
        const totalUnread = Object.values(u.unread).reduce((a,b)=>a+b,0);
        return { pseudo: u.pseudo, unread: totalUnread };
    });
}

function getTime(){
    const now = new Date();
    const h = now.getHours().toString().padStart(2,'0');
    const m = now.getMinutes().toString().padStart(2,'0');
    return `${h}:${m}`;
}

http.listen(PORT, () => console.log(`Serveur lancé sur http://localhost:${PORT}`));
