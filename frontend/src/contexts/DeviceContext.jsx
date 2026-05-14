import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { createDeviceWebSocket, api } from '../api/client';

const DeviceContext = createContext(null);

export function DeviceProvider({ children }) {
  const [deviceState, setDeviceState] = useState({
    state: 'idle',
    connected: false,
    volume: 50,
    current_track: null,
    nfc_tag: null,
    profile_id: 'default',
    usage_today_minutes: 0,
    remaining_minutes: 120,
  });

  const [devices, setDevices] = useState([]);
  const [ws, setWs] = useState(null);

  // Fetch devices on mount
  useEffect(() => {
    api.getDevices()
      .then(setDevices)
      .catch(() => {});
  }, []);

  // Connect WebSocket when a device is available
  useEffect(() => {
    if (devices.length === 0) return;

    const deviceId = devices[0].device_id;
    const socket = createDeviceWebSocket(deviceId, (msg) => {
      if (msg.type === 'device_state') {
        setDeviceState(prev => ({ ...prev, ...msg.data }));
      } else if (msg.type === 'connection') {
        setDeviceState(prev => ({ ...prev, connected: msg.data.connected }));
      }
    });

    setWs(socket);
    return () => socket.disconnect();
  }, [devices]);

  const sendCommand = useCallback(async (command, payload = {}) => {
    // Send via WebSocket for real-time
    if (ws) ws.send(command, payload);
    // Also send via HTTP for reliability
    await api.sendCommand(command, payload);
  }, [ws]);

  const dismissSafetyAlert = useCallback(() => {
    setDeviceState(prev => ({ ...prev, safety_alert: null }));
  }, []);

  return (
    <DeviceContext.Provider value={{ deviceState, devices, sendCommand, dismissSafetyAlert }}>
      {children}
    </DeviceContext.Provider>
  );
}

export function useDevice() {
  const ctx = useContext(DeviceContext);
  if (!ctx) throw new Error('useDevice must be used within DeviceProvider');
  return ctx;
}
