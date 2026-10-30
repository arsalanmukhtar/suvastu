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
