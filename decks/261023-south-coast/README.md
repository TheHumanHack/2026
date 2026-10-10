# Human Hack ? South Coast User Group, 23 October 2026

The working deck is `slides.md`, converted from `Human Hack - South Coast 2026.pptx`.
It uses the same Reveal.js loading, authentication, presenter, follower, speaker,
remote and notes views as `../260925-little-code/`.

All **24 slides** remain in their original order, including the sponsor slide,
three contributor profiles, fireplace video and final brand reference. Original
wording, the source speaker note, QR imagery and media are preserved. The
PowerPoint remains unchanged. South Coast artwork and its mint, blue, navy and
white palette are retained.

Text is editable HTML inside Markdown; vector shapes are inline SVG. Source
coordinates are scaled to the app's 1280 ? 720 canvas and fitted into speaker
previews. Original images and the MP4 are extracted byte-for-byte into
`public/slides/261023-south-coast/`. `source-assets.json` records the source hash,
slide text, notes, media hashes and font provenance.

## Session access

The session is **11:00?11:45 BST, 23 October 2026** (Europe/London, UTC+01:00).

- `availableFrom`: `2026-10-23T10:00:00Z`.
- `selfExploreFrom`: `2026-10-23T10:45:00Z`.

These metadata fields control access, rather than automatic slide advancement.
Use the existing presenter password to preview before the event.

With `npm run dev` running:

- Presenter: <http://localhost:5173/deck/261023-south-coast/presenter>.
- Follower: <http://localhost:5173/deck/261023-south-coast/follower>.
- Speaker notes/previews: <http://localhost:5173/deck/261023-south-coast/speaker>.
- Remote: <http://localhost:5173/deck/261023-south-coast/remote>.

## Presenting and editing

Right Arrow moves between topics; Down Arrow explores the current topic's
vertical branch. Space advances through slides and explicit fragments;
Escape opens the overview. The fireplace on source slide 6 autoplays muted,
loops, and keeps its original playback speed; on-slide video controls remain
available. Explicit `autoFragment: false` keeps navigation free of notes-driven
fragment steps.

### Shared event header

Slides share the same top-right event header: South Coast User Group,
23rd October 2026 and the original Meetup symbol (`image38.png`). The title
(`#/0`), fireplace (`#/6`) and topic hub (`#/7`) omit this header. The added
Community slide (`#/2`) uses it together with a mint heading, a framed photo
area and the original compact branded footer. Its photo-folder marker remains
intact. `EVENT_HEADER`, `EVENT_HEADER_EXCLUDED_SOURCE_SLIDES` and
`community_slide()` in `convert-source.py` preserve these choices on conversion.

The Community slide adds one horizontal position before the contributor slides;
topic links and deeper branches account for that position. All 24 original
source slides remain, for 25 slides in total.

### Fireside topic hub

The discussion hub is at `#/7` (source slide 7), immediately after the fireplace
at `#/6` (source slide 6). It uses the same muted, looping fire video, with a dark
overlay for contrast. All ten topic titles are hyperlinks containing miniature
copies of their target slides, not static screenshots. Hover or keyboard focus
lifts a window; selecting it uses Reveal Auto-Animate to expand the thumbnail
into the target slide over 0.8 seconds. **Back to topics** shrinks the discussion
back into its window, including returns from the deeper branches. Reduced-motion users
get immediate navigation without the zoom or hover movement. The ten windows
fly in with staggered perspective motion each time the hub is entered.

Following slides include **Back to topics**, and normal arrow-key navigation
still works. Presenter jumps use the existing live slide synchronization;
followers cannot use topic links to bypass their live-session navigation limits.
Speaker previews also display the thumbnail hub.

`data-slide-hub-animate` opts this hub into native animation. The portal enhancer
matches the complete slide canvas to its thumbnail once, avoiding double scaling
of nested text and images. Direct Reveal slide updates use the same animation,
while the existing contributor and deeper-branch matching stays intact.

The source converter preserves this hub when regenerating the deck. Edit its
`TOPIC_HUB` markup and hub CSS in `convert-source.py` as well as `slides.md` when
changing the topic labels or destinations.

Run `node --test tests/southCoastHub.test.mjs` from the repository root to verify
the slide count, fireplace background settings and all ten topic destinations.

All slides share a 0.8-second Auto-Animate group except source slide 6 (`#/6`),
which keeps its fade transition when entering and leaving the fireplace video.
The hub retains its thumbnail zoom, and contributor and branch matches remain intact.

### Topic layout and deeper branches

The sponsor, Community, contributor, hub, topic and branch slides use a 52px
footer across the full slide. The original blue
background artwork is retained, with South Coast User Group on the left, Meetup
centred and Microsoft on the right. Each original logo is scaled proportionally.
**Back to topics** sits between Meetup and Microsoft; **Explore deeper** sits
between South Coast User Group and Meetup. Reveal's arrows sit above this strip.
Closing thoughts (`#/17`) uses the same 52px footer as the preceding slide.
Questions & discussion (`#/18`) also uses this shared 52px footer.
Topic subjects stay fitted into the expanded content area without stretching images.

The deck retains all 24 source slides, now arranged into 20 horizontal positions:

| Topic | Entry | Downward slides |
| --- | --- | --- |
| Consulting mindset | `#/10` (source 10) | `#/10/1` through `#/10/4` (source 11-14) |
| Elastic Leadership | `#/11` (source 15, previously `#/14`) | `#/11/1` (source 16) |
| Closing thoughts | `#/17` (source 22, previously `#/21`) | Three section fragments |

Use Down Arrow or **Explore deeper** within the two branches; Up Arrow returns
to the previous level. Right Arrow skips to the next topic. All branch slides use
Reveal Auto-Animate, with stable IDs for decision-map labels/dots and leadership
stages. New content fades in while matched elements morph and move.

The Consulting mindset section (`#/10` through `#/10/4`) shares 32px mint titles,
aligned 18px subtitles and bottom captions, and 20px role labels: blue Mercenary
and teal Missionary. Role descriptions use 16px text. Font sizes account for
each diagram's scale, and ownership-map descriptions sit below the axis.
These deck-local styles and semantic classes are retained by the converter.
The section's main content, subtitles and bottom captions were moved 30px lower
to leave more room below the titles. The ownership charts at `#/10/3` and `#/10/4`
now use the space freed by moving their explanations into notes: their vertical
layout is 35% taller, without stretching text or dots. **Minimum compliance**
sits below the vertical axis with a clear gap. The opening comparison also has more line
spacing and uses a blue/teal balance illustration; its original image remains
intact. See [illustration edit details](consulting-balance-image.md) for the
saved asset and prompt.

The Elastic Leadership branch (`#/11` and `#/11/1`) moves its explanatory
captions into speaker notes. Both diagrams use taller layouts and larger text;
the source citation stays below the graphic. The converter preserves these edits.

### Animated SVG topic visuals

The eight slides at `#/10` through `#/10/4`, `#/11`, `#/11/1` and `#/14`
now use editable SVG assets in `public/slides/261023-south-coast/`, inlined by
the source converter. They share mint titles, blue/teal accents, navy labels
and soft rounded panels:

- `consulting-mindsets.svg`: the original two sets of six points around a vector balance.
- `decisions-context-1.svg` and `decisions-context-2.svg`: eleven decision dots shift along the same reward/purpose spectrum.
- `ownership-map-1.svg` and `ownership-map-2.svg`: four shaded quadrants and the original decision examples.
- `elastic-leadership.svg` and `leadership-stages.svg`: three connected leadership stages followed by two practical transition panels.
- `passion-requirement.svg`: the original four numbered quadrants, with the same need/want wording.

These visuals supersede the earlier diagram layouts and balance bitmap described
above; original media files remain available. Wording, notes, slide positions,
footer branding and navigation are preserved. Cards and dots arrive in a
staggered sequence and connecting lines draw into place without extra clicks.
Shared objects use Reveal Auto-Animate between branch slides. Entrance effects
are disabled on matched objects before Reveal measures them, keeping final
positions and opacity correct. Overview and hub copies show complete diagrams;
reduced-motion users see the complete content immediately.

Edit the SVGs and `topic-graphics.css`, then rerun `convert-source.py` to update
the inline slide markup and styles. Browser validation used the installed Reveal
Markdown/Highlight plugins, white theme, bundled font and the app's 1280 × 720
canvas, checking text fit, shared-object transitions and reduced motion.

Closing thoughts reveals **Consulting mindset**, **Client value**, then
**Delivery habits** on successive advances using native Reveal fragments, so
presenter/follower and speaker synchronization retain the same fragment state.
The hub thumbnail always shows all three sections. Reduced motion disables
fly-ins, typing animation and Auto-Animate for this deck, while keeping
the same click/keyboard reveal sequence.

[Krona One](https://github.com/google/fonts/tree/main/ofl/kronaone) is bundled
locally with its [SIL Open Font License](../../public/slides/261023-south-coast/fonts/OFL.txt).
No external font request is needed during the talk. Browser font metrics require
small layout adjustments to the sponsor date/header. Text remains selectable;
slide images have descriptive alt text. Speaker previews preserve the 16:9 canvas.

Edit the generated HTML or slide attributes in `slides.md`, keeping a blank line
on both sides of each `---` (horizontal) or `--` (vertical). The brand reference
remains source slide 24, as in the source.

To rebuild from the PowerPoint, run:

```powershell
python decks/261023-south-coast/convert-source.py
```

The converter needs Python 3 and its standard library only. Regeneration
**overwrites manual edits to `slides.md` and `source-assets.json`**. It leaves
`meta.json` and the PowerPoint untouched. Bundled fonts and their licence must
remain in the public asset folder.

## Validation

- The installed Reveal Markdown plugin and actual app render 24 slides.
- Source wording is preserved, including the colour palette table;
  original PPTX/media hashes match, and all separators have surrounding blank lines.
- Headless Edge checked every slide through the built app at 1600 ? 900: no application script
  errors, failed asset requests, broken images or material text overflow.
- Verified Krona One loads, the fireplace plays muted at 1? with looping enabled,
  and both speaker previews fit the full slide.
- Verified a live slide update reaches the browser follower view.
- `npm run build` passed with the existing Vite deprecation and bundle-size warnings.
- Topic-hub regression tests cover the 19-horizontal/24-leaf topology, ten
  destinations, two Auto-Animate branches and three closing fragments.
- Browser checks verify every hub jump/return, native Down/Right branch behavior,
  staggered fly-in delays, reduced-motion styling and collision-free footer
  controls on all 15 topic slides.

Other decks are unchanged. Shared portal enhancements resolve source slide IDs
to horizontal/vertical coordinates and preserve the existing follower limits.

### Fast typing on Closing thoughts

At `#/16`, each of the three existing section reveals types its heading and
body in order at 6ms per character (about a second per section). The heading
finishes before the body starts, regardless of the original PowerPoint shape order. The full text
stays in place while characters appear, so line wrapping and column positions
remain stable. Previous reveals remain visible, and hiding then revealing a
section replays the typing. Reduced motion shows the complete text immediately;
topic thumbnails always show the full wording. The source converter preserves
the effect on regeneration.

Verified in headless Edge: progressive typing on all three reveals, replay after
hiding a section, stable line positions, unchanged text, immediate reduced-motion
reveals and full-text thumbnails. All five existing South Coast deck checks pass.

### Contributor profiles

Contributor slides 3?5 (`#/2`, `#/3`, `#/4`) share a new portrait panel, prominent
name/role, Focus and Awards cards, and the compact South Coast footer. The
original biography copy, focus areas, awards, company/award artwork and every
connection QR remain. Areti's cards use the extra room where the source has no
biography; no biography was invented.

The three original portraits have stable per-person Auto-Animate IDs. As you
advance, the next portrait expands from the small roster into the featured
panel, and the previous portrait shrinks back into the roster. A mint position
indicator moves along with the active contributor, and the cards move to fit
each profile. The 0.8-second animation applies across the deck except slide 6 and
respects the deck's reduced-motion rules. No extra clicks or application code
are required. Regeneration retains these layouts via `contributor_content`.

Validated all three layouts in headless Edge at the host's 1280 ? 720 canvas:
all portraits match for Auto-Animate, all assets load, no profile text overflows,
and speaker preview scaling and reduced motion work. All five existing deck
checks pass. Original contributor wording and media URLs were compared against
the pre-redesign slides.

### Rapport pyramid

Rapport (`#/8`, source slide 9) uses an editable inline SVG in the deck's blue,
mint and navy palette, with dimensional tiers and readable labels. All six
original levels and the Trust arrow remain. The foundation arrives first,
followed by each higher tier; the Trust arrow draws upward to finish the
entrance in about 1.7 seconds. Re-entering the slide replays it automatically,
without extra clicks. Hub thumbnails and the overview show the complete diagram;
reduced motion displays it immediately.

Edit `public/slides/261023-south-coast/rapport-pyramid.svg` and regenerate to
update the diagram. `topic_content` in the converter embeds it, and `STYLE`
owns its slide-entry animation. The original `image46.jpeg` remains intact.

### Animated topic graphics

The five topic positions `#/7`, `#/11`, `#/12`, `#/14` and `#/15` (source slides
8, 17, 18, 20 and 21) use editable inline SVGs in the mint, blue and navy palette:

- Delivery constraints: the triangle and connections draw in, then Quality arrives.
- Situational leadership: the curve draws and the four matching style cards appear in sequence.
- Competence and confidence: the curve traces from left to right, followed by its landmarks.
- Motivation: the five needs tiers assemble from the foundation upward, with the two factor panels.
- Conflict management: the four quadrants arrive, followed by Compromising at the centre.

All effects replay automatically on slide entry and require no extra clicks.
Overview and topic thumbnails show complete diagrams; reduced motion disables
the entrances. The original image files remain available, and the headings,
speaker notes, footer and navigation remain unchanged.

Edit the five SVGs and `topic-graphics.css` in `public/slides/261023-south-coast/`,
then run the source converter. Its `TOPIC_GRAPHICS` map inlines those assets and
the CSS into `slides.md`, preserving the replacements during regeneration.

Validated with the installed Reveal plugins and slide enhancements at 1600 × 900:
all five graphics fit, the local font loads, entrance animations replay, hub
thumbnails remain static, and reduced motion and 640 × 360 preview scaling work.
All six South Coast deck checks and `npm run build` pass.
