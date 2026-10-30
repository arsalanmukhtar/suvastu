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
