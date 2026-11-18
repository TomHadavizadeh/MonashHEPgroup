# Adding yourself to the website

Every card on the People page comes from one Markdown file in the
[`people/`](people/) folder. To add yours, open a pull request (GitHub) or
merge request (GitLab) that adds that file. No other changes are needed: the
page is rebuilt automatically once it is merged.

## Step by step (in the web interface, no software needed)

1. **Open [`people/_TEMPLATE.md`](people/_TEMPLATE.md)** and copy its contents.
2. In the `people/` folder, click **Add file → Create new file** (GitHub) or
   **+ → New file** (GitLab). Name it after yourself in lower case with
   hyphens, e.g. `jane-citizen.md`.
3. **Paste the template and fill it in.** The fields:

   | Field      | Required | What to put |
   |------------|----------|-------------|
   | `name`     | yes      | Your name as you want it shown |
   | `category` | yes      | `academic`, `postdoc`, `phd` or `honours` |
   | `role`     |          | Your title, e.g. `Associate Professor`, `ARC DECRA Fellow` |
   | `photo`    |          | File name of your photo in `people/photos/` |
   | `areas`    |          | Any of `comet`, `lhcb`, `detector-development`, `qcd`, `flavour`, `cosmology` |
   | `email`, `website`, `inspire`, `orcid`, `github`, `pronouns` | | Optional links and details |

   Below the second `---`, write **two or three sentences about your research**
   (under about 600 characters).

4. **Add a photo (optional).** Upload it to `people/photos/` on the same branch
   (**Add file → Upload files** on GitHub). Use a JPG, PNG or WebP under 1 MB;
   about 600×800 px, portrait, works best. Without a photo, your initials are
   shown instead.
5. Commit to **a new branch** and open the **pull request / merge request**.
   On GitHub, members without write access are offered a fork automatically.
   That's fine.
6. The automatic check runs on your file. If it fails, open the failed check:
   it says exactly which line to fix. When it passes, you can download the
   **site-preview** artifact (GitHub: the run's *Summary* page; GitLab: the
   merge request's *Site preview* link) to see your card before it goes live.
7. A maintainer reviews and merges. Your card appears within a few minutes.

## When you leave the group

Don't delete your card. Add these lines to it so you move to **Previous members**:

```yaml
former: true
years: 2022–2026
now: Postdoc at CERN      # optional
```

## Adding a research project

Copy [`projects/_TEMPLATE.md`](projects/_TEMPLATE.md) to
`projects/short-project-name.md` and fill it in. `level` can include `phd`,
`honours` and/or `other` (summer, undergraduate, Masters). When the project is
taken, set `status: filled` or delete the file.

## Adding or editing a research area

Each page in the **Research** menu is a file in `research/experimental/` or
`research/theoretical/`. Add a new file there and it appears in the menu
automatically. Use `order:` to control its position and `leads:` to list
the people who lead it (by their card's file name, e.g. `peter-skands`).

## Previewing on your own computer (optional)

```bash
pip install -r requirements.txt
python build.py --serve        # then open http://localhost:8000
python build.py --check        # just validate
```
