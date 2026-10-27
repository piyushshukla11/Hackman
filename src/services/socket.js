import { io } from 'socket.io-client';

// Connect to the backend through the Vite proxy or direct port 5000
const SOCKET_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:5000';

export const socket = io(SOCKET_URL, {
  withCredentials: true,
  transports: ['websocket', 'polling'],
  reconnectionAttempts: 10,
  reconnectionDelay: 1000,
});

socket.on('connect', () => {
  console.log('[PRISM Socket] Connected to backend on:', SOCKET_URL, 'Socket ID:', socket.id);
});

socket.on('connect_error', (err) => {
  console.warn('[PRISM Socket] Connection error:', err.message);
});

socket.on('disconnect', (reason) => {
  console.log('[PRISM Socket] Disconnected:', reason);
});

export default socket;
