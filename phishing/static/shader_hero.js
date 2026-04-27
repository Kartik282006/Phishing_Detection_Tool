// Sparkles Animation - Adapted from React tsParticles to Vanilla JS
// Uses @tsparticles/slim bundle

document.addEventListener("DOMContentLoaded", async () => {
    // Create container if it doesn't exist (though tsparticles can create a canvas)
    // We will let tsParticles create the canvas by targeting an ID.
    // The previous code created 'shaderCanvas'. We can reuse that ID or just let tsparticles handle "tsparticles" id.

    // Create a div for tsparticles to live in, to ensure z-index correctness
    const particlesDiv = document.createElement('div');
    particlesDiv.id = 'tsparticles';
    particlesDiv.style.position = 'fixed';
    particlesDiv.style.top = '0';
    particlesDiv.style.left = '0';
    particlesDiv.style.width = '100%';
    particlesDiv.style.height = '100%';
    particlesDiv.style.zIndex = '-1';
    document.body.prepend(particlesDiv);

    // Remove old shaderCanvas if it exists (from previous script execution)
    const oldCanvas = document.getElementById('shaderCanvas');
    if (oldCanvas) {
        oldCanvas.remove();
    }

    await tsParticles.load({
        id: "tsparticles",
        options: {
            background: {
                color: {
                    value: "transparent", // Let CSS handle background color
                },
            },
            fullScreen: {
                enable: false, // We are using a fixed div
                zIndex: -1,
            },
            fpsLimit: 120,
            interactivity: {
                events: {
                    onClick: {
                        enable: true,
                        mode: "push",
                    },
                    onHover: {
                        enable: false,
                        mode: "repulse",
                    },
                    resize: true,
                },
                modes: {
                    push: {
                        quantity: 4,
                    },
                    repulse: {
                        distance: 200,
                        duration: 0.4,
                    },
                },
            },
            particles: {
                bounce: {
                    horizontal: { value: 1 },
                    vertical: { value: 1 },
                },
                collisions: {
                    enable: false,
                },
                color: {
                    value: "#ffffff",
                },
                move: {
                    direction: "none",
                    enable: true,
                    outModes: {
                        default: "out",
                    },
                    random: false,
                    speed: {
                        min: 0.1,
                        max: 1,
                    },
                    straight: false,
                },
                number: {
                    density: {
                        enable: true,
                        width: 400, // area
                        height: 400,
                    },
                    value: 100, // particleDensity
                },
                opacity: {
                    value: { min: 0.1, max: 1 },
                    animation: {
                        enable: true,
                        speed: 1, // Speed
                        sync: false,
                        startValue: "random",
                    },
                },
                shape: {
                    type: "circle",
                },
                size: {
                    value: { min: 0.6, max: 1.4 },
                },
            },
            detectRetina: true,
        },
    });

    console.log("Sparkles initialized");
});
