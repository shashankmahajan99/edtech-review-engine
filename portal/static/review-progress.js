/* Polling observes the review POST; stopping it never cancels document work. */
(() => {
  'use strict';
  function start({id, onUpdate, onUnavailable, fetch: request = globalThis.fetch.bind(globalThis), intervalMs = 1000, timeoutMs = 5000}) {
    let active = true;
    let nextTimer;
    let timeoutTimer;
    let controller;
    function stop() {
      active = false;
      clearTimeout(nextTimer);
      clearTimeout(timeoutTimer);
      controller?.abort();
    }
    async function poll() {
      if (!active) return;
      controller = new AbortController();
      timeoutTimer = setTimeout(() => controller.abort(), timeoutMs);
      try {
        const response = await request(`/api/thinkingstorm/progress/${encodeURIComponent(id)}`, {
          cache: 'no-store', credentials: 'same-origin', signal: controller.signal
        });
        if (!active) return;
        if (response.status === 404) return; // Multipart upload has not reached the handler yet.
        if (!response.ok) throw new Error('Progress is unavailable.');
        const data = await response.json();
        if (!active) return;
        onUpdate(data);
        if (data.status === 'complete' || data.status === 'failed') stop();
      } catch {
        if (active) onUnavailable();
      } finally {
        clearTimeout(timeoutTimer);
        if (active) nextTimer = setTimeout(poll, intervalMs);
      }
    }
    poll();
    return {stop};
  }
  globalThis.ReviewProgress = {start};
})();
