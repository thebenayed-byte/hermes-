const socket = io();
let username = "";
let target = "";

// Son notification
const notifSound = new Audio('ding.mp3');

function login() {
    username = document.getElementById("username").value.trim();
    if (!username) return alert("Écris ton nom !");
    socket.emit("login", username);
    document.getElementById("login").classList.add("hidden");
    document.getElementById("chat").classList.remove("hidden");
}

// Liste utilisateurs
socket.on("updateUsers", (list) => {
    const ul = document.getElementById("userList");
    ul.innerHTML = "";
    list.forEach(u => {
        if (u !== username) {
            const div = document.createElement("div");
            div.innerText = u;
            div.onclick = () => selectUser(u);
            ul.appendChild(div);
        }
    });
});

// Sélection utilisateur
function selectUser(u) {
    target = u;
    document.getElementById("chatTitle").innerText = "Discussion avec " + u;
    socket.emit("joinRoom", target);
    document.getElementById("messages").innerHTML = "";
}

// Envoyer message
function sendMessage() {
    const input = document.getElementById("messageInput");
    if (input.value.trim() !== "" && target) {
        socket.emit("privateMessage", input.value);
        input.value = "";
    }
}

// Afficher un message
function displayMessage(data) {
    const div = document.createElement("div");
    div.classList.add("bubble");
    div.classList.add(data.user === username ? "me" : "other");
    div.innerHTML = `<span>${data.message}</span><small>${data.time}</small>`;

    const messagesContainer = document.getElementById("messages");
    messagesContainer.appendChild(div);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    if (data.user !== username) showNotification(data.user, data.message);
}

// Charger messages existants
socket.on("loadMessages", (messages) => { messages.forEach(displayMessage); });
socket.on("privateMessage", displayMessage);

// Notifications flottantes style WhatsApp
function showNotification(user, message) {
    const notif = document.getElementById("notif");
    notif.innerText = `${user}: ${message}`;
    notifSound.play();
    notif.classList.add("show");
    notif.classList.remove("hidden");
    setTimeout(() => { notif.classList.remove("show"); notif.classList.add("hidden"); }, 3000);
}

// ENTRÉE pour login ou envoyer message
document.getElementById("username").addEventListener("keypress", (e) => { if(e.key==="Enter") login(); });
document.getElementById("messageInput").addEventListener("keypress", (e) => { if(e.key==="Enter") sendMessage(); });
