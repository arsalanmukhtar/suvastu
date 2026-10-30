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
