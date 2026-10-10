Implement isolated rendering for untrusted public GitHub slide decks.

Goal: allow any author to use custom CSS, including <style> blocks and
inline positioning, without allowing deck content to modify or access
the platform UI, authentication or privileged APIs.

First inspect the current presenter, follower, preview and export
rendering paths. Propose the renderer-origin and deployment boundary
before implementing changes that require infrastructure decisions.

Move Reveal.js and deck rendering into a sandboxed iframe on a dedicated
origin with no platform authentication cookies or credentials. Keep
login, presenter controls, audience tools, authenticated requests and
session authority in the parent application.

Allow deck CSS only inside the isolated renderer. Retain HTML and URL
sanitization; reject deck-authored scripts, event handlers, forms,
plugins and nested iframes initially. Keep renderer JavaScript under
platform control. Do not globally set trustedStyles: true in the
existing parent-page renderer.

Implement restrictive sandbox permissions and a renderer-specific CSP.
Define an explicit external image/font/media policy and document its
privacy implications. Do not introduce an unrestricted asset proxy.

Build a narrowly scoped, schema-validated postMessage bridge for
readiness, errors, navigation, fragments and slide-state synchronization.
Validate sender identity appropriately for the chosen sandbox/origin
model. Never transmit credentials or accept arbitrary privileged
commands. Keep presenter authorization in the parent.

Preserve existing layout, scaling, animations, notes, interactions and
live synchronization. Investigate and cover presenter, follower,
preview and export surfaces.

Add regression tests for CSS isolation, blocked deck script execution,
sandbox navigation restrictions, forged bridge messages, remote asset
policy and existing presentation behavior. Use the
TheHumanHack/2026/261023-south-coast deck as a layout regression fixture.

Document deployment requirements, remaining risks and supported deck
features. Run focused tests and the relevant build/type-check.