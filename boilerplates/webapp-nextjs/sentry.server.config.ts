/**
 * GlitchTip (Sentry-compatible) server-side SDK initialisation.
 *
 * This file is automatically loaded by @sentry/nextjs on the server side
 * (Node.js runtime). Server-side error tracking always captures errors without
 * consent considerations since no end-user PII is involved by default.
 */

import * as Sentry from "@sentry/nextjs";

const GLITCHTIP_DSN = process.env.NEXT_PUBLIC_GLITCHTIP_DSN;

if (GLITCHTIP_DSN) {
  Sentry.init({
    dsn: GLITCHTIP_DSN,
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
