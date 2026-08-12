// MapLibre v6 loads its web worker via `new URL('./maplibre-gl-worker.mjs',
// import.meta.url)`. Next.js does not emit that file as a static asset, so
// the worker 404s silently and the map never finishes loading a style.
// Fix: vendor the worker (and the shared chunk it imports) into public/ and
// point MapLibre at it with setWorkerUrl() — see components/MapView.tsx.
// Runs automatically via the predev/prebuild npm scripts.
import { copyFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(fileURLToPath(import.meta.url));
const dist = join(root, "..", "node_modules", "maplibre-gl", "dist");
const dest = join(root, "..", "public", "maplibre");

mkdirSync(dest, { recursive: true });
for (const f of ["maplibre-gl-worker.mjs", "maplibre-gl-shared.mjs"]) {
  copyFileSync(join(dist, f), join(dest, f));
}
console.log("copied maplibre worker ->", dest);
