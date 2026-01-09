'use client';

import { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';

export default function AIModel3D() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Set canvas size
    const updateSize = () => {
      const dpr = window.devicePixelRatio || 1;
      const rect = canvas.getBoundingClientRect();
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      ctx.scale(dpr, dpr);
    };
    updateSize();
    window.addEventListener('resize', updateSize);

    // Neural network nodes
    const nodes: Array<{ x: number; y: number; vx: number; vy: number; connections: number[] }> = [];
    const nodeCount = 50;
    const centerX = canvas.width / (window.devicePixelRatio || 1) / 2;
    const centerY = canvas.height / (window.devicePixelRatio || 1) / 2;
    const radius = 150;

    // Initialize nodes in a sphere-like distribution
    for (let i = 0; i < nodeCount; i++) {
      const angle = (i / nodeCount) * Math.PI * 2;
      const layer = Math.floor(i / 10);
      const layerRadius = radius * (0.5 + (layer / 5) * 0.5);
      
      nodes.push({
        x: centerX + Math.cos(angle) * layerRadius,
        y: centerY + Math.sin(angle) * layerRadius,
        vx: (Math.random() - 0.5) * 0.5,
        vy: (Math.random() - 0.5) * 0.5,
        connections: [],
      });
    }

    // Create connections (each node connects to 3-5 nearby nodes)
    nodes.forEach((node, i) => {
      const distances = nodes.map((n, j) => ({
        index: j,
        dist: Math.hypot(n.x - node.x, n.y - node.y),
      }));
      distances.sort((a, b) => a.dist - b.dist);
      
      const connectionCount = 3 + Math.floor(Math.random() * 3);
      for (let j = 1; j <= connectionCount && j < distances.length; j++) {
        node.connections.push(distances[j].index);
      }
    });

    // Particles for extra effect
    const particles: Array<{ x: number; y: number; vx: number; vy: number; size: number }> = [];
    for (let i = 0; i < 30; i++) {
      particles.push({
        x: Math.random() * (canvas.width / (window.devicePixelRatio || 1)),
        y: Math.random() * (canvas.height / (window.devicePixelRatio || 1)),
        vx: (Math.random() - 0.5) * 1,
        vy: (Math.random() - 0.5) * 1,
        size: 1 + Math.random() * 2,
      });
    }

    let time = 0;
    let animationId: number;

    const animate = () => {
      const w = canvas.width / (window.devicePixelRatio || 1);
      const h = canvas.height / (window.devicePixelRatio || 1);

      // Clear canvas with fade effect
      ctx.fillStyle = 'rgba(15, 23, 42, 0.1)';
      ctx.fillRect(0, 0, w, h);

      time += 0.01;

      // Update and draw nodes
      nodes.forEach((node, i) => {
        // Gentle floating motion
        node.x += node.vx + Math.sin(time + i) * 0.1;
        node.y += node.vy + Math.cos(time + i) * 0.1;

        // Boundary check with smooth bounce
        if (node.x < 50 || node.x > w - 50) node.vx *= -0.9;
        if (node.y < 50 || node.y > h - 50) node.vy *= -0.9;

        // Keep nodes in bounds
        node.x = Math.max(50, Math.min(w - 50, node.x));
        node.y = Math.max(50, Math.min(h - 50, node.y));

        // Draw connections
        ctx.strokeStyle = `rgba(34, 211, 238, ${0.15 + Math.sin(time + i) * 0.1})`;
        ctx.lineWidth = 1;
        node.connections.forEach((targetIndex) => {
          const target = nodes[targetIndex];
          ctx.beginPath();
          ctx.moveTo(node.x, node.y);
          ctx.lineTo(target.x, target.y);
          ctx.stroke();
        });

        // Draw node with glow
        const pulse = 0.8 + Math.sin(time * 2 + i) * 0.2;
        const gradient = ctx.createRadialGradient(node.x, node.y, 0, node.x, node.y, 8 * pulse);
        gradient.addColorStop(0, `rgba(34, 211, 238, ${0.8 * pulse})`);
        gradient.addColorStop(0.5, `rgba(168, 85, 247, ${0.4 * pulse})`);
        gradient.addColorStop(1, 'rgba(168, 85, 247, 0)');
        
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(node.x, node.y, 8 * pulse, 0, Math.PI * 2);
        ctx.fill();

        // Core node
        ctx.fillStyle = '#22d3ee';
        ctx.beginPath();
        ctx.arc(node.x, node.y, 2, 0, Math.PI * 2);
        ctx.fill();
      });

      // Update and draw particles
      particles.forEach((particle) => {
        particle.x += particle.vx;
        particle.y += particle.vy;

        // Wrap around edges
        if (particle.x < 0) particle.x = w;
        if (particle.x > w) particle.x = 0;
        if (particle.y < 0) particle.y = h;
        if (particle.y > h) particle.y = 0;

        // Draw particle
        const alpha = 0.3 + Math.sin(time * 3 + particle.x) * 0.2;
        ctx.fillStyle = `rgba(168, 85, 247, ${alpha})`;
        ctx.beginPath();
        ctx.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2);
        ctx.fill();
      });

      animationId = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      cancelAnimationFrame(animationId);
      window.removeEventListener('resize', updateSize);
    };
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.8 }}
      className="relative w-full h-full"
    >
      <canvas
        ref={canvasRef}
        className="w-full h-full"
        style={{ width: '100%', height: '100%' }}
      />
      
      {/* Center glow effect */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-64 h-64 bg-cyan-500/20 rounded-full blur-[100px] pointer-events-none" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-48 h-48 bg-purple-500/20 rounded-full blur-[80px] pointer-events-none" />
    </motion.div>
  );
}
