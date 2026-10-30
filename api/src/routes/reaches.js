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
