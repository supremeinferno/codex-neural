import React from "react";

function Atmosphere() {
  const particles = Array.from({ length: 70 });

  return (
    <div className="atmosphere" aria-hidden="true">

      {/* Deep ambient glows */}
      <div className="atmo-glow atmo-glow-1"></div>
      <div className="atmo-glow atmo-glow-2"></div>
      <div className="atmo-glow atmo-glow-3"></div>

      {/* Fine moving light */}
      <div className="atmo-grid"></div>

      {/* Floating particles */}
      <div className="particle-field">
        {particles.map((_, index) => (
          <span
            key={index}
            className="particle"
            style={{
              "--x": `${Math.random() * 100}%`,
              "--delay": `${Math.random() * 12}s`,
              "--duration": `${8 + Math.random() * 14}s`,
              "--size": `${1 + Math.random() * 2.5}px`,
              "--drift": `${-80 + Math.random() * 160}px`,
            }}
          />
        ))}
      </div>

      {/* Shooting stars */}
      <div className="shooting-stars">
        <span className="shooting-star"></span>
        <span className="shooting-star"></span>
        <span className="shooting-star"></span>
        <span className="shooting-star"></span>
      </div>

      {/* Floating energy cores */}
      <div className="energy-core core-1"></div>
      <div className="energy-core core-2"></div>
      <div className="energy-core core-3"></div>

      {/* Orbital rings intentionally disabled */}
      <div className="orbit orbit-1"></div>
      <div className="orbit orbit-2"></div>
      <div className="orbit orbit-3"></div>

    </div>
  );
}

export default Atmosphere;