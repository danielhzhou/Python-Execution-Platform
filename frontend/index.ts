/**
 * Main Bun server for Python Execution Platform Frontend
 */
import index from "./index.html";

const server = Bun.serve({
  port: 3000,
  routes: {
    "/": index,
    "/api/*": {
      // Proxy API requests to backend
      GET: (req) => {
        const url = new URL(req.url);
        const backendUrl = `http://localhost:8000${url.pathname}${url.search}`;
        return fetch(backendUrl, {
          method: req.method,
          headers: req.headers,
          body: req.body,
        });
      },
      POST: (req) => {
        const url = new URL(req.url);
        const backendUrl = `http://localhost:8000${url.pathname}${url.search}`;
        return fetch(backendUrl, {
          method: req.method,
          headers: req.headers,
          body: req.body,
        });
      },
    },
  },
  websocket: {
    open: () => {
      console.log("WebSocket connection opened");
    },
    message: (_, message) => {
      // Forward WebSocket messages to backend
      console.log("WebSocket message:", message);
    },
    close: () => {
      console.log("WebSocket connection closed");
    },
  },
  development: {
    hmr: true,
    console: true,
  },
});

console.log(`🚀 Frontend server running at http://localhost:${server.port}`);
console.log(`📝 Environment: ${process.env.NODE_ENV || 'development'}`);    