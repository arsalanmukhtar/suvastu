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
