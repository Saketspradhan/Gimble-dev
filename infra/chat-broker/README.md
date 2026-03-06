# Gimble Chat Broker (Cloudflare Worker)

This worker enables public URLs in the form:

`https://chat.gimble.dev/<username>/<session_id>`

It stores temporary session -> tunnel mappings in a Durable Object (strong consistency, low-latency reads). KV is kept as a fallback binding only.

## Setup

1. Put `gimble.dev` under Cloudflare DNS (nameservers at GoDaddy -> Cloudflare).
2. Keep your existing Vercel records for apex/`www` unchanged in Cloudflare DNS.
3. Create DNS record `chat.gimble.dev` (proxied orange cloud).
4. Configure Worker bindings:
   - Durable Object binding: `SESSION_BROKER` (class `SessionBroker`)
   - KV binding: `SESSIONS` (fallback only)
5. Deploy worker on route `chat.gimble.dev/*`.
6. No client secret needed; worker verifies ownership via `/__gimble_proof` nonce checks.

## Local CLI env vars

Set on developer machine (or let Gimble auto-populate defaults):

- `GIMBLE_CHAT_PUBLIC_BASE=https://chat.gimble.dev`
- `GIMBLE_CHAT_BROKER_ENDPOINT=https://chat.gimble.dev/api/register`

Optional (recommended for faster startup):

- `GIMBLE_NAMED_TUNNEL_URL=https://<your-stable-tunnel-hostname>`

When `GIMBLE_NAMED_TUNNEL_URL` is set, Gimble skips creating a new quick tunnel each run and registers the stable tunnel URL directly, which reduces warm-up delay.

Then running `gim chat` will register the session and print a link like:

`https://chat.gimble.dev/<username>/<session_id>`
