# compliance/ — approved copy only

Every file here is **supplied** by the user or by compliance. Claude must never write,
paraphrase, shorten, reflow, translate, or "improve" the text in this directory, and must
never put disclaimer text in the context dict instead. `validate_context.py` rejects a
`disclaimer_blocks` entry that looks like prose rather than a filename, for exactly that
reason.

The template references these by filename. To add a block: drop the approved file in, then
name it in the context's `disclaimer_blocks` list.

## The placeholder convention

A file whose body contains the token `PLACEHOLDER` is a **slot, not copy**. Validation
downgrades to a warning and the factsheet still renders — deliberately, so layout work can
proceed before legal sign-off — but the warning says what it means: **the PDF must not be
distributed** until real copy replaces it. The rendered page shows the placeholder visibly
marked, so an unapproved draft cannot be mistaken for a finished document.

If the approved copy is not ready, that is the correct state. Leave the placeholder and say
so; do not draft substitute wording.
