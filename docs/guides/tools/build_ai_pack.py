"""Builds the AnythingLLM knowledge pack in docs/guides/ai-pack/ from the guides themselves, so it never drifts:

    python docs/guides/tools/build_ai_pack.py

- knowledge/user-*.md        one card per section of the Training Guide (how to use IntraForge)
- knowledge/eng-*.md         one card per section of the Engineering Handbook (how it is built)
- knowledge/ref-*.md         the generated API, data-model and module references
- knowledge/screens.md       every screenshot: its file and what it shows
- screenshots/               the pictures the cards point to

Each card that has a picture carries it twice: as a file path (always works) and as a Markdown image on
http://localhost:8765/ (shows inside the chat while Show-Pictures.cmd is running). No downloads, no network.
"""

import pathlib
import re
import shutil

GUIDES = pathlib.Path(__file__).resolve().parents[1]
PACK = GUIDES / "ai-pack"
KNOW = PACK / "knowledge"
PICTURES_URL = "http://localhost:8765/"

# Screenshots the Training Guide does not show, with what they show.
EXTRA_CAPTIONS = {
    "control-center/5-uninstall.png": "Control Center: Uninstall — the three ways to remove IntraForge",
    "control-center/6-output.png": "Control Center: the output of a task (what the scripts printed)",
    "control-center/7-shop-wifi.png": "Control Center: Shop network — letting other PCs and phones on the shop Wi-Fi open IntraForge",
    "control-center/9-settings-shop-names.png": "Control Center: Settings — the shop's names on the network (for example myshop.lan, movies.lan)",
    "control-center/10-names-ending.png": "Control Center: choosing the ending of the shop's names",
    "web/06-organizations.png": "IntraForge: the list of organizations",
    "web/08-workspace.png": "IntraForge: a workspace and its projects",
    "web/17-database.png": "IntraForge: a database and its tables (the database builder)",
    "web/21-app-gallery.png": "IntraForge: the application gallery (Apps > Available to install)",
    "web/23-units.png": "IntraForge: organizational units (branches, departments)",
    "web/25-websites.png": "IntraForge: hosted websites of an organization",
    "web/26-developer.png": "IntraForge: the developer area (applications, API keys, environments, webhooks)",
    "web/27-developer-applications.png": "IntraForge: developer applications (programs that connect with a token)",
    "web/28-application.png": "IntraForge: one application, its credentials and access",
    "web/40-movie-shops.png": "Movie Shop: the list of shops",
    "web/52-portal-sign-up.png": "Movie Shop customer portal: signing up on a phone",
    "web/81-spareparts-catalogue.png": "Spare Parts shop app: the reference catalogue",
    "web/82-spareparts-admin.png": "Spare Parts shop app: administration and settings",
    "web/86-pharmacy-medicines.png": "Pharmacy app: the medicines list",
}

IMAGE = re.compile(r"^!\[([^\]]*)\]\((?:\.\./)?screenshots/([^)]+)\)\s*$")


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60]


def picture_lines(caption: str, rel: str) -> list[str]:
    return [f"Screenshot: `screenshots/{rel}` — {caption}", "", f"![{caption}]({PICTURES_URL}screenshots/{rel})"]


def split_cards(md: str) -> list[tuple[str, str, list[str]]]:
    """(chapter title, section title, lines) per H2 section; text before the first H2 is the chapter's intro card."""
    cards, chapter, section, lines = [], "", "", []

    def flush():
        if any(line.strip() for line in lines):
            cards.append((chapter, section or chapter, lines.copy()))
        lines.clear()

    for line in md.replace("\r\n", "\n").split("\n"):
        if line.startswith("# "):
            flush(); chapter, section = line[2:].strip(), ""
        elif line.startswith("## "):
            flush(); section = line[3:].strip()
        else:
            lines.append(line)
    flush()
    return cards


def write_cards(folder: str, prefix: str, audience: str) -> tuple[int, dict[str, str]]:
    count, captions = 0, {}
    for part in sorted((GUIDES / folder).glob("*.md")):
        if part.name.startswith("9"):
            continue  # the generated references are copied whole below
        for chapter, section, lines in split_cards(part.read_text(encoding="utf-8")):
            body = []
            for line in lines:
                m = IMAGE.match(line)
                if m:
                    captions.setdefault(m.group(2), m.group(1))
                    body += picture_lines(m.group(1), m.group(2))
                else:
                    body.append(line)
            title = section if section == chapter else f"{chapter} — {section}"
            text = (f"# {title}\n\nTopic for: {audience}. Source: IntraForge {('Training Guide' if prefix == 'user' else 'Engineering Handbook')}, "
                    f"{chapter}.\n\n" + "\n".join(body).strip() + "\n")
            count += 1
            (KNOW / f"{prefix}-{part.stem[:2]}-{count:03d}-{slug(section)}.md").write_text(text, encoding="utf-8")
    return count, captions


def main() -> None:
    if KNOW.exists():
        shutil.rmtree(KNOW)
    KNOW.mkdir(parents=True)
    shots = PACK / "screenshots"
    if shots.exists():
        shutil.rmtree(shots)
    shutil.copytree(GUIDES / "screenshots", shots, ignore=shutil.ignore_patterns("*.txt"))

    n_user, captions = write_cards("training", "user", "shop owners, managers and staff")
    n_eng, more = write_cards("engineering", "eng", "software engineers")
    captions.update(more)
    for name, target in (("90-reference-api.md", "ref-api.md"), ("91-reference-models.md", "ref-data-model.md"),
                         ("92-reference-modules.md", "ref-modules.md")):
        shutil.copyfile(GUIDES / "engineering" / name, KNOW / target)

    captions.update({k: v for k, v in EXTRA_CAPTIONS.items() if k not in captions})
    lines = ["# Every screen of IntraForge (screenshot catalogue)", "",
             "Each line names a screenshot file in the pack's `screenshots` folder and what it shows. When someone asks "
             "what a screen looks like, answer with the matching file and its picture line.", ""]
    for rel in sorted(captions):
        if (shots / rel).exists():
            lines += [f"## {captions[rel]}", "", *picture_lines(captions[rel], rel), ""]
    (KNOW / "screens.md").write_text("\n".join(lines), encoding="utf-8")
    missing = sorted(p.relative_to(shots).as_posix() for p in shots.rglob("*.png")
                     if p.relative_to(shots).as_posix() not in captions)
    print(f"{n_user} user cards, {n_eng} engineering cards, 3 references, {len(captions)} screenshots described")
    if missing:
        print("screenshots without a caption:", ", ".join(missing))


if __name__ == "__main__":
    main()
