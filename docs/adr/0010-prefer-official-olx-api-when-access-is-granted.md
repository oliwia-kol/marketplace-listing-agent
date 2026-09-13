# ADR 0010: prefer the official OLX API when access is granted

Status: accepted as the target direction, 2026-09-13. Implementation is blocked on
application registration and approval.

OLX currently documents a Partner API that can create and manage adverts. Access
requires signing in to the Developer Portal, registering an application and passing
OLX verification. The current browser adapter remains useful for a controlled local
prototype, but an approved API integration would provide explicit schemas, OAuth
scopes, stable identifiers and a stronger reconciliation path than DOM automation.

The approval model does not change: the API adapter must accept only a `job_id`, reload
the immutable snapshot, validate a separate publication approval and store tokens only
in an operating-system secret store. It must first create a draft where the API permits
that workflow and activate it only after the final approval. No API token may pass
through Telegram, a model prompt, MCP arguments, logs or the repository.

Allegro Lokalnie remains browser-based because its official help explicitly states that
Allegro Lokalnie adverts cannot be published through the Allegro API. The Allegro REST
API applies to the main Allegro marketplace, which is a different product scope.

Sources:

- https://developer.olx.pl/pl
- https://developer.olx.pl/articles/getting-access-to-api
- https://developer.olx.pl/swagger/v2/partner_api.yaml
- https://allegro.pl/pomoc/dla-kupujacych/sprzedaz-na-allegro-lokalnie/jak-wystawic-ogloszenie-na-allegro-lokalnie-XEB1GldM8HR
