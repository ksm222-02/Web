

const ROSLIB = require('roslib');
const WebSocket = require('ws');

const RELAY_SERVER_IP = 'YOUR_PUBLIC_SERVER_IP';
const RELAY_SERVER_URL = `ws://${RELAY_SERVER_IP}:8080`;

const ROSBRIDGE_URL = 'ws://localhost:9090';

const ros = new ROSLIB.Ros({
    url: ROSBRIDGE_URL
});

ros.on('connection', () => {
    console.log(`✅ Connected to ROSbridge server at ${ROSBRIDGE_URL}`);
});

ros.on('error', (error) => {
    console.error(`❌ Error connecting to ROSbridge server: ${JSON.stringify(error)}`);
});

ros.on('close', () => {
    console.log(`🔌 Connection to ROSbridge server closed.`);
});

const engageTopic = new ROSLIB.Topic({
    ros: ros,
    name: '/autoware/engage',
    messageType: 'autoware_auto_vehicle_msgs/msg/Engage'
});

function connectToRelayServer() {
    const ws = new WebSocket(RELAY_SERVER_URL);

    ws.on('open', () => {
        console.log(`✅ Connected to Relay Server at ${RELAY_SERVER_URL}`);
        ws.send(JSON.stringify({ type: 'register', clientType: 'autoware-pc' }));
    });

    ws.on('message', (message) => {
        try {
            const data = JSON.parse(message);
            console.log('Received command from relay server:', data);

            if (data.type === 'command' && data.topic === '/autoware/engage') {
                const engageMsg = new ROSLIB.Message(data.msg);
                engageTopic.publish(engageMsg);
                console.log(`Published to ${engageTopic.name}:`, engageMsg);
            }
        } catch (error) {
            console.error('Failed to process message from relay server:', message, error);
        }
    });

    ws.on('close', () => {
        console.log('🔌 Disconnected from Relay Server. Retrying in 5 seconds...');
        setTimeout(connectToRelayServer, 5000);
    });

    ws.on('error', (error) => {
        console.error('❌ Error with Relay Server connection:', error.message);
    });
}

// 스크립트 시작 시 중계 서버 연결 시작
connectToRelayServer();

