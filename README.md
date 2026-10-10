# Reveal.js slide showcase

This repository is a copy-and-paste template for decks hosted by
[slides.mightora.io](https://slides.mightora.io/). The included
[`platform-showcase`](platform-showcase) deck demonstrates the supported
Reveal.js and platform features, with the Markdown source shown on each
slide.

## Quick start

1. Fork or copy this repository.
2. Edit `platform-showcase/slides.md` and `platform-showcase/meta.json`.
3. Push the changes to the `main` branch of a **public** GitHub repository.
4. Open the deck using these URLs, replacing the placeholders:

	 ```text
	 https://slides.mightora.io/r/<owner>/<repo>/platform-showcase/follower
	 https://slides.mightora.io/r/<owner>/<repo>/platform-showcase/presenter
	 ```

The folder name is the deck ID. Use lowercase letters, numbers, and hyphens
for it. Presenter mode requires the platform presenter password; follower mode
is the audience view.

## Deck structure

Each remote deck consists of exactly two files:

```text
<deck-id>/
├── meta.json
└── slides.md
```

For a repository containing multiple decks, keep them in a `decks/` directory:

```text
decks/
├── product-launch/
│   ├── meta.json
│   └── slides.md
└── workshop/
		├── meta.json
		└── slides.md
```

Remote decks read `slides.md` from the `main` branch. A remote deck cannot load
`slides.html`; use Markdown only.

## Writing slides

Use standard Markdown, HTML, and Reveal.js slide comments:

```md
# Opening slide

---

## Next topic

--

### Vertical detail slide
```

- `---` starts a horizontal slide.
- `--` starts a vertical child slide.
- `Notes:` starts speaker notes for the current slide.
- `<!-- .slide: ... -->` sets Reveal.js attributes for the slide and must be
	the first line of that slide.
- `<!-- .element: ... -->` sets attributes on the preceding Markdown element.

The showcase contains examples for fragments, transitions, auto-animate,
Mermaid, PlantUML, video, images, background media, links, and Reveal layout
helpers. It is the fastest reference for syntax supported by the platform.

## `meta.json`

The smallest useful metadata file is:

```json
{
	"title": "My Talk",
	"description": "A short description shown on the landing page",
	"published": true,
	"theme": "black"
}
```

Supported fields include:

| Field | Purpose |
| --- | --- |
| `title` | Deck title shown on the landing page |
| `description` | Landing-page description |
| `published` | Whether the deck appears in the deck list; direct URLs still work when false |
| `theme` | Reveal theme: `black`, `white`, `league`, `beige`, `sky`, `night`, `serif`, `simple`, `solarized`, `moon`, `dracula`, or `blood` |
| `autoFragment` | Makes list items appear as click-to-reveal fragments |
| `availableFrom` | ISO 8601 UTC time when the deck becomes available |
| `selfExploreFrom` | ISO 8601 UTC time when followers can browse independently |
| `videoPlaybackRate` | Playback rate applied to videos |
| `videoBackgroundSize` | Background-video sizing, such as `contain` |
| `defaultBackground` | Default `image`, `color`, `gradient`, or `video` background and its display options |

If neither availability date is set, the deck is open immediately. During a
live event, followers stay on the presenter's current slide until
`selfExploreFrom`.

## Assets and diagrams

Use absolute URLs for images and videos in remote decks. Relative paths resolve
against `slides.mightora.io`, not this repository:

```md
![Logo](https://raw.githubusercontent.com/<owner>/<repo>/main/assets/logo.png)
```

Mermaid uses a `mermaid` fenced block. PlantUML uses a `plantuml` fenced block.
Both are rendered by the platform when the slide is shown.

## Presenter workflow

Open the presenter URL to use the platform HUD, speaker view, follower list,
messages, whiteboard, break overlay, and live synchronization. The first slide
in presenter mode includes the follower URL and a QR code to share with the
audience.

## Troubleshooting

- **Metadata not found:** confirm `meta.json` is in the deck folder on `main`.
- **Missing images or video:** use an absolute URL and confirm the asset is publicly reachable.
- **Slides merge together:** put blank lines around `---` and `--` separators.
- **Notes appear on screen:** use one `Notes:` block per slide.
- **A diagram is blank:** check that the fence language is exactly `mermaid` or `plantuml`.

For a complete feature reference, open the included showcase deck and inspect
the Markdown beneath each example.