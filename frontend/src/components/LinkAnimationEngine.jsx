/**
 * LinkAnimationEngine: Renders animated traffic flows on canvas links.
 * 
 * CRE-68 Phase 3: Listens to WebSocket traffic events and spawns animated
 * SVG particles (dots) that flow along link paths with filter colors.
 * 
 * Features:
 * - Particle spawning on traffic_match events
 * - Smooth path animation using SVG <animateMotion>
 * - Color-coded by filter (BGP red, OSPF green, etc.)
 * - Link glow effect when active
 * - Auto-cleanup after animation completes
 * - Performance: max 50 particles on screen, throttle spawning
 */
import React, { useState, useEffect, useCallback, useRef } from 'react';
import './LinkAnimationEngine.css';

const MAX_PARTICLES_PER_LINK = 5; // Limit particles per link to prevent lag
const MAX_TOTAL_PARTICLES = 50; // Global limit
const THROTTLE_MS = 100; // Min time between particle spawns for same filter

const LinkAnimationEngine = ({ links, trafficEvents, activeFilters }) => {
  const [particles, setParticles] = useState([]); // Array of {id, linkId, color, duration, path}
  const particleCounterRef = useRef(0);
  const lastSpawnTimeRef = useRef({}); // {filter_id: timestamp}

  // Clean up old particles
  const removeParticle = useCallback((particleId) => {
    setParticles(prev => prev.filter(p => p.id !== particleId));
  }, []);

  // Spawn a new particle on a link
  const spawnParticle = useCallback((linkId, color, duration) => {
    const now = Date.now();
    
    // Throttle: Don't spawn too frequently
    const filterId = `${linkId}-${color}`; // Unique key per link+color combo
    const lastSpawn = lastSpawnTimeRef.current[filterId] || 0;
    if (now - lastSpawn < THROTTLE_MS) {
      return; // Skip this spawn
    }
    lastSpawnTimeRef.current[filterId] = now;

    // Check limits
    setParticles(prev => {
      const linkParticles = prev.filter(p => p.linkId === linkId);
      if (linkParticles.length >= MAX_PARTICLES_PER_LINK) {
        return prev; // Link already has max particles
      }
      if (prev.length >= MAX_TOTAL_PARTICLES) {
        // Remove oldest particle
        const oldest = prev[0];
        if (oldest) removeParticle(oldest.id);
        return prev.slice(1);
      }

      // Find the link path
      const link = links.find(l => l.id === linkId);
      if (!link || !link.path) {
        console.warn(`Link ${linkId} not found or has no path`);
        return prev;
      }

      // Create new particle
      const particleId = `particle-${particleCounterRef.current++}`;
      const newParticle = {
        id: particleId,
        linkId,
        color,
        duration,
        path: link.path,
        createdAt: now
      };

      // Schedule removal after animation completes
      setTimeout(() => removeParticle(particleId), duration);

      return [...prev, newParticle];
    });
  }, [links, removeParticle]);

  // Listen to traffic events and spawn particles
  useEffect(() => {
    if (!trafficEvents || trafficEvents.length === 0) return;

    const latestEvent = trafficEvents[trafficEvents.length - 1];
    
    if (latestEvent.type === 'traffic_match') {
      const { filter_id, link_id } = latestEvent;
      
      // Find filter details (color, duration)
      const filter = activeFilters.get(filter_id);
      if (!filter) {
        console.warn(`Filter ${filter_id} not found in activeFilters`);
        return;
      }

      spawnParticle(link_id, filter.color, filter.duration);
    }
    else if (latestEvent.type === 'traffic_batch') {
      // CRE-68 Phase 3 Milestone 4 Task 3: Handle batched events
      // Expand batch into individual particle animations
      const { events, count } = latestEvent;
      
      if (!events || events.length === 0) {
        console.warn('traffic_batch with no events', latestEvent);
        return;
      }

      // Stagger animations slightly to avoid all particles spawning at once
      // Spread over 100ms (matching backend batch interval)
      const staggerDelay = events.length > 1 ? 100 / events.length : 0;

      events.forEach((packet, idx) => {
        const { filter_id, link_id } = packet;
        
        // Find filter details (color, duration)
        const filter = activeFilters.get(filter_id);
        if (!filter) {
          console.warn(`Filter ${filter_id} not found in activeFilters (batch event ${idx})`);
          return;
        }

        // Spawn with staggered timing for smooth visual flow
        if (staggerDelay > 0 && idx > 0) {
          setTimeout(() => {
            spawnParticle(link_id, filter.color, filter.duration);
          }, idx * staggerDelay);
        } else {
          spawnParticle(link_id, filter.color, filter.duration);
        }
      });
    }
  }, [trafficEvents, activeFilters, spawnParticle]);

  // Render particles as SVG circles with animateMotion
  return (
    <g className="traffic-animation-layer">
      {particles.map(particle => (
        <circle
          key={particle.id}
          r="5"
          fill={particle.color}
          className="traffic-particle"
          style={{
            filter: `drop-shadow(0 0 6px ${particle.color})`
          }}
        >
          <animateMotion
            dur={`${particle.duration}ms`}
            path={particle.path}
            repeatCount="1"
            fill="freeze"
          />
          {/* Fade out near the end */}
          <animate
            attributeName="opacity"
            values="0;1;1;0"
            keyTimes="0;0.1;0.8;1"
            dur={`${particle.duration}ms`}
            repeatCount="1"
          />
          {/* Pulse effect */}
          <animate
            attributeName="r"
            values="5;7;5"
            dur="1s"
            repeatCount="indefinite"
          />
        </circle>
      ))}
    </g>
  );
};

export default LinkAnimationEngine;
