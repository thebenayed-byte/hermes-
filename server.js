const express = require('express');
const http = require('http');
const socketIo = require('socket.io');

const app = express();
const server = http.createServer(app);
const io = socketIo(server);

app.use(express.static(__dirname + '/public'));

let users = {};

io.on('connection', (socket) => {
  let currentPseudo = null;

  socket.on('join', (pseudo) => {
    currentPseudo = pseudo;
    users[socket.id] = pseudo;
    updateUsers();
  });

  socket.on('chat message', (msg) => {
    if (currentPseudo) {
      io.emit('chat message', { pseudo: currentPseudo, message: msg });
    }
  });

  socket.on('disconnect', () => {
    delete users[socket.id];
    updateUsers();
  });

  function updateUsers() {
    io.emit('update users', {
      count: Object.keys(users).length,
      users: Object.values(users)
    });
  }
});

server.listen(3000, () => {
  console.log('Serveur démarré sur http://localhost:3000');
});