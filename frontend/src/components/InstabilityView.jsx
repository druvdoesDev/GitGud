import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

const MIN_RADIUS = 28;
const MAX_RADIUS = 78;

const MIN_SPEED = 0.35;
const MAX_SPEED = 2.8;

const COLLISION_BOUNCE = 0.92;
const BURST_THRESHOLD = 0.30;

const ROUTE_ORDER = [
  "home",
  "product",
  "cart",
  "checkout",
  "confirmation",
];

const FALLBACK_NAMES = [
  "Flow Drift",
  "Navigation Bounce",
  "Path Detour",
  "Behavior Shift",
];

function seededRandom(seed) {
  let value = seed >>> 0;

  return () => {
    value += 0x6d2b79f5;

    let t = value;

    t = Math.imul(
      t ^ (t >>> 15),
      t | 1
    );

    t ^= t + Math.imul(
      t ^ (t >>> 7),
      t | 61
    );

    return (
      ((t ^ (t >>> 14)) >>> 0) /
      4294967296
    );
  };
}

function stringHash(value) {
  let hash = 2166136261;

  for (let i = 0; i < value.length; i++) {
    hash ^= value.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }

  return hash >>> 0;
}

function getRouteIndex(name) {
  return ROUTE_ORDER.indexOf(
    String(name).toLowerCase()
  );
}

function getBehaviorName(deviation, index) {
  const from = getRouteIndex(deviation.from);
  const to = getRouteIndex(deviation.to);

  if (from >= 0 && to >= 0) {
    if (to < from) {
      return "Backtrack";
    }

    if (
      String(deviation.to).toLowerCase() ===
      "confirmation"
    ) {
      return "Completion Push";
    }

    if (
      String(deviation.from).toLowerCase() ===
      "checkout"
    ) {
      return "Checkout Shift";
    }

    if (to > from) {
      return "Forward Flow";
    }
  }

  if (deviation.severity === "high") {
    return "Routing Surge";
  }

  if (deviation.severity === "medium") {
    return "Behavior Shift";
  }

  return (
    FALLBACK_NAMES[index % FALLBACK_NAMES.length]
  );
}

function getColors() {
  const dark =
    document.documentElement.dataset.theme ===
    "dark";

  return {
    dark,

    low: dark
      ? "#78b4ff"
      : "#3578d4",

    medium: dark
      ? "#f2b552"
      : "#d97706",

    high: dark
      ? "#ff7078"
      : "#cf222e",
  };
}

function radiusFor(magnitude) {
  return (
    MIN_RADIUS +
    (MAX_RADIUS - MIN_RADIUS) *
      Math.min(Math.abs(magnitude), 1)
  );
}

function speedFor(magnitude) {
  return (
    MIN_SPEED +
    (MAX_SPEED - MIN_SPEED) *
      Math.min(Math.abs(magnitude), 1)
  );
}

function createBubble(
  deviation,
  index,
  width,
  height
) {
  const random = seededRandom(
    stringHash(
      `${deviation.from}|${deviation.to}|${index}`
    )
  );

  const magnitude = Math.abs(
    Number(deviation.magnitude ?? 0)
  );

  const radius = radiusFor(
    magnitude
  );

  const speed = speedFor(
    magnitude
  );

  const angle =
    random() * Math.PI * 2;

  const safeWidth = Math.max(
    width,
    radius * 2 + 20
  );

  const safeHeight = Math.max(
    height,
    radius * 2 + 20
  );

  const colors = getColors();

  const severity =
    deviation.severity ?? "low";

  const color =
    severity === "high"
      ? colors.high
      : severity === "medium"
      ? colors.medium
      : colors.low;

  return {
    id:
      `${deviation.from}-` +
      `${deviation.to}-` +
      `${index}`,

    name: getBehaviorName(
      deviation,
      index
    ),

    from: deviation.from,
    to: deviation.to,

    severity,

    magnitude,

    delta: Number(
      deviation.absolute_delta ?? 0
    ),

    radius,

    color,

    x:
      radius +
      random() *
        Math.max(
          10,
          safeWidth - radius * 2
        ),

    y:
      radius +
      random() *
        Math.max(
          10,
          safeHeight - radius * 2
        ),

    vx:
      Math.cos(angle) * speed,

    vy:
      Math.sin(angle) * speed,

    age:
      random() * 700,

    burstTimer: 0,

    bursting: false,
    escaped: false,
  };
}

export default function InstabilityView({
  deviations,
}) {
  const fieldRef = useRef(null);

  const bubbleElementsRef =
    useRef(new Map());

  const bubblesRef =
    useRef([]);

  const frameRef =
    useRef(null);

  const sizeRef = useRef({
    width: 900,
    height: 500,
  });

  const [size, setSize] =
    useState({
      width: 900,
      height: 500,
    });

  const [ready, setReady] =
    useState(false);

  const isEmpty =
    !deviations ||
    deviations.length === 0;

  /* ================================================================
     MEASURE FIELD
     ================================================================ */

  useEffect(() => {
    const field =
      fieldRef.current;

    if (!field) return;

    const measure = () => {
      const rect =
        field.getBoundingClientRect();

      const width = Math.max(
        420,
        Math.floor(rect.width)
      );

      const height = Math.max(
        420,
        Math.floor(rect.height)
      );

      sizeRef.current = {
        width,
        height,
      };

      setSize({
        width,
        height,
      });

      setReady(true);
    };

    measure();

    const observer =
      new ResizeObserver(measure);

    observer.observe(field);

    return () =>
      observer.disconnect();
  }, []);

  /* ================================================================
     BUILD BUBBLES
     ================================================================ */

  useEffect(() => {
    if (isEmpty || !ready) {
      bubblesRef.current = [];
      return;
    }

    const {
      width,
      height,
    } = sizeRef.current;

    bubblesRef.current =
      deviations.map(
        (deviation, index) =>
          createBubble(
            deviation,
            index,
            width,
            height
          )
      );
  }, [
    deviations,
    isEmpty,
    ready,
    size.width,
    size.height,
  ]);

  /* ================================================================
     DOM REF REGISTRATION
     ================================================================ */

  const registerBubble =
    useCallback(
      (id, element) => {
        if (element) {
          bubbleElementsRef.current.set(
            id,
            element
          );
        } else {
          bubbleElementsRef.current.delete(
            id
          );
        }
      },
      []
    );

  /* ================================================================
     PHYSICS
     ================================================================ */

  const resolveCollisions =
    useCallback(() => {
      const bubbles =
        bubblesRef.current;

      const {
        width,
        height,
      } = sizeRef.current;

      for (
        let i = 0;
        i < bubbles.length;
        i++
      ) {
        const a = bubbles[i];

        if (
          a.escaped ||
          a.bursting
        ) {
          continue;
        }

        for (
          let j = i + 1;
          j < bubbles.length;
          j++
        ) {
          const b = bubbles[j];

          if (
            b.escaped ||
            b.bursting
          ) {
            continue;
          }

          let dx = b.x - a.x;
          let dy = b.y - a.y;

          let distance =
            Math.hypot(
              dx,
              dy
            );

          if (distance < 0.001) {
            distance = 0.001;
            dx = 0.001;
            dy = 0;
          }

          const nx =
            dx / distance;

          const ny =
            dy / distance;

          const minDistance =
            a.radius +
            b.radius;

          if (
            distance >=
            minDistance
          ) {
            continue;
          }

          const overlap =
            minDistance -
            distance;

          a.x -=
            nx *
            overlap *
            0.5;

          a.y -=
            ny *
            overlap *
            0.5;

          b.x +=
            nx *
            overlap *
            0.5;

          b.y +=
            ny *
            overlap *
            0.5;

          const relativeX =
            b.vx - a.vx;

          const relativeY =
            b.vy - a.vy;

          const velocityAlongNormal =
            relativeX * nx +
            relativeY * ny;

          if (
            velocityAlongNormal > 0
          ) {
            continue;
          }

          const impulse =
            -velocityAlongNormal *
            COLLISION_BOUNCE;

          a.vx -=
            impulse * nx;

          a.vy -=
            impulse * ny;

          b.vx +=
            impulse * nx;

          b.vy +=
            impulse * ny;
        }
      }

      for (const bubble of bubbles) {
        if (
          bubble.escaped ||
          bubble.bursting
        ) {
          continue;
        }

        if (
          bubble.x -
            bubble.radius <
          0
        ) {
          bubble.x =
            bubble.radius;

          bubble.vx =
            Math.abs(
              bubble.vx
            );
        }

        if (
          bubble.x +
            bubble.radius >
          width
        ) {
          bubble.x =
            width -
            bubble.radius;

          bubble.vx =
            -Math.abs(
              bubble.vx
            );
        }

        if (
          bubble.y -
            bubble.radius <
          0
        ) {
          bubble.y =
            bubble.radius;

          bubble.vy =
            Math.abs(
              bubble.vy
            );
        }

        if (
          bubble.y +
            bubble.radius >
          height
        ) {
          bubble.y =
            height -
            bubble.radius;

          bubble.vy =
            -Math.abs(
              bubble.vy
            );
        }
      }
    }, []);

  /* ================================================================
     ANIMATION
     ================================================================ */

  const animate =
    useCallback(() => {
      const bubbles =
        bubblesRef.current;

      const {
        width,
        height,
      } = sizeRef.current;

      for (const bubble of bubbles) {
        bubble.age += 16;

        /* High-severity bubbles eventually burst */
        if (
          bubble.severity ===
            "high" &&
          !bubble.bursting &&
          !bubble.escaped &&
          bubble.age > 1700
        ) {
          bubble.bursting = true;
          bubble.burstTimer = 0;
        }

        if (
          bubble.bursting
        ) {
          bubble.burstTimer +=
            16;

          bubble.x +=
            bubble.vx * 1.6;

          bubble.y +=
            bubble.vy * 1.6;
        } else if (
          bubble.escaped
        ) {
          bubble.x +=
            bubble.vx * 1.2;

          bubble.y +=
            bubble.vy * 1.2;
        } else {
          bubble.x +=
            bubble.vx;

          bubble.y +=
            bubble.vy;
        }
      }

      resolveCollisions();

      for (const bubble of bubbles) {
        const element =
          bubbleElementsRef.current.get(
            bubble.id
          );

        if (!element) {
          continue;
        }

        let scale = 1;

        let opacity = 1;

        if (
          bubble.bursting
        ) {
          const progress =
            Math.min(
              bubble.burstTimer /
                420,
              1
            );

          scale =
            1 +
            progress *
              0.75;

          opacity =
            1 - progress * 0.75;

          element.style.setProperty(
            "--burst-progress",
            String(progress)
          );

          if (
            bubble.burstTimer >
            420
          ) {
            bubble.bursting =
              false;

            bubble.escaped =
              true;

            bubble.vx *= 1.35;
            bubble.vy *= 1.35;
          }
        } else if (
          bubble.escaped
        ) {
          opacity = 0.22;
          scale = 0.82;
        }

        element.style.transform =
          `translate3d(` +
          `${bubble.x - bubble.radius}px,` +
          `${bubble.y - bubble.radius}px,0) ` +
          `scale(${scale})`;

        element.style.opacity =
          String(opacity);

        element.style.width =
          `${bubble.radius * 2}px`;

        element.style.height =
          `${bubble.radius * 2}px`;

        element.style.setProperty(
          "--bubble-color",
          bubble.color
        );

        const ring =
          element.querySelector(
            ".instability-burst-ring"
          );

        if (ring) {
          ring.style.opacity =
            bubble.bursting
              ? "1"
              : "0";

          ring.style.transform =
            bubble.bursting
              ? `scale(${
                  1 +
                  Math.min(
                    bubble.burstTimer /
                      150,
                    1
                  )
                })`
              : "scale(.7)";
        }

        const glare =
          element.querySelector(
            ".instability-glare"
          );

        if (glare) {
          glare.style.opacity =
            bubble.escaped
              ? "0"
              : "1";
        }
      }

      frameRef.current =
        requestAnimationFrame(
          animate
        );
    }, [resolveCollisions]);

  useEffect(() => {
    frameRef.current =
      requestAnimationFrame(
        animate
      );

    return () => {
      if (frameRef.current) {
        cancelAnimationFrame(
          frameRef.current
        );
      }
    };
  }, [animate]);

  /* ================================================================
     EMPTY STATE
     ================================================================ */

  if (isEmpty) {
    return (
      <div
        ref={fieldRef}
        className="instability-wrap"
      >
        <div className="instability-empty">
          <div className="instability-empty-icon">
            🫧
          </div>

          <div className="instability-empty-title">
            Waiting for a What-If simulation
          </div>

          <div className="instability-empty-text">
            Run a scenario to populate the
            behavioral stress field.
          </div>
        </div>
      </div>
    );
  }

  /* ================================================================
     VISUAL FIELD
     ================================================================ */

  return (
    <div
      ref={fieldRef}
      className="instability-wrap"
    >
      <div className="instability-field-grid" />

      <div className="instability-field-glow" />

      <div className="instability-field-hud">
        <span>
          {deviations.length} active deviations
        </span>

        <span>
          Live simulation
        </span>
      </div>

      <div className="instability-field-center">
        <span />
      </div>

      {deviations.map(
        (deviation, index) => {
          const bubble =
            bubblesRef.current[index];

          return (
            <div
              key={
                `${deviation.from}-` +
                `${deviation.to}-` +
                `${index}`
              }
              ref={(element) =>
                registerBubble(
                  `${
                    deviation.from
                  }-${
                    deviation.to
                  }-${index}`,
                  element
                )
              }
              className={`instability-bubble severity-${deviation.severity}`}
              style={{
                width: bubble
                  ? bubble.radius * 2
                  : MIN_RADIUS * 2,

                height: bubble
                  ? bubble.radius * 2
                  : MIN_RADIUS * 2,

                "--bubble-color":
                  bubble?.color ??
                  "#78b4ff",
              }}
            >
              <div className="instability-bubble-inner">
                <span className="instability-glare" />

                <span className="instability-bubble-name">
                  {
                    getBehaviorName(
                      deviation,
                      index
                    )
                  }
                </span>

                <span className="instability-bubble-delta">
                  {deviation.absolute_delta >=
                  0
                    ? "+"
                    : ""}
                  {(
                    deviation.absolute_delta *
                    100
                  ).toFixed(1)}
                  %
                </span>

                <span className="instability-bubble-edge">
                  {deviation.from}
                  {" → "}
                  {deviation.to}
                </span>
              </div>

              <span className="instability-burst-ring" />
            </div>
          );
        }
      )}

      <div className="instability-field-footer">
        <span className="instability-footer-dot blue" />
        Low deviation

        <span className="instability-footer-dot yellow" />
        Medium deviation

        <span className="instability-footer-dot red" />
        High deviation
      </div>
    </div>
  );
}