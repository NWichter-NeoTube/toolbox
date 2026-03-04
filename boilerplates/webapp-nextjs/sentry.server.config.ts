/**
 * Sentry server-side SDK initialisation.
 *
 * This file is automatically loaded by @sentry/nextjs on the server side
 * (Node.js runtime). Server-side Sentry always captures errors without
 * consent considerations since no end-user PII is involved by default.
 */

import * as Sentry from "@sentry/nextjs";

const SENTRY_DSN = process.env.NEXT_PUBLIC_SENTRY_DSN;

if (SENTRY_DSN) {
  Sentry.init({
    dsn: SENTRY_DSN,
    environment: process.env.NODE_ENV,

    // Performance monitoring -- sample 20% of transactions.
    tracesSampleRate: 0.2,

    // Do not send PII on the server by default.
    sendDefaultPii: false,

    beforeSend(event) {
      // Strip IP addresses and request headers on the server.
      if (event.request) {
        delete event.request.headers;
        delete event.request.env;
      }
      return event;
    },
  });
}
