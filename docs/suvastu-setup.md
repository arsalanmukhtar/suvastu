# SUVASTU: Project Setup

> **SUVASTU** (soo-VAAS-too) is the Rigvedic name of the Swat River. Backronym: **S**AR-based **U**nified **V**aluation & **A**ggregate **S**urveillance of **T**ehsil **U**nits.
> Tagline: *Satellite intelligence for a safer, revenue-earning Swat River.*

PERN stack (PostgreSQL/PostGIS, Express, React, Node) with Vite, Tailwind CSS v4, Mapbox GL JS v3, a Python SAR worker and a TiTiler raster server, all in Docker Compose.

---

## 1. Architecture

```
            ┌──────────────────────────┐
 browser ──▶│ web  (React + Vite + TW) │ :5173
            └────────────┬─────────────┘
                         │ /api  (Vite proxy in dev)
            ┌────────────▼─────────────┐      ┌──────────────────────┐
            │ api  (Express, Node 22)  │─────▶│ db  PostGIS 17-3.5   │ :5432
            └────────────┬─────────────┘      └──────────▲───────────┘
                         │ /tiles                        │
            ┌────────────▼─────────────┐      ┌──────────┴───────────┐
            │ tiler (TiTiler/rio-tiler)│◀─────│ worker (Python SAR)  │
            └──────────────────────────┘ COGs └──────────────────────┘
                         ▲                 ./data/cogs
```

| Service | Role | Port |
|---|---|---|
| `db` | PostGIS: reaches, scenes, bar observations, alerts, blocks | 5432 |
| `api` | Express REST + GeoJSON endpoints | 4000 |
| `web` | React 19 + Vite + Tailwind v4 + Mapbox GL JS | 5173 |
| `tiler` | Serves COGs (SAR composites, classifications) as XYZ tiles | 8000 |
| `worker` | Sentinel-1 search, HyP3 RTC/InSAR jobs, classification, change detection | none |

---

## 2. Prerequisites

### 2.1 Machine

- Docker Desktop (WSL2 backend on Windows) or Docker Engine + Compose v2
- Git, Node 22 (only for scaffolding outside Docker)
- About 100 GB free disk for Sentinel-1 RTC/InSAR products over Swat (2019 to 2026)
- On Windows, clone the repo inside the WSL filesystem (`~/projects/...`), not `/mnt/c/...`, or file watching will be slow.

### 2.2 Accounts and credentials

| # | Account | Required | What you get | Goes into `.env` as |
|---|---|---|---|---|
| 1 | **NASA Earthdata Login** (https://urs.earthdata.nasa.gov) | Yes | Username, password, user token | `EARTHDATA_USERNAME`, `EARTHDATA_PASSWORD`, `EARTHDATA_TOKEN` |
| 2 | **Mapbox** (https://account.mapbox.com) | Yes | Public token `pk.*`; optional secret token `sk.*` | `VITE_MAPBOX_TOKEN`, `MAPBOX_SECRET_TOKEN` |
| 3 | **Copernicus Data Space Ecosystem** (https://dataspace.copernicus.eu) | Recommended | Username, password (Sentinel-2 L2A, S1 backup) | `CDSE_USERNAME`, `CDSE_PASSWORD` |

### 2.3 One-time setup steps

**NASA Earthdata**
1. Register, verify email, log in.
2. Profile → *Generate Token* → copy the user token (valid 60 days, regenerate when it expires).
3. Profile → *Applications* → *Authorized Apps* → *Approve More Applications*, then approve:
   - `Alaska Satellite Facility Data Access` (Sentinel-1, ALOS PALSAR downloads)
   - `ASF HyP3` (on-demand RTC and InSAR processing)
   - `NASA GESDISC DATA ARCHIVE` (GPM IMERG rainfall for scene flags)
4. Log in once at https://search.asf.alaska.edu (Vertex) and accept the data use terms.
5. Log in once at https://hyp3-api.asf.alaska.edu and check your monthly processing credits.

**Mapbox**
1. Account → *Tokens* → *Create a token* (public, default scopes). Name it `suvastu-web`.
2. Under *URL restrictions* add `http://localhost:5173` and your production domain. This token is visible in the browser, so restrictions are what protect it.
3. Secret token (`sk.*`) is only needed if you upload tilesets to Mapbox Studio via the Uploads API (scopes `uploads:write`, `tilesets:write`). It must never reach the frontend.

**Copernicus Data Space**
1. Register at dataspace.copernicus.eu. Username and password are enough for OData/S3 downloads through `cdsetool` or `sentinelhub`.

**Do not paste passwords or tokens into chat.** Fill them directly into your local `.env`, which is gitignored.

### 2.4 Open datasets (no account needed)

| Dataset | Source | Use |
|---|---|---|
| Admin boundaries (adm3 tehsils) | OCHA COD-AB on HDX | `admin_tehsils` |
| HydroRIVERS | hydrosheds.org | Reach centerlines |
| Copernicus GLO-30 DEM | AWS Open Data `s3://copernicus-dem-30m` | Slope, HAND, reach metrics |
| OSM Pakistan extract | download.geofabrik.de | Bridges, roads, power, settlements |
| Google Open Buildings | sites.research.google/open-buildings | Settlement no-go zones |
| ESA WorldCover 10 m | esa-worldcover.org | Vegetated bar validation |

---

## 3. Repository layout

```
suvastu/
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
├── Makefile
├── data/
│   ├── raw/            # downloaded S1/S2 products (gitignored)
│   └── cogs/           # processed COGs served by tiler (gitignored)
├── db/
│   └── init/
│       ├── 01_extensions.sql
│       └── 02_schema.sql
├── api/
│   ├── Dockerfile
│   ├── package.json
│   └── src/
│       ├── index.js
│       ├── db.js
│       └── routes/
│           ├── health.js
│           ├── reaches.js
│           ├── alerts.js
│           └── blocks.js
├── web/
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── main.jsx
│       ├── index.css
│       ├── App.jsx
│       └── components/MapView.jsx
└── worker/
    ├── Dockerfile
    ├── requirements.txt
    └── suvastu/
        ├── __init__.py
        ├── config.py
        ├── search_s1.py
        ├── fetch_raw.py
        └── hyp3_jobs.py
```

Create it:

```bash
mkdir -p suvastu/{data/{raw,cogs},db/init,api/src/routes,web/src/components,worker/suvastu}
cd suvastu
git init
printf "node_modules\n.env\ndata/raw\ndata/cogs\n__pycache__\ndist\n" > .gitignore
touch data/raw/.gitkeep data/cogs/.gitkeep
```

---

## 4. Environment

One `.env` at the repo root feeds every container through `env_file`. The full template is in `.env.example` (shipped alongside this document).

Rules:
- Only variables prefixed `VITE_` are exposed to the browser. Never prefix a secret with `VITE_`.
- `DATABASE_URL` must repeat the same user, password and database as the `POSTGRES_*` values.
- If your password contains `@ : / ? #`, URL-encode it inside `DATABASE_URL` (e.g. `@` → `%40`).
- Generate strong values with `openssl rand -base64 24`.

```bash
cp .env.example .env
```

Validate after filling:

```bash
docker compose config --quiet && echo "compose + env OK"
grep -E '^(EARTHDATA_|VITE_MAPBOX_TOKEN|POSTGRES_PASSWORD)' .env | grep -E '=$' && echo "^ still empty" || echo "required vars filled"
```

---

## 5. Docker Compose (development)

`docker-compose.yml`:

```yaml
name: suvastu

services:
  db:
    image: postgis/postgis:17-3.5
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    ports:
      - "${POSTGRES_PORT}:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./db/init:/docker-entrypoint-initdb.d:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 5s
      timeout: 3s
      retries: 20

  api:
    build:
      context: ./api
      target: dev
    restart: unless-stopped
    env_file: .env
    environment:
      PORT: ${API_PORT}
    ports:
      - "${API_PORT}:4000"
    volumes:
      - ./api:/app
      - /app/node_modules
    depends_on:
      db:
        condition: service_healthy

  web:
    build:
      context: ./web
      target: dev
    restart: unless-stopped
    env_file: .env
    ports:
      - "5173:5173"
    volumes:
      - ./web:/app
      - /app/node_modules
    depends_on:
      - api

  tiler:
    image: ghcr.io/developmentseed/titiler:latest
    restart: unless-stopped
    environment:
      PORT: 8000
      WORKERS_PER_CORE: 1
      CPL_VSIL_CURL_ALLOWED_EXTENSIONS: .tif,.TIF,.tiff
      GDAL_DISABLE_READDIR_ON_OPEN: EMPTY_DIR
    ports:
      - "8000:8000"
    volumes:
      - ./data/cogs:/data/cogs:ro

  worker:
    build: ./worker
    env_file: .env
    volumes:
      - ./worker:/app
      - ./data:/data
    depends_on:
      db:
        condition: service_healthy
    profiles: ["worker"]   # run on demand: docker compose run --rm worker ...

volumes:
  pgdata:
```

---

## 6. Database

`db/init/01_extensions.sql`:

```sql
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_raster;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

`db/init/02_schema.sql`:

```sql
-- Geometries stored in EPSG:4326; metric work in EPSG:32643 (UTM 43N) via ST_Transform.

CREATE TABLE admin_tehsils (
  id          serial PRIMARY KEY,
  district    text NOT NULL,
  tehsil      text NOT NULL,
  pcode       text UNIQUE,
  geom        geometry(MultiPolygon, 4326) NOT NULL
);
CREATE INDEX ON admin_tehsils USING gist (geom);

CREATE TABLE reaches (
  id          serial PRIMARY KEY,
  river       text NOT NULL,
  seq         int  NOT NULL,                -- order downstream
  tehsil_id   int REFERENCES admin_tehsils(id),
  length_m    numeric,
  slope       numeric,
  width_mean  numeric,
  centerline  geometry(LineString, 4326),
  geom        geometry(Polygon, 4326) NOT NULL  -- active channel corridor polygon
);
CREATE INDEX ON reaches USING gist (geom);

CREATE TABLE sar_scenes (
  id          serial PRIMARY KEY,
  granule     text UNIQUE NOT NULL,         -- S1 granule name
  platform    text NOT NULL,                -- S1A / S1C / NISAR
  orbit_rel   int,
  direction   text CHECK (direction IN ('ASCENDING','DESCENDING')),
  acq_time    timestamptz NOT NULL,
  rain_mm_72h numeric,                       -- GPM IMERG flag
  usable      boolean DEFAULT true,
  cog_path    text,                          -- /data/cogs/...
  footprint   geometry(Polygon, 4326)
);
CREATE INDEX ON sar_scenes (acq_time);
CREATE INDEX ON sar_scenes USING gist (footprint);

CREATE TABLE bar_obs (
  reach_id    int REFERENCES reaches(id) ON DELETE CASCADE,
  scene_id    int REFERENCES sar_scenes(id) ON DELETE CASCADE,
  water_m2    numeric,
  bar_m2      numeric,
  veg_bar_m2  numeric,
  PRIMARY KEY (reach_id, scene_id)
);

CREATE TABLE change_alerts (
  id          bigserial PRIMARY KEY,
  reach_id    int REFERENCES reaches(id),
  scene_pre   int REFERENCES sar_scenes(id),
  scene_post  int REFERENCES sar_scenes(id),
  db_change   numeric,                        -- backscatter change (dB)
  coh_loss    numeric,                        -- coherence drop 0..1
  confidence  numeric,
  status      text DEFAULT 'new' CHECK (status IN ('new','verified','false_positive','actioned')),
  verified_by text,
  notes       text,
  created_at  timestamptz DEFAULT now(),
  geom        geometry(Polygon, 4326) NOT NULL
);
CREATE INDEX ON change_alerts USING gist (geom);
CREATE INDEX ON change_alerts (status, created_at DESC);

CREATE TABLE nogo_zones (
  id          serial PRIMARY KEY,
  type        text NOT NULL,   -- bridge, intake, weir, eroding_bank, settlement, encroachment_zone
  source      text,            -- osm, digitized, irrigation_dept
  buffer_m    numeric,
  geom        geometry(MultiPolygon, 4326) NOT NULL
);
CREATE INDEX ON nogo_zones USING gist (geom);

CREATE TABLE blocks (
  id                 serial PRIMARY KEY,
  code               text UNIQUE,
  reach_ids          int[] NOT NULL,
  net_deposition_m2  numeric,
  vol_low_m3         numeric,
  vol_high_m3        numeric,
  reserve_pkr        numeric,
  status             text DEFAULT 'candidate' CHECK (status IN ('candidate','approved','auctioned','suspended')),
  geom               geometry(MultiPolygon, 4326) NOT NULL
);
CREATE INDEX ON blocks USING gist (geom);
```

Init scripts only run on an empty volume. To re-run: `docker compose down -v`.

---

## 7. API (Express)

`api/package.json`:

```json
{
  "name": "suvastu-api",
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "node --watch src/index.js",
    "start": "node src/index.js"
  },
  "dependencies": {
    "compression": "^1.8.0",
    "cors": "^2.8.5",
    "express": "^5.1.0",
    "helmet": "^8.1.0",
    "morgan": "^1.10.0",
    "pg": "^8.16.0"
  }
}
```

`api/Dockerfile`:

```dockerfile
FROM node:22-alpine AS base
WORKDIR /app
COPY package*.json ./

FROM base AS dev
RUN npm install
COPY . .
EXPOSE 4000
CMD ["npm", "run", "dev"]

FROM base AS prod
ENV NODE_ENV=production
RUN npm install --omit=dev
COPY . .
EXPOSE 4000
CMD ["npm", "start"]
```

`api/src/db.js`:

```js
import pg from 'pg';

export const pool = new pg.Pool({
  connectionString: process.env.DATABASE_URL,
  max: 10,
});

export const query = (text, params) => pool.query(text, params);

// Wrap a SELECT that returns (geom, ...props) into a FeatureCollection in SQL.
export const featureCollection = (innerSql) => `
  SELECT json_build_object(
    'type', 'FeatureCollection',
    'features', COALESCE(json_agg(ST_AsGeoJSON(t.*)::json), '[]'::json)
  ) AS fc
  FROM (${innerSql}) t
`;
```

`api/src/index.js`:

```js
import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import compression from 'compression';
import morgan from 'morgan';

import health from './routes/health.js';
import reaches from './routes/reaches.js';
import alerts from './routes/alerts.js';
import blocks from './routes/blocks.js';

const app = express();

app.use(helmet());
app.use(cors({ origin: process.env.CORS_ORIGIN?.split(',') ?? '*' }));
app.use(compression());
app.use(express.json({ limit: '2mb' }));
app.use(morgan('dev'));

app.use('/api/health', health);
app.use('/api/reaches', reaches);
app.use('/api/alerts', alerts);
app.use('/api/blocks', blocks);

app.use((err, req, res, _next) => {
  console.error(err);
  res.status(err.status || 500).json({ error: err.message || 'Internal error' });
});

const port = process.env.PORT || 4000;
app.listen(port, () => console.log(`api listening on :${port}`));
```

`api/src/routes/health.js`:

```js
import { Router } from 'express';
import { query } from '../db.js';

const r = Router();

r.get('/', async (_req, res) => {
  const { rows } = await query('SELECT postgis_full_version() AS v');
  res.json({ ok: true, postgis: rows[0].v });
});

export default r;
```

`api/src/routes/reaches.js`:

```js
import { Router } from 'express';
import { query, featureCollection } from '../db.js';

const r = Router();

// GET /api/reaches?tehsil=Babuzai
r.get('/', async (req, res) => {
  const { tehsil } = req.query;
  const sql = featureCollection(`
    SELECT r.id, r.river, r.seq, t.tehsil, r.length_m, r.width_mean, r.geom
    FROM reaches r
    LEFT JOIN admin_tehsils t ON t.id = r.tehsil_id
    WHERE ($1::text IS NULL OR t.tehsil = $1)
    ORDER BY r.river, r.seq
  `);
  const { rows } = await query(sql, [tehsil ?? null]);
  res.json(rows[0].fc);
});

// GET /api/reaches/:id/timeseries
r.get('/:id/timeseries', async (req, res) => {
  const { rows } = await query(
    `SELECT s.acq_time, s.direction, b.water_m2, b.bar_m2, b.veg_bar_m2
     FROM bar_obs b JOIN sar_scenes s ON s.id = b.scene_id
     WHERE b.reach_id = $1 AND s.usable
     ORDER BY s.acq_time`,
    [req.params.id]
  );
  res.json(rows);
});

export default r;
```

`api/src/routes/alerts.js`:

```js
import { Router } from 'express';
import { query, featureCollection } from '../db.js';

const r = Router();

// GET /api/alerts?since=2026-06-01&status=new
r.get('/', async (req, res) => {
  const { since, status } = req.query;
  const sql = featureCollection(`
    SELECT id, reach_id, db_change, coh_loss, confidence, status, created_at, geom
    FROM change_alerts
    WHERE ($1::timestamptz IS NULL OR created_at >= $1)
      AND ($2::text IS NULL OR status = $2)
    ORDER BY created_at DESC
    LIMIT 2000
  `);
  const { rows } = await query(sql, [since ?? null, status ?? null]);
  res.json(rows[0].fc);
});

// PATCH /api/alerts/:id  { status, verified_by, notes }
r.patch('/:id', async (req, res) => {
  const { status, verified_by, notes } = req.body;
  const { rows } = await query(
    `UPDATE change_alerts
     SET status = COALESCE($2, status),
         verified_by = COALESCE($3, verified_by),
         notes = COALESCE($4, notes)
     WHERE id = $1
     RETURNING id, status, verified_by, notes`,
    [req.params.id, status, verified_by, notes]
  );
  if (!rows.length) return res.status(404).json({ error: 'not found' });
  res.json(rows[0]);
});

export default r;
```

`api/src/routes/blocks.js`:

```js
import { Router } from 'express';
import { query, featureCollection } from '../db.js';

const r = Router();

r.get('/', async (_req, res) => {
  const sql = featureCollection(`
    SELECT b.id, b.code, b.status, b.net_deposition_m2,
           b.vol_low_m3, b.vol_high_m3, b.reserve_pkr,
           ROUND(ST_Area(ST_Transform(b.geom, 32643))::numeric) AS area_m2,
           EXISTS (
             SELECT 1 FROM nogo_zones n WHERE ST_Intersects(n.geom, b.geom)
           ) AS conflicts_nogo,
           b.geom
    FROM blocks b
  `);
  const { rows } = await query(sql);
  res.json(rows[0].fc);
});

export default r;
```

---

## 8. Web (React + Vite + Tailwind v4 + Mapbox GL JS)

Scaffold once (on host, or skip and create the files below by hand):

```bash
npm create vite@latest web -- --template react
cd web
npm install
npm install mapbox-gl
npm install -D tailwindcss @tailwindcss/vite
cd ..
```

`web/package.json` (resulting shape):

```json
{
  "name": "suvastu-web",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "mapbox-gl": "^3.13.0",
    "react": "^19.1.0",
    "react-dom": "^19.1.0"
  },
  "devDependencies": {
    "@tailwindcss/vite": "^4.1.0",
    "@vitejs/plugin-react": "^4.5.0",
    "tailwindcss": "^4.1.0",
    "vite": "^6.3.0"
  }
}
```

`web/vite.config.js`:

```js
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    watch: { usePolling: process.env.CHOKIDAR_USEPOLLING === 'true' },
    proxy: {
      '/api': { target: 'http://api:4000', changeOrigin: true },
    },
  },
});
```

`web/src/index.css`:

```css
@import "tailwindcss";
@import "mapbox-gl/dist/mapbox-gl.css";

@theme {
  --color-river: #1f6feb;
  --color-bar: #d4a259;
  --color-alert: #e5484d;
  --font-sans: "Inter", ui-sans-serif, system-ui, sans-serif;
}

html, body, #root { height: 100%; }
```

`web/src/main.jsx`:

```jsx
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import App from './App.jsx';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>
);
```

`web/src/App.jsx`:

```jsx
import { useEffect, useState } from 'react';
import MapView from './components/MapView.jsx';

const API = import.meta.env.VITE_API_URL ?? '/api';

export default function App() {
  const [health, setHealth] = useState(null);

  useEffect(() => {
    fetch(`${API}/health`).then((r) => r.json()).then(setHealth).catch(() => setHealth({ ok: false }));
  }, []);

  return (
    <div className="flex h-full">
      <aside className="w-80 shrink-0 border-r border-slate-200 bg-white p-4 overflow-y-auto">
        <h1 className="text-lg font-semibold text-slate-900">SUVASTU</h1>
        <p className="mt-1 text-sm text-slate-500">Reaches, SAR change alerts, extraction blocks</p>
        <div className="mt-4 rounded-lg bg-slate-50 p-3 text-xs">
          API: {health ? (health.ok ? <span className="text-green-600">connected</span> : <span className="text-alert">down</span>) : '...'}
        </div>
      </aside>
      <main className="relative flex-1">
        <MapView apiBase={API} />
      </main>
    </div>
  );
}
```

`web/src/components/MapView.jsx`:

```jsx
import { useEffect, useRef } from 'react';
import mapboxgl from 'mapbox-gl';

mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_TOKEN;

// Mapbox needs absolute URLs for GeoJSON sources.
const abs = (u) => new URL(u, window.location.origin).toString();

export default function MapView({ apiBase }) {
  const ref = useRef(null);

  useEffect(() => {
    const map = new mapboxgl.Map({
      container: ref.current,
      style: import.meta.env.VITE_MAPBOX_STYLE || 'mapbox://styles/mapbox/satellite-streets-v12',
      center: [72.36, 34.95],   // Mingora / Swat valley
      zoom: 9.5,
      pitch: 45,                 // 3D valley view
    });
    map.addControl(new mapboxgl.NavigationControl(), 'top-right');
    map.addControl(new mapboxgl.ScaleControl(), 'bottom-left');

    map.on('style.load', () => {
      map.addSource('dem', { type: 'raster-dem', url: 'mapbox://mapbox.mapbox-terrain-dem-v1', tileSize: 512 });
      map.setTerrain({ source: 'dem', exaggeration: 1.3 });
    });

    map.on('load', () => {
      map.addSource('reaches', { type: 'geojson', data: abs(`${apiBase}/reaches`) });
      map.addLayer({
        id: 'reaches-fill', type: 'fill', source: 'reaches',
        paint: { 'fill-color': '#1f6feb', 'fill-opacity': 0.25 },
      });

      map.addSource('alerts', { type: 'geojson', data: abs(`${apiBase}/alerts?status=new`) });
      map.addLayer({
        id: 'alerts-fill', type: 'fill', source: 'alerts',
        paint: { 'fill-color': '#e5484d', 'fill-opacity': 0.6 },
      });

      map.on('click', 'alerts-fill', (e) => {
        const p = e.features[0].properties;
        new mapboxgl.Popup()
          .setLngLat(e.lngLat)
          .setHTML(`<b>Alert ${p.id}</b><br/>Δ ${Number(p.db_change).toFixed(2)} dB<br/>coh loss ${Number(p.coh_loss).toFixed(2)}`)
          .addTo(map);
      });
    });

    return () => map.remove();
  }, [apiBase]);

  return <div ref={ref} className="absolute inset-0" />;
}
```

To show a COG from the tiler later:

```js
map.addSource('s1-vh', {
  type: 'raster',
  tiles: [`${new URL(import.meta.env.VITE_TILER_URL, window.location.origin)}/cog/tiles/WebMercatorQuad/{z}/{x}/{y}.png?url=/data/cogs/s1_vh_20260715.tif&rescale=-25,0`],
  tileSize: 256,
});
map.addLayer({ id: 's1-vh', type: 'raster', source: 's1-vh' });
```

`web/Dockerfile`:

```dockerfile
FROM node:22-alpine AS base
WORKDIR /app
COPY package*.json ./

FROM base AS dev
RUN npm install
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev"]

FROM base AS build
RUN npm install
COPY . .
ARG VITE_API_URL=/api
ARG VITE_TILER_URL=/tiles
ARG VITE_MAPBOX_TOKEN
ARG VITE_MAPBOX_STYLE=mapbox://styles/mapbox/satellite-streets-v12
ENV VITE_API_URL=$VITE_API_URL VITE_TILER_URL=$VITE_TILER_URL \
    VITE_MAPBOX_TOKEN=$VITE_MAPBOX_TOKEN VITE_MAPBOX_STYLE=$VITE_MAPBOX_STYLE
RUN npm run build

FROM nginx:1.27-alpine AS prod
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
```

`web/nginx.conf` (production):

```nginx
server {
  listen 80;
  root /usr/share/nginx/html;
  client_max_body_size 20m;

  location /api/ {
    proxy_pass http://api:4000;
    proxy_set_header Host $host;
  }

  location /tiles/ {
    proxy_pass http://tiler:8000/;
  }

  location / {
    try_files $uri /index.html;
  }
}
```

---

## 9. Worker (Python SAR pipeline)

`worker/requirements.txt`:

```text
asf_search>=8.0
hyp3_sdk>=7.0
rasterio>=1.4
rio-cogeo>=5.4
numpy>=2.0
scipy>=1.14
geopandas>=1.0
shapely>=2.0
pyproj>=3.7
psycopg[binary]>=3.2
sqlalchemy>=2.0
geoalchemy2>=0.15
python-dotenv>=1.0
click>=8.1
```

`worker/Dockerfile`:

```dockerfile
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends gdal-bin && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENTRYPOINT ["python", "-m"]
CMD ["suvastu.search_s1", "--help"]
```

`worker/suvastu/__init__.py`: empty file.

`worker/suvastu/config.py`:

```python
import os

DB_URL = os.environ["DATABASE_URL"].replace("postgres://", "postgresql+psycopg://", 1)
AOI_BBOX = [float(v) for v in os.environ.get("AOI_BBOX", "72.05,34.60,72.95,35.75").split(",")]
AOI_WKT = (
    f"POLYGON(({AOI_BBOX[0]} {AOI_BBOX[1]},{AOI_BBOX[2]} {AOI_BBOX[1]},"
    f"{AOI_BBOX[2]} {AOI_BBOX[3]},{AOI_BBOX[0]} {AOI_BBOX[3]},{AOI_BBOX[0]} {AOI_BBOX[1]}))"
)
EARTHDATA_USERNAME = os.environ.get("EARTHDATA_USERNAME")
EARTHDATA_PASSWORD = os.environ.get("EARTHDATA_PASSWORD")
EARTHDATA_TOKEN = os.environ.get("EARTHDATA_TOKEN")
CDSE_USERNAME = os.environ.get("CDSE_USERNAME")
CDSE_PASSWORD = os.environ.get("CDSE_PASSWORD")
DATA_DIR = os.environ.get("DATA_DIR", "/data")
```

`worker/suvastu/search_s1.py` (search Sentinel-1 over Swat and register scenes):

```python
import click
import asf_search as asf
from shapely.geometry import shape
from sqlalchemy import create_engine, text

from .config import AOI_WKT, DB_URL


@click.command()
@click.option("--start", default="2019-03-01", help="YYYY-MM-DD")
@click.option("--end", default="2026-11-30", help="YYYY-MM-DD")
@click.option("--level", default="SLC", type=click.Choice(["SLC", "GRD_HD"]))
def main(start, end, level):
    results = asf.search(
        platform=asf.PLATFORM.SENTINEL1,
        processingLevel=level,
        beamMode="IW",
        intersectsWith=AOI_WKT,
        start=start,
        end=end,
    )
    click.echo(f"found {len(results)} granules")

    eng = create_engine(DB_URL)
    sql = text("""
        INSERT INTO sar_scenes (granule, platform, orbit_rel, direction, acq_time, footprint)
        VALUES (:g, :p, :o, :d, :t, ST_GeomFromText(:fp, 4326))
        ON CONFLICT (granule) DO NOTHING
    """)
    with eng.begin() as con:
        for r in results:
            p = r.properties
            geom = r.geometry
            fp = shape(geom).wkt
            con.execute(sql, {
                "g": p["sceneName"],
                "p": p["platform"],
                "o": p.get("pathNumber"),
                "d": p.get("flightDirection"),
                "t": p["startTime"],
                "fp": fp,
            })
    click.echo("registered in sar_scenes")


if __name__ == "__main__":
    main()
```

`worker/suvastu/fetch_raw.py` (direct granule download with the Earthdata token, e.g. ALOS PALSAR 2010 or S1 GRD):

```python
import click
import asf_search as asf

from .config import EARTHDATA_TOKEN, DATA_DIR


@click.command()
@click.argument("granules", nargs=-1, required=True)
def main(granules):
    session = asf.ASFSession().auth_with_token(EARTHDATA_TOKEN)
    results = asf.granule_search(list(granules))
    results.download(path=f"{DATA_DIR}/raw", session=session, processes=4)
    click.echo(f"downloaded {len(results)} files to {DATA_DIR}/raw")


if __name__ == "__main__":
    main()
```

`worker/suvastu/hyp3_jobs.py` (submit RTC and InSAR jobs to ASF HyP3, download to `/data/raw`):

```python
import click
import hyp3_sdk as sdk

from .config import EARTHDATA_USERNAME, EARTHDATA_PASSWORD, DATA_DIR


def client():
    return sdk.HyP3(username=EARTHDATA_USERNAME, password=EARTHDATA_PASSWORD)


@click.group()
def cli():
    pass


@cli.command()
@click.argument("granules", nargs=-1, required=True)
@click.option("--name", default="suvastu-rtc")
def rtc(granules, name):
    """Radiometric terrain correction (gamma0, dB, 10 m) with layover/shadow mask."""
    h = client()
    jobs = sdk.Batch()
    for g in granules:
        jobs += h.submit_rtc_job(
            g, name=name, resolution=10, scale="decibel",
            include_ls_map=True, include_dem=False, dem_matching=True,
        )
    click.echo(f"submitted {len(jobs)} RTC jobs")


@cli.command()
@click.argument("reference")
@click.argument("secondary")
@click.option("--name", default="suvastu-insar")
def insar(reference, secondary, name):
    """Interferogram pair; coherence used for change detection on gravel bars."""
    h = client()
    job = h.submit_insar_job(reference, secondary, name=name, looks="10x2", include_inc_map=True)
    click.echo(f"submitted {job.job_id}")


@cli.command()
def credits():
    """Verify Earthdata login against HyP3 and show remaining processing credits."""
    h = client()
    click.echo(f"HyP3 login OK, credits remaining: {h.check_credits()}")


@cli.command()
@click.option("--name", required=True)
def download(name):
    h = client()
    batch = h.find_jobs(name=name)
    batch = h.watch(batch)
    batch.download_files(f"{DATA_DIR}/raw")
    click.echo(f"downloaded {len(batch)} products to {DATA_DIR}/raw")


if __name__ == "__main__":
    cli()
```

---

## 10. Makefile

```makefile
include .env
export

.PHONY: up down reset logs psql ps creds s1-search worker-shell build-prod

up:
	docker compose up -d --build

down:
	docker compose down

reset:            ## wipe DB volume and re-run init SQL
	docker compose down -v && docker compose up -d --build

logs:
	docker compose logs -f api web

ps:
	docker compose ps

psql:
	docker compose exec db psql -U $$POSTGRES_USER -d $$POSTGRES_DB

creds:            ## verify Earthdata + HyP3 credentials
	docker compose run --rm worker suvastu.hyp3_jobs credits

s1-search:
	docker compose run --rm worker suvastu.search_s1 --start 2022-03-01 --end 2026-11-30 --level SLC

worker-shell:
	docker compose run --rm --entrypoint bash worker

build-prod:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

---

## 11. Production override

`docker-compose.prod.yml`:

```yaml
services:
  db:
    ports: !reset []          # do not expose Postgres publicly

  api:
    build:
      context: ./api
      target: prod
    volumes: !reset []
    ports: !reset []

  web:
    build:
      context: ./web
      target: prod
      args:
        VITE_MAPBOX_TOKEN: ${VITE_MAPBOX_TOKEN}
        VITE_MAPBOX_STYLE: ${VITE_MAPBOX_STYLE}
    volumes: !reset []
    ports: !reset ["80:80"]

  tiler:
    ports: !reset []
```

`!reset` needs Docker Compose 2.24 or newer (`docker compose version`). Without it, ports from the base file are merged, not replaced.

---

## 12. First run

```bash
cp .env.example .env              # then fill every value marked REQUIRED
docker compose config --quiet     # env + compose syntax check
make up
make creds                        # Earthdata/HyP3 login check + credits
curl localhost:4000/api/health    # {"ok":true,"postgis":"POSTGIS=..."}
open http://localhost:5173        # Mapbox 3D map centered on Swat
make s1-search                    # registers Sentinel-1 SLC granules over AOI
make psql                         # SELECT direction, count(*) FROM sar_scenes GROUP BY 1;
```

Load tehsil boundaries (OCHA COD-AB from HDX) into `admin_tehsils`:

```bash
docker compose run --rm --entrypoint bash worker -c \
  "ogr2ogr -f PostgreSQL PG:\"host=db dbname=\$POSTGRES_DB user=\$POSTGRES_USER password=\$POSTGRES_PASSWORD\" \
   /data/raw/pak_admbnda_adm3.shp -nln stg_adm3 -nlt PROMOTE_TO_MULTI -t_srs EPSG:4326 -overwrite"
```

```sql
INSERT INTO admin_tehsils (district, tehsil, pcode, geom)
SELECT adm2_en, adm3_en, adm3_pcode, wkb_geometry
FROM stg_adm3
WHERE adm2_en ILIKE '%Swat%';
```

Check the column names in the shapefile with `ogrinfo -so` first; they differ between COD-AB releases.

---

## 13. Build order (6 weeks)

| Week | Task | Touches |
|---|---|---|
| 1 | Compose up, tehsils loaded, reach segmentation (500 m) from HydroRIVERS + GLO-30 | db, worker |
| 1 | S1 search, RTC jobs (asc + desc), GPM rain flag on `sar_scenes.usable` | worker |
| 2 | Water / bar / vegetated-bar classification per scene → `bar_obs`, COGs → tiler | worker, tiler |
| 3 | Backscatter min-feature + coherence change → `change_alerts`; validate on Fizagat and Khwazakhela | worker |
| 4 | `nogo_zones` (OSM bridges, intakes, settlements), block recommender → `blocks` | worker, db |
| 5 | UI: reach explorer with time-series chart, alert feed with verify/false-positive, block sheets | web, api |
| 6 | Statistics report, PDF block sheet endpoint, demo deployment | api, web |

---

## 14. Notes

- **Layover and shadow:** always request `include_ls_map=True` and mask those pixels before classification. Use both orbit directions in the narrow valley.
- **Rain contamination:** flag scenes with heavy 72-hour rainfall from GPM IMERG and exclude them from alert generation.
- **Volumes:** SAR gives area change, not depth. Report `vol_low_m3`/`vol_high_m3` as ranges from an assumed thickness band until drone/GNSS validation.
- **COG naming:** `s1_{pol}_{yyyymmdd}_{dir}.tif`, `cls_{yyyymmdd}.tif`, `coh_{pre}_{post}.tif` under `data/cogs/`.
