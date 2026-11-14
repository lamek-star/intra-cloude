# IntraForge Mentor — knowledge pack for AnythingLLM

This folder turns an offline AnythingLLM (with a local model through Ollama or AnythingLLM's own runner) into a mentor
that answers questions about IntraForge — how to use it and how it is built — and shows the screen it is talking about.
Nothing here needs the internet.

| In this folder | What it is |
|---|---|
| `knowledge/user-*.md` | One card per topic of the Training Guide (for shop owners and staff) |
| `knowledge/eng-*.md` | One card per topic of the Engineering Handbook (for software engineers) |
| `knowledge/ref-api.md`, `ref-data-model.md`, `ref-modules.md` | Every API endpoint, database model and source file, generated from the code |
| `knowledge/screens.md` | Every screenshot and what it shows |
| `screenshots/` | The pictures (web app, phone portal, Control Center) |
| `system-prompt.txt` | The mentor's instructions — paste into the workspace settings |
| `Show-Pictures.cmd` | Lets the chat show the pictures (see step 5) |

## Set it up (about 15 minutes)

1. **Open AnythingLLM** and choose your model under *Settings > AI Providers > LLM*. A model with at least 7–8 billion
   parameters answers much better than a small one. If you use Ollama, pick it there and choose the model you pulled.
2. **Embedder:** keep AnythingLLM's built-in embedder (*Settings > AI Providers > Embedder > AnythingLLM Embedder*) —
   it works offline.
3. **Create a workspace** named `IntraForge Mentor`.
4. **Add the documents:** in the workspace, click the upload icon, drag in **all the files of the `knowledge` folder**
   (not the screenshots), select them and press **Move to Workspace**, then **Save and Embed**. Optionally add the two
   PDFs (`docs/guides/out/IntraForge-Training-Guide.pdf`, `IntraForge-Engineering-Handbook.pdf`) too; the cards
   already hold the same text.
5. **Pictures in the chat (optional):** double-click `Show-Pictures.cmd` and leave its window open while you chat. It
   serves only the PNG files of `screenshots/` on `http://localhost:8765/`, to this computer only. Without it the
   answer still names the screenshot file — open it from the `screenshots` folder.
6. **Instructions:** open the workspace's settings (gear icon) > **Chat Settings** > **Prompt**, paste the whole of
   `system-prompt.txt` and save. Under the same settings set **Chat mode** to *Query* (answers only from the
   documents) and, under **Vector Database**, raise **Max Context Snippets** to 6–8.

## Try it

- "How do I sell a part at the counter?"
- "Show me the Movie Shop catalogue screen."
- "A customer forgot their portal password — what do I do?"
- "How do I check last night's backup?"
- "Where is the code that decides whether someone may sell stock?"
- "Which endpoint creates a sale, and what does it check?"
- "How do I add a new built-in application?"

## Keeping it current

After the guides change, rebuild the pack from the repository root and re-upload the `knowledge` files
(AnythingLLM: remove the old documents from the workspace first):

```
python docs/guides/tools/build_ai_pack.py
```

## Good to know

- The mentor knows only these documents. It cannot see your shop's live data, and it should never be given passwords,
  keys or the `.env` file.
- A local model can still be wrong. For anything that deletes or restores data, follow the Training Guide and take a
  backup first.
