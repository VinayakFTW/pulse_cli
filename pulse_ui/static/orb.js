/**
 * Pulse AI - Futuristic 3D Spherical Nano-Particle Orb Engine
 * Simulates a defined 3D spherical orb filled with 5,000 nano-sized particles
 * circulating in 3D elliptical orbits with blue-grey gradients and real-time audio reactivity.
 */

class NanoParticle {
    constructor(baseRadius, isShell = false) {
        this.baseSize = 0.65 + Math.random() * 0.55; // 0.65px - 1.2px nano scale
        this.reset(baseRadius, isShell, true);
    }

    reset(baseRadius, isShell, randomizePhase = false) {
        this.isShell = isShell;

        if (isShell) {
            // Shell particles define the crisp outer boundary of the 3D spherical orb
            this.orbitRadius = baseRadius * (0.91 + Math.random() * 0.10);
            this.eccentricity = 0.88 + Math.random() * 0.11; // 0.88 - 0.99 (spherical surface contour)
        } else {
            // Interior volume particles fill the sphere core and mantle
            const volT = Math.pow(Math.random(), 0.65);
            this.orbitRadius = baseRadius * (0.16 + volT * 0.74);
            this.eccentricity = 0.74 + Math.random() * 0.22; // 0.74 - 0.96
        }

        this.a = this.orbitRadius;
        this.b = this.a * this.eccentricity;

        // 3D Orbital plane random normal orientation
        const theta = Math.random() * Math.PI * 2;
        const phi = Math.acos(2 * Math.random() - 1); // Uniform spherical distribution

        // Normal vector of the orbital plane
        const nx = Math.sin(phi) * Math.cos(theta);
        const ny = Math.sin(phi) * Math.sin(theta);
        const nz = Math.cos(phi);

        // Find two orthonormal basis vectors u and v perpendicular to n
        let refX = 0, refY = 1, refZ = 0;
        if (Math.abs(ny) > 0.9) {
            refX = 1; refY = 0; refZ = 0;
        }

        // Cross product ref x n -> u
        let ux = refY * nz - refZ * ny;
        let uy = refZ * nx - refX * nz;
        let uz = refX * ny - refY * nx;
        const uLen = Math.hypot(ux, uy, uz) || 1;
        this.ux = ux / uLen;
        this.uy = uy / uLen;
        this.uz = uz / uLen;

        // Cross product n x u -> v
        this.vx = ny * this.uz - nz * this.uy;
        this.vy = nz * this.ux - nx * this.uz;
        this.vz = nx * this.uy - ny * this.ux;

        // Orbital angular speed (nano-particles swirl in both directions)
        const dir = Math.random() < 0.5 ? 1 : -1;
        const baseSpeed = (0.45 + Math.random() * 0.65) / 2.5;
        this.angularSpeed = dir * (baseSpeed / Math.sqrt(this.a / 60));

        this.currentTheta = randomizePhase ? Math.random() * Math.PI * 2 : 0;
        this.phase = this.currentTheta;
        this.harmonicFreq = 3.0 + Math.random() * 4.0;

        // 3D and projected coords
        this.x = 0;
        this.y = 0;
        this.z = 0;
        this.screenX = 0;
        this.screenY = 0;
        this.screenScale = 1;
        this.screenAlpha = 1;
        this.colorBucket = 0;
    }

    update(time, amplitude, growth, speedMult, gyroMatrix, baseRadius, isPaused) {
        // Update orbital angle
        const activeSpeed = isPaused ? this.angularSpeed * 0.25 : this.angularSpeed * speedMult;
        this.currentTheta += activeSpeed * 0.016;

        // Elliptical position in 3D orbit plane
        const cosT = Math.cos(this.currentTheta);
        const sinT = Math.sin(this.currentTheta);

        let localA = this.a * growth;
        let localB = this.b * growth;

        // Acoustic harmonic radial ripples during speech
        if (amplitude > 0.01) {
            const ripple = Math.sin(time * 9.0 + this.phase * this.harmonicFreq) * (amplitude * 22.0);
            localA += ripple;
            localB += ripple * this.eccentricity;
        }

        // Calculate 3D position
        const px = localA * cosT * this.ux + localB * sinT * this.vx;
        const py = localA * cosT * this.uy + localB * sinT * this.vy;
        const pz = localA * cosT * this.uz + localB * sinT * this.vz;

        // Apply slow 3D gyroscopic drift
        const gx = px * gyroMatrix.xx + py * gyroMatrix.yx + pz * gyroMatrix.zx;
        const gy = px * gyroMatrix.xy + py * gyroMatrix.yy + pz * gyroMatrix.zy;
        const gz = px * gyroMatrix.xz + py * gyroMatrix.yz + pz * gyroMatrix.zz;

        this.x = gx;
        this.y = gy;
        this.z = gz;

        // 3D perspective projection
        const fov = 500;
        const depth = fov / (fov + this.z);
        this.screenScale = depth;

        // Depth attenuation: foreground particles are crisper, background particles softer
        const normZ = this.z / (baseRadius * 1.4);
        const depthAlpha = Math.max(0.18, Math.min(1.0, 0.62 - normZ * 0.45));
        const ampBrightness = 1.0 + amplitude * 0.7;
        this.screenAlpha = Math.min(1.0, depthAlpha * ampBrightness);

        // Determine blue-grey gradient bucket (0 = deep slate, 6 = starlight ice core)
        const radiusRatio = Math.min(1.0, Math.hypot(this.x, this.y, this.z) / (baseRadius * growth));
        let energyLevel = (1.0 - radiusRatio * 0.7) + amplitude * 0.45;
        if (this.isShell) {
            // Shell nano-particles shimmer with cool electric blue-grey
            energyLevel = 0.4 + (1.0 - normZ) * 0.35 + amplitude * 0.4;
        }

        if (isPaused) {
            energyLevel *= 0.55;
        }

        if (energyLevel < 0.28) {
            this.colorBucket = 0; // Deep Slate
        } else if (energyLevel < 0.45) {
            this.colorBucket = 1; // Steel Slate
        } else if (energyLevel < 0.62) {
            this.colorBucket = 2; // Cool Slate-Cyan
        } else if (energyLevel < 0.78) {
            this.colorBucket = 3; // Electric Slate-Blue
        } else if (energyLevel < 0.92) {
            this.colorBucket = 4; // Ice Blue
        } else {
            this.colorBucket = 5; // Starlight Spark
        }
    }
}

class OrbRenderer {
    constructor(canvas) {
        this.canvas = canvas;
        this.ctx = canvas.getContext("2d");


        // 50,000 nano particles baseline as specified by user
        this.particleCount = 50000;
        this.particles = [];

        this.baseRadius = 155;
        this.currentAmplitude = 0.0;
        this.targetAmplitude = 0.0;
        this.state = "idle"; // "idle", "listening", "thinking", "speaking", "paused"
        this.isPaused = false;

        this.time = 0;
        this.lastFrameTime = performance.now();

        // 6-Stop Blue-Grey Futuristic Gradient Palette
        this.colorPalette = [
            "rgba(47, 63, 86, 0.45)",   // 0: Deep Slate
            "rgba(71, 85, 105, 0.65)",  // 1: Steel Slate
            "rgba(100, 116, 139, 0.8)", // 2: Cool Slate-Cyan
            "rgba(96, 165, 250, 0.85)", // 3: Electric Slate-Blue
            "rgba(147, 197, 253, 0.92)",// 4: Ice Blue
            "rgba(241, 245, 249, 1.0)", // 5: Starlight Spark
        ];

        this.resize();
        this.initParticles();
        window.addEventListener("resize", () => this.resize());

        this.animate = this.animate.bind(this);
        requestAnimationFrame(this.animate);
    }

    resize() {
        const dpr = window.devicePixelRatio || 1;
        const rect = this.canvas.getBoundingClientRect();
        this.width = rect.width || window.innerWidth || 650;
        this.height = rect.height || window.innerHeight || 650;

        this.canvas.width = this.width * dpr;
        this.canvas.height = this.height * dpr;
        this.ctx.scale(dpr, dpr);

        this.centerX = this.width / 2;
        this.centerY = this.height / 2;

        const minDim = Math.min(this.width, this.height);
        this.baseRadius = minDim * 0.26;
    }

    initParticles() {
        this.particles = [];
        // 60% interior volumetric stardust, 40% outer spherical shell boundary
        const shellCount = Math.round(this.particleCount * 0.40);
        const volumeCount = this.particleCount - shellCount;

        for (let i = 0; i < volumeCount; i++) {
            this.particles.push(new NanoParticle(this.baseRadius, false));
        }
        for (let i = 0; i < shellCount; i++) {
            this.particles.push(new NanoParticle(this.baseRadius, true));
        }
    }

    setAmplitude(amp, state = "speaking") {
        if (this.isPaused) return;
        this.targetAmplitude = Math.max(0.0, Math.min(1.0, amp));
        if (state) {
            this.state = state;
        }
    }

    setState(state) {
        this.state = state;
        this.isPaused = (state === "paused");
        if (this.isPaused) {
            this.targetAmplitude = 0.0;
        } else if (state === "listening") {
            this.targetAmplitude = Math.max(this.targetAmplitude, 0.05);
        } else if (state === "thinking") {
            this.targetAmplitude = 0.16;
        } else if (state === "idle") {
            this.targetAmplitude = 0.0;
        }
    }

    setPaused(paused) {
        this.isPaused = Boolean(paused);
        this.state = this.isPaused ? "paused" : "listening";
        if (this.isPaused) {
            this.targetAmplitude = 0.0;
        }
    }

    animate(now) {
        const dt = Math.min((now - this.lastFrameTime) / 1000, 0.1);
        this.lastFrameTime = now;
        this.time += dt;

        // Envelope follower for audio responsiveness
        const lerpRate = this.targetAmplitude > this.currentAmplitude ? 0.36 : 0.08;
        this.currentAmplitude += (this.targetAmplitude - this.currentAmplitude) * lerpRate;

        let activeAmp = this.isPaused ? 0.0 : this.currentAmplitude;
        if (this.state === "thinking" && !this.isPaused) {
            activeAmp = 0.12 + Math.sin(this.time * 6.0) * 0.05;
        }

        // Orb Growth: Base sphere expands dynamically up to 1.8x with sound amplitude
        const baseExpansion = this.isPaused ? 0.94 : (1.0 + Math.sin(this.time * 1.6) * 0.025);
        const growth = baseExpansion + activeAmp * 0.78;

        // Nano-particle speed multiplier
        const speedMult = 1.0 + activeAmp * 2.8 + (this.state === "thinking" ? 1.4 : 0);

        // Gyroscopic 3D precession matrix
        const driftSpeed = (this.isPaused ? 0.08 : 0.26) / 2.5;
        const yaw = this.time * driftSpeed;
        const pitch = Math.sin(this.time * (driftSpeed * 0.65)) * 0.22;
        const roll = Math.cos(this.time * (driftSpeed * 0.5)) * 0.16;

        const cy = Math.cos(yaw), sy = Math.sin(yaw);
        const cp = Math.cos(pitch), sp = Math.sin(pitch);
        const cr = Math.cos(roll), sr = Math.sin(roll);

        const gyroMatrix = {
            xx: cy * cr + sy * sp * sr,
            xy: sr * cp,
            xz: -sy * cr + cy * sp * sr,
            yx: -cy * sr + sy * sp * cr,
            yy: cr * cp,
            yz: sy * sr + cy * sp * cr,
            zx: sy * cp,
            zy: -sp,
            zz: cy * cp
        };

        // Update all 5,000 nano particles
        const cx = this.centerX;
        const cyCenter = this.centerY;

        for (let i = 0; i < this.particles.length; i++) {
            const p = this.particles[i];
            p.update(this.time, activeAmp, growth, speedMult, gyroMatrix, this.baseRadius, this.isPaused);
            p.screenX = cx + p.x * p.screenScale;
            p.screenY = cyCenter + p.y * p.screenScale;
        }

        // Render frame
        this.render(activeAmp, growth);

        requestAnimationFrame(this.animate);
    }

    render(amplitude, growth) {
        const ctx = this.ctx;
        const cx = this.centerX;
        const cy = this.centerY;

        // Clear canvas with subtle trail fade for silky motion
        ctx.save();
        ctx.fillStyle = "rgba(5, 8, 14, 0.28)";
        ctx.fillRect(0, 0, this.width, this.height);

        // Volumetric blending
        ctx.globalCompositeOperation = "lighter";

        // Subtle, elegant internal volumetric haze (non-blob, bounded within sphere)
        const innerHazeR = Math.max(40, (this.baseRadius * 0.75) * growth);
        const hazeGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, innerHazeR);
        const hazeAlpha = this.isPaused ? 0.04 : (0.08 + amplitude * 0.18).toFixed(3);
        hazeGrad.addColorStop(0.0, `rgba(96, 165, 250, ${hazeAlpha})`);
        hazeGrad.addColorStop(0.5, `rgba(71, 85, 105, ${(hazeAlpha * 0.5).toFixed(3)})`);
        hazeGrad.addColorStop(1.0, "rgba(5, 8, 14, 0)");
        ctx.fillStyle = hazeGrad;
        ctx.beginPath();
        ctx.arc(cx, cy, innerHazeR, 0, Math.PI * 2);
        ctx.fill();

        // High-Performance Batched Nano-Particle Rendering:
        // Group particles by color bucket so all particles of the same shade are drawn in one draw call
        const buckets = [[], [], [], [], [], []];

        for (let i = 0; i < this.particles.length; i++) {
            const p = this.particles[i];
            buckets[p.colorBucket].push(p);
        }

        for (let b = 0; b < buckets.length; b++) {
            const list = buckets[b];
            if (list.length === 0) continue;

            ctx.fillStyle = this.colorPalette[b];
            ctx.beginPath();

            for (let i = 0; i < list.length; i++) {
                const p = list[i];
                const size = Math.max(0.6, p.baseSize * p.screenScale * (1.0 + amplitude * 0.45));
                const half = size * 0.5;
                ctx.rect(p.screenX - half, p.screenY - half, size, size);
            }

            ctx.fill();
        }

        ctx.restore();
    }
}

// Export for window access
window.OrbRenderer = OrbRenderer;
