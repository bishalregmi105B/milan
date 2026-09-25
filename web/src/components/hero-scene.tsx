"use client";

// The hero's 3D stage — pure CSS transforms, no animation libraries.
//
// Layer 1  · a field of marigold petals, dhaka hearts and rice-cream petals
//            distributed across translateZ depth slices, drifting downward on
//            independent negative-delay loops (so the field is full on load).
// Layer 2  · a phone mockup built from divs — a stylized Milan chat with
//            Messenger-like bubbles and animated typing dots — floating in
//            3D space with floating trust chips at their own depths.
//
// Pointer movement eases two CSS variables (--mx / --my, -1..1) through a
// rAF lerp; petals and phone tilt by different magnitudes of the same
// variables, which produces parallax between depth layers. Everything is
// inert under prefers-reduced-motion (globals.css kill-switch + guards here).

import { useEffect, useRef } from "react";
import { IconBadgeCheck, IconSend } from "./icons";

/* ── Deterministic petal field (same values on server and client) ─────── */

function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

interface Petal {
  left: number; // % across the hero
  size: number; // px
  z: number; // px into the scene
  dur: number; // fall duration, s
  delay: number; // negative delay → starts mid-fall
  sway: number; // lateral drift, vw
  spin: number; // total rotation over one fall, deg
  baseRotate: number; // resting rotation
  kind: "petal" | "heart";
  style: React.CSSProperties; // background (petal) or fill via color (heart)
}

function buildPetals(count: number): Petal[] {
  const rand = mulberry32(20260902);
  const petals: Petal[] = [];
  for (let i = 0; i < count; i++) {
    const alpha = 0.28 + rand() * 0.42;
    const heart = rand() < 0.32;
    const toneRoll = rand();
    let style: Petal["style"];
    if (heart) {
      style =
        toneRoll < 0.5
          ? { color: `rgba(238,152,20,${alpha + 0.08})` }
          : { color: `rgba(123,30,58,${alpha * 0.72})` };
    } else if (toneRoll < 0.42) {
      // marigold petal
      style = {
        background: `linear-gradient(135deg, rgba(245,166,35,${alpha + 0.06}), rgba(224,146,15,${alpha}))`,
      };
    } else if (toneRoll < 0.72) {
      // rice-cream petal
      style = {
        background: `linear-gradient(135deg, rgba(253,233,200,${Math.min(1, alpha + 0.18)}), rgba(248,192,106,${alpha * 0.85}))`,
      };
    } else {
      // dhaka crimson petal
      style = {
        background: `linear-gradient(135deg, rgba(123,30,58,${alpha * 0.8}), rgba(158,47,80,${alpha * 0.7}))`,
      };
    }
    const dur = 14 + rand() * 12;
    petals.push({
      left: -3 + rand() * 106,
      size: heart ? 11 + rand() * 9 : 10 + rand() * 14,
      z: -300 + rand() * 500,
      dur,
      delay: -rand() * dur,
      sway: -4 + rand() * 10,
      spin: 180 + rand() * 380,
      baseRotate: -40 + rand() * 120,
      kind: heart ? "heart" : "petal",
      style,
    });
  }
  return petals;
}

const PETALS = buildPetals(30);

function PetalSpecimen({ petal }: { petal: Petal }) {
  return (
    <span
      aria-hidden="true"
      className="absolute top-0 block"
      style={{
        left: `${petal.left}%`,
        transform: `translateZ(${petal.z}px) rotate(${petal.baseRotate}deg)`,
      }}
    >
      <span
        className="petal-drift block"
        style={
          {
            "--sway": `${petal.sway}vw`,
            "--spin": `${petal.spin}deg`,
            "--dur": `${petal.dur}s`,
            "--delay": `${petal.delay}s`,
          } as React.CSSProperties
        }
      >
        {petal.kind === "heart" ? (
          <svg width={petal.size} height={petal.size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" style={petal.style}>
            <path d="M12 20.5C7.2 17 3.5 13.6 3.5 9.9 3.5 7.4 5.4 5.5 7.8 5.5c1.7 0 3.2 1 4.2 2.5 1-1.5 2.5-2.5 4.2-2.5 2.4 0 4.3 1.9 4.3 4.4 0 3.7-3.7 7.1-8.5 10.6z" />
          </svg>
        ) : (
          <span
            className="block"
            style={{
              width: petal.size,
              height: Math.round(petal.size * 0.62),
              borderRadius: "999px 999px 999px 2px",
              ...petal.style,
            }}
          />
        )}
      </span>
    </span>
  );
}

/* ── Phone mockup — a stylized Milan chat ─────────────────────────────── */

function TypingDot({ delay }: { delay: number }) {
  return (
    <span
      className="typing-dot inline-block h-1.5 w-1.5 rounded-full bg-night-300"
      style={{ animationDelay: `${delay}s` }}
    />
  );
}

function PhoneMockup() {
  return (
    <div className="relative">
      {/* Warm glow pooled behind the phone (deep in the scene) */}
      <div
        aria-hidden="true"
        className="absolute -inset-10 rounded-[64px]"
        style={{
          transform: "translateZ(-70px)",
          background:
            "radial-gradient(closest-side, rgba(245,166,35,0.28), transparent 72%), radial-gradient(closest-side at 30% 75%, rgba(123,30,58,0.14), transparent 75%)",
          filter: "blur(14px)",
        }}
      />

      <div className="milan-float">
        <div className="w-[288px] rounded-[42px] border border-night-700/30 bg-night-900 p-[9px] shadow-floating sm:w-[318px]">
          <div className="relative overflow-hidden rounded-[34px] bg-paper-0">
            {/* Chat wallpaper — faint dhaka dot-grid */}
            <div
              aria-hidden="true"
              className="absolute inset-0"
              style={{
                backgroundImage: "radial-gradient(rgba(123,30,58,0.06) 1px, transparent 1.2px)",
                backgroundSize: "16px 16px",
              }}
            />
            {/* Notch */}
            <div aria-hidden="true" className="absolute left-1/2 top-2 z-10 h-[20px] w-[88px] -translate-x-1/2 rounded-full bg-night-900" />

            {/* Status bar */}
            <div aria-hidden="true" className="relative flex items-center justify-between px-6 pb-1 pt-2 text-[10px] font-bold text-night-900">
              <span>9:41</span>
              <span className="flex items-end gap-[3px]">
                <span className="h-1.5 w-[3px] rounded-sm bg-night-900" />
                <span className="h-2 w-[3px] rounded-sm bg-night-900" />
                <span className="h-2.5 w-[3px] rounded-sm bg-night-900" />
                <span className="ml-1 h-2 w-4 rounded-[3px] border border-night-900/70" />
              </span>
            </div>

            {/* Chat header — Asha, clearly labeled AI */}
            <div className="relative flex items-center gap-2.5 border-b border-line200 bg-paper-50/90 px-4 pb-2.5 pt-1.5 backdrop-blur-sm">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#7d8fa3" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M14.5 6l-6 6 6 6" />
              </svg>
              <span className="relative grid h-9 w-9 shrink-0 place-items-center rounded-full bg-marigold-100 font-display text-sm font-bold text-marigold-700">
                अ
                <span aria-hidden="true" className="presence-dot absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-2 border-paper-50 bg-pine-500" />
              </span>
              <span className="min-w-0">
                <span className="block text-[13px] font-bold leading-tight text-night-900">Asha</span>
                <span className="block text-[10.5px] leading-tight text-night-400">online · replies in seconds</span>
              </span>
              <span className="ml-auto shrink-0 rounded-full bg-dhaka-100 px-2 py-0.5 text-[9.5px] font-bold uppercase tracking-wide text-dhaka-700">
                AI · साथी
              </span>
            </div>

            {/* Messages */}
            <div className="relative space-y-2 px-3.5 py-4">
              <p className="text-center text-[9.5px] font-semibold uppercase tracking-widest text-night-300">
                आज · Today
              </p>

              <div className="chat-in max-w-[82%] rounded-2xl rounded-bl-md border border-line200 bg-white px-3.5 py-2 text-[12.5px] leading-snug text-night-900 shadow-raised" style={{ animationDelay: "0.35s" }}>
                Good morning! Aaja momo khane din ho?
              </div>

              <div className="chat-in ml-auto max-w-[82%] rounded-2xl rounded-br-md bg-action-500 px-3.5 py-2 text-[12.5px] leading-snug text-white shadow-[0_3px_10px_rgba(11,132,254,0.28)]" style={{ animationDelay: "0.7s" }}>
                Obviously momo. Buff, extra achar.
              </div>

              <div className="chat-in max-w-[82%] rounded-2xl rounded-bl-md border border-line200 bg-white px-3.5 py-2 text-[12.5px] leading-snug text-night-900 shadow-raised" style={{ animationDelay: "1.05s" }}>
                Tyo bhanda ke chahiyo? Save the evening — 6 pm, my treat.
              </div>

              <div className="chat-in flex w-fit items-center gap-1 rounded-2xl rounded-bl-md border border-line200 bg-white px-3 py-2.5 shadow-raised" style={{ animationDelay: "1.45s" }}>
                <TypingDot delay={0} />
                <TypingDot delay={0.16} />
                <TypingDot delay={0.32} />
              </div>
            </div>

            {/* Input */}
            <div className="relative flex items-center gap-2 border-t border-line100 bg-paper-50/95 px-3.5 py-3">
              <div className="h-9 flex-1 rounded-full border border-line200 bg-white px-3.5 text-[12px] leading-[34px] text-night-300">
                Message…
              </div>
              <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-action-500 text-white shadow-[0_3px_10px_rgba(11,132,254,0.35)]">
                <IconSend size={15} />
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Floating trust chips — each at its own depth */}
      <div aria-hidden="true" className="absolute -left-8 top-16 hidden sm:block" style={{ transform: "translateZ(120px)" }}>
        <span className="milan-float flex items-center gap-1.5 rounded-full border border-line200 bg-white/95 px-3 py-1.5 text-[11px] font-bold text-night-900 shadow-floating" style={{ animationDuration: "9s", animationDelay: "-2.2s" }}>
          <IconBadgeCheck size={14} className="text-pine-600" />
          Liveness verified
        </span>
      </div>
      <div aria-hidden="true" className="absolute -right-6 top-1/2 hidden sm:block" style={{ transform: "translateZ(150px)" }}>
        <span className="milan-float flex items-center gap-1.5 rounded-full bg-marigold-500 px-3 py-1.5 text-[11px] font-bold text-ink-900 shadow-floating" style={{ animationDuration: "8s", animationDelay: "-4.5s" }}>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <path d="M12 20.5C7.2 17 3.5 13.6 3.5 9.9 3.5 7.4 5.4 5.5 7.8 5.5c1.7 0 3.2 1 4.2 2.5 1-1.5 2.5-2.5 4.2-2.5 2.4 0 4.3 1.9 4.3 4.4 0 3.7-3.7 7.1-8.5 10.6z" />
          </svg>
          98% match
        </span>
      </div>
      <div aria-hidden="true" className="absolute -bottom-4 -left-4 hidden sm:block" style={{ transform: "translateZ(90px)" }}>
        <span className="milan-float rounded-full border border-dhaka-200 bg-dhaka-100/95 px-3 py-1.5 text-[11px] font-bold text-dhaka-700 shadow-floating" style={{ animationDuration: "10s", animationDelay: "-1s" }}>
          Always labeled AI
        </span>
      </div>
    </div>
  );
}

/* ── HeroScene — petals + copy slot + phone, all in one tilted stage ──── */

export function HeroScene({ children }: { children: React.ReactNode }) {
  const rootRef = useRef<HTMLElement>(null);
  const target = useRef({ x: 0, y: 0 });
  const current = useRef({ x: 0, y: 0 });
  const rafRef = useRef<number | null>(null);
  const enabledRef = useRef(false);

  useEffect(() => {
    enabledRef.current =
      !window.matchMedia("(prefers-reduced-motion: reduce)").matches &&
      window.matchMedia("(pointer: fine)").matches;
    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    };
  }, []);

  const tick = () => {
    rafRef.current = null;
    const c = current.current;
    const t = target.current;
    c.x += (t.x - c.x) * 0.085;
    c.y += (t.y - c.y) * 0.085;
    const root = rootRef.current;
    if (root) {
      root.style.setProperty("--mx", c.x.toFixed(4));
      root.style.setProperty("--my", c.y.toFixed(4));
    }
    if (Math.abs(t.x - c.x) + Math.abs(t.y - c.y) > 0.0015) {
      rafRef.current = requestAnimationFrame(tick);
    }
  };

  const kick = () => {
    if (rafRef.current === null) rafRef.current = requestAnimationFrame(tick);
  };

  const onPointerMove = (e: React.PointerEvent<HTMLElement>) => {
    if (!enabledRef.current) return;
    const rect = rootRef.current?.getBoundingClientRect();
    if (!rect || rect.width === 0 || rect.height === 0) return;
    target.current = {
      x: ((e.clientX - rect.left) / rect.width - 0.5) * 2,
      y: ((e.clientY - rect.top) / rect.height - 0.5) * 2,
    };
    kick();
  };

  const onPointerLeave = () => {
    if (!enabledRef.current) return;
    target.current = { x: 0, y: 0 };
    kick();
  };

  return (
    <section
      ref={rootRef}
      onPointerMove={onPointerMove}
      onPointerLeave={onPointerLeave}
      className="relative overflow-hidden"
    >
      {/* Warm dawn wash */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse 70% 55% at 50% -10%, rgba(245,166,35,0.17), transparent 65%), radial-gradient(ellipse 40% 35% at 88% 22%, rgba(123,30,58,0.08), transparent 70%), linear-gradient(180deg, #ffffff 0%, #fffbf5 78%)",
        }}
      />

      {/* 3D petal field */}
      <div className="hero-perspective pointer-events-none absolute inset-0" aria-hidden="true">
        <div
          className="scene3d absolute inset-0"
          style={{ transform: "rotateX(calc(var(--my, 0) * -4.5deg)) rotateY(calc(var(--mx, 0) * 7deg))" }}
        >
          {PETALS.map((petal, i) => (
            <PetalSpecimen key={i} petal={petal} />
          ))}
        </div>
      </div>

      {/* Content grid — copy (children) + floating phone */}
      <div className="relative z-10 mx-auto grid min-h-[calc(100svh-4rem)] w-full max-w-6xl items-center gap-14 px-6 pb-20 pt-14 sm:pt-16 lg:grid-cols-[1.04fr_0.96fr] lg:gap-8">
        <div className="text-center lg:text-left">{children}</div>

        <div className="hero-perspective flex justify-center lg:justify-end lg:pr-4">
          <div
            className="scene3d relative"
            style={{ transform: "rotateX(calc(var(--my, 0) * -2.4deg)) rotateY(calc(var(--mx, 0) * 4deg))" }}
          >
            <PhoneMockup />
          </div>
        </div>
      </div>
    </section>
  );
}
