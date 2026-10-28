/**
 * Pulse AI - Voice App Controller
 * Manages WebSocket connection, real-time telemetry ingestion,
 * auto-fading controls, pause toggle, and window operations.
 */

(function () {
    const canvas = document.getElementById("orb-canvas");
    const closeBtn = document.getElementById("close-btn");
    const controlsContainer = document.getElementById("controls-container");
    const pauseBtn = document.getElementById("pause-btn");
    const pauseIcon = document.getElementById("pause-icon");
    const pauseLabel = document.getElementById("pause-label");

    if (!canvas) return;

    // Instantiate 3D Spherical Nano-Particle Orb
    const orb = new window.OrbRenderer(canvas);

    let isPaused = false;
    let ws = null;
    let reconnectTimeout = null;
    let reconnectInterval = 1000;
    const maxReconnectInterval = 5000;

    // Auto-Fade Controls Logic (2.5 seconds of mouse idle)
    let idleTimer = null;
    const IDLE_DELAY_MS = 2500;

    function resetIdleTimer() {
        if (controlsContainer) {
            controlsContainer.classList.remove("controls-idle");
        }
        if (idleTimer) {
            clearTimeout(idleTimer);
        }
        idleTimer = setTimeout(() => {
            if (controlsContainer) {
                controlsContainer.classList.add("controls-idle");
            }
        }, IDLE_DELAY_MS);
    }

    window.addEventListener("mousemove", resetIdleTimer);
    window.addEventListener("mousedown", resetIdleTimer);
    resetIdleTimer();

    // Update UI pause pill styling
    function updatePauseUI(paused) {
        isPaused = paused;
        orb.setPaused(isPaused);

        if (pauseBtn && pauseIcon && pauseLabel) {
            if (isPaused) {
                pauseBtn.classList.add("is-paused");
                pauseIcon.innerHTML = "&#9658;"; // Play icon
                pauseLabel.textContent = "RESUME";
            } else {
                pauseBtn.classList.remove("is-paused");
                pauseIcon.innerHTML = "&#9646;&#9646;"; // Pause bars
                pauseLabel.textContent = "PAUSE";
            }
        }
    }

    // Toggle Pause Function
    function togglePause() {
        resetIdleTimer();
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ action: "toggle_pause" }));
        } else {
            updatePauseUI(!isPaused);
        }
    }

    if (pauseBtn) {
        pauseBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            togglePause();
        });
    }

    // Spacebar toggles pause/resume
    window.addEventListener("keydown", (e) => {
        if (e.code === "Space" || e.key === " ") {
            e.preventDefault();
            togglePause();
        } else if (e.key === "Escape") {
            closeWindow();
        }
    });

    // WebSocket Telemetry Management
    function connectWebSocket() {
        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const wsUrl = `${protocol}//${window.location.host}/ws/voice`;

        try {
            ws = new WebSocket(wsUrl);

            ws.onopen = () => {
                reconnectInterval = 1000;
                if (reconnectTimeout) {
                    clearTimeout(reconnectTimeout);
                    reconnectTimeout = null;
                }
            };

            ws.onmessage = (event) => {
                try {
                    const msg = JSON.parse(event.data);
                    if (msg.type === "amplitude") {
                        orb.setAmplitude(msg.value, msg.state);
                    } else if (msg.type === "state") {
                        orb.setState(msg.state);
                        if (msg.state === "paused") {
                            updatePauseUI(true);
                        } else if (isPaused && msg.state === "listening") {
                            updatePauseUI(false);
                        }
                    } else if (msg.type === "pause_state") {
                        updatePauseUI(Boolean(msg.paused));
                    }
                } catch (e) {
                    // Ignore malformed messages
                }
            };

            ws.onclose = () => {
                scheduleReconnect();
            };

            ws.onerror = () => {
                try {
                    ws.close();
                } catch (e) {}
            };
        } catch (e) {
            scheduleReconnect();
        }
    }

    function scheduleReconnect() {
        if (!reconnectTimeout) {
            reconnectTimeout = setTimeout(() => {
                reconnectTimeout = null;
                reconnectInterval = Math.min(reconnectInterval * 1.5, maxReconnectInterval);
                connectWebSocket();
            }, reconnectInterval);
        }
    }

    // Heartbeat Keepalive Ping
    setInterval(() => {
        if (ws && ws.readyState === WebSocket.OPEN) {
            try {
                ws.send(JSON.stringify({ action: "ping" }));
            } catch (e) {}
        }
    }, 15000);

    // Initial connection
    connectWebSocket();

    // Close window handler (pywebview API or window.close)
    function closeWindow() {
        if (window.pywebview && window.pywebview.api && typeof window.pywebview.api.close === "function") {
            window.pywebview.api.close();
        } else {
            window.close();
        }
    }

    if (closeBtn) {
        closeBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            closeWindow();
        });
    }
})();
