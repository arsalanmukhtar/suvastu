import { Router } from 'express';
import { query } from '../db.js';

const r = Router();

r.get('/', async (_req, res) => {
  const { rows } = await query('SELECT postgis_full_version() AS v');
  res.json({ ok: true, postgis: rows[0].v });
});

export default r;
