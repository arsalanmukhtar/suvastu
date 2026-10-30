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
