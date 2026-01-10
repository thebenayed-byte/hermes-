const express = require('express');
const http = require('http');
const { Server } = require('socket.io');

const app = express();
const server = http.createServer(app);
const io = new Server(server);

app.use(express.static(__dirname));

let users = []; // { id, pseudo, unread: 0 }

io.on('connection', socket => {
  console.log('Un utilisateur connecté');

  socket.on('login', pseudo => {
    socket.pseudo = pseudo;
    users.push({ id: socket.id, pseudo, unread: 0 });
    io.emit('users', users);
  });

  socket.on('message', msg => {
    msg.time = Date.now();
    if(msg.type === 'private') {
      const user = users.find(u => u.pseudo === msg.to);
      if(user) {
        io.to(user.id).emit('message', msg);
        user.unread = (user.unread || 0) + 1;
      }
      socket.emit('message', msg); // aussi pour l'envoyeur
    } else {
      io.emit('message', msg);
    }
    io.emit('users', users);
  });

  socket.on('disconnect', () => {
    users = users.filter(u => u.id !== socket.id);
    io.emit('users', users);
  });
});

server.listen(3000, () => console.log('Serveur sur http://localhost:3000'));
