
const WebSocket = require('ws');

const wss = new WebSocket.Server({ port: 8080 });

let connections = {
    autowarePc: null,
    clients: new Set()
};

wss.on('connection', ws => {
    console.log('A new client connected.');

    ws.on('message', message => {
        try {
            const data = JSON.parse(message);

            if (data.type === 'register') {
                if (data.clientType === 'autoware-pc') {
                    connections.autowarePc = ws;
                    console.log('Autoware PC registered.');
                    broadcastToClients({ type: 'status', message: 'Autoware PC connected' });
                } else if (data.clientType === 'client') {
                    connections.clients.add(ws);
                    console.log('A new web client registered.');
                    if (connections.autowarePc) {
                        ws.send(JSON.stringify({ type: 'status', message: 'Autoware PC connected' }));
                    }
                }
            }
            else if (data.type === 'command' && ws !== connections.autowarePc) {
                if (connections.autowarePc && connections.autowarePc.readyState === WebSocket.OPEN) {
                    console.log('Forwarding command to Autoware PC:', data);
                    connections.autowarePc.send(JSON.stringify(data));
                } else {
                    console.log('Autoware PC is not connected. Command dropped.');
                    ws.send(JSON.stringify({ type: 'error', message: 'Autoware PC is not connected.' }));
                }
            }
        } catch (error) {
            console.error('Failed to process message:', message, error);
        }
    });

    ws.on('close', () => {
        console.log('Client disconnected.');
        if (ws === connections.autowarePc) {
            connections.autowarePc = null;
            console.log('Autoware PC disconnected.');
            broadcastToClients({ type: 'status', message: 'Autoware PC disconnected' });
        } 
        else if (connections.clients.has(ws)) {
            connections.clients.delete(ws);
            console.log('A web client disconnected.');
        }
    });

    ws.on('error', (error) => {
        console.error('A websocket error occurred:', error);
    });
});

function broadcastToClients(message) {
    connections.clients.forEach(client => {
        if (client.readyState === WebSocket.OPEN) {
            client.send(JSON.stringify(message));
        }
    });
}

console.log('🚀 Relay server started on port 8080. Waiting for connections...');

