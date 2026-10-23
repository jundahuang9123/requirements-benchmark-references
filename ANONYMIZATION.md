# Preparing a separate anonymous repository

Curator names have been replaced with neutral role labels. Upstream account links,
source commit IDs and workstation paths have been removed from the distributed
files. Scientific citations, third-party attribution, source documents and the
disclosure of machine-assisted curation remain. The supplement PDF's text and
metadata and the other bundled PDFs were checked for known curator identifiers.
The two PNG figures were visually inspected and their metadata checked; the export
accepts only those exact reviewed image bytes.

The current repository owner, public URL and earlier Git commits still identify
the project. These edits sanitize the current files; they do not erase publication
history or guarantee that identical public content cannot be linked back to it.
Use a fresh repository or your venue's anonymous hosting service for review.
Do not fork, mirror, copy `.git`, or reuse the existing Git history for that purpose.

From the checkout root, with Poppler installed, export a clean snapshot:

```sh
python3 tools/export_anonymous.py ../anonymous-references.zip
```

The command includes tracked files from the current working tree, checks the
sanitized benchmark hashes, scans text and PDF metadata for local user paths,
and excludes Git history, remotes and untracked files. ZIP timestamps and permissions
are normalized. Add `--deny-term` for each private name, email address or account
identifier to check; keep those arguments outside versioned files. Inspection
does not detect every possible identifier, image annotation or indirect clue.

Extract the ZIP into a new directory. Upload its contents to the anonymous host.
If using Git, create new history under an anonymous account with neutral author
and committer metadata. Do not connect it to the original account, issues or PRs.
Review the host's displayed owner, links and commit metadata before sharing it.

`IMPORT-PROVENANCE.json` describes the sanitized snapshot, with hashes recalculated
after changes. Refresh those hashes whenever benchmark files change. Archived
build scripts record the original workflow; their neutral `workspace/` paths are
placeholders and require local configuration before reuse.
