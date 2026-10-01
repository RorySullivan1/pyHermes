# 6. Check and send

Once your email builds, look at it, check it, then get it to your readers. There are three
ways to send it, from simplest to most automated:

| Way | You need | Best for |
|---|---|---|
| [Put it straight into your Outlook drafts](#how-to-put-the-email-straight-into-your-outlook-drafts) | Classic Outlook on Windows | Sending by hand from your own mailbox |
| [Open it as an Outlook draft](#how-to-open-your-email-as-an-outlook-draft) | A mail program that opens `.eml` files | The same, from a saved file |
| [Send through Microsoft 365](#how-to-send-through-microsoft-365-outlook) | An access token from your IT team | Scheduled or automated sends |
| [Send through Gmail](#how-to-send-through-gmail) | Google API credentials | Google Workspace firms |

```python
from pyhermes.builder import EmailBuilder, FullWidth, TextBlock
from pyhermes.builder.images import EmailImage
from pyhermes.delivery import build_message, save_eml

email = (
    EmailBuilder()
    .metadata({
        "email_subject": "Rates Weekly: the curve steepens",
        "firm_name": "Acme Research",
        "campaign_name": "Rates Weekly",
        "preheader_text": "Ten-year yields rose six basis points.",
    })
    .section(FullWidth(TextBlock("<p>The curve steepened.</p>"), title="Summary"))
    .build()
)
```

## How to look at your email

1. **In a browser.** `email.save("rates.html")` writes the email. Open the file in any
   browser. Attached images show as broken here. That is expected, see below.
2. **As plain text.** `print(email.text())` shows the text-only version pyHermes writes
   for you. Read it once: it is what a reader sees on a text-only device.
3. **With the checker.** From any folder:

   ```bash
   python -m pyhermes.check path/to/rates.py:build
   ```

   It saves the HTML and plain-text versions into `output/` and checks the email against
   the rules Outlook and Gmail enforce. It exits with 0 when there is nothing to fix, 1 when
   there is, and 2 when the email does not build, so a script can stop on a problem. In
   Python, `from pyhermes.check import check` and `check(email)` returns the same findings.
4. **As pictures.** From the `pyHermes` folder, with the `[qa]` extra,
   `python -m qa.preview path/to/rates.py:build --screenshot` saves desktop and phone
   pictures of it, with attached images in place, into `output/screenshots/`.

```python
email.save("rates.html")
plain = email.text()
```

> **Note:** a browser shows roughly what Gmail shows. It does not show what Outlook on
> Windows shows, because Outlook lays out email with Microsoft Word. The `--lint` check is
> what covers Outlook. For an important send, also send yourself a test and open it in
> Outlook.

## How to put the email straight into your Outlook drafts

**When to use this:** you use classic Outlook on Windows and want the email waiting in your
drafts, with its pictures, without saving a file or asking IT for anything.

**Steps:**
1. Install the extra once, from the `pyHermes` folder: `pip install -e ".[outlook-desktop]"`.
2. With Outlook open, create the draft:

<!-- manual: skip -->
```python
from pyhermes.outlook.desktop import create_draft

message = build_message(email, sender="you@example.com", to=["reader@example.com"])
create_draft(message)
```

3. The draft opens. Check it, then click **Send**.

**Result:** the draft is saved in your Drafts folder, with the pictures in place and the
attachments listed. pyHermes never sends it: you do.

**Notes:**
- `create_draft(message, display=False)` saves it without opening it.
- It sends from your Outlook account, whatever `sender` says.
- It needs classic Outlook. The new Outlook for Windows has no way for a program to reach
  it, so use the `.eml` route below or [Microsoft 365](#how-to-send-through-microsoft-365-outlook).
- On a Mac or Linux it raises an error that names the alternatives.

## How to open your email as an Outlook draft

**When to use this:** you want to send from your own mailbox, by hand, with the email ready
to go.

**Steps:**
1. Build the message and mark it as unsent:

   ```python
   message = build_message(
       email,
       sender="you@example.com",
       to=["reader@example.com"],
   )
   message["X-Unsent"] = "1"        # tells Outlook to open it as a draft
   save_eml(message, "rates.eml")
   ```

2. Double-click `rates.eml`.
3. Outlook opens it as a new email, ready to edit. Add or change recipients if you need to,
   then click **Send**.

**Result:** your readers get the email exactly as pyHermes built it, with attached images
in place and the plain-text version included.

**Notes:**
- `X-Unsent` is honoured by classic Outlook for Windows. Other mail programs open the file
  as a received email instead. You can still read it, but you cannot send it from there.
- Outlook sends from the account you pick in the draft, whatever `sender` says.
- Do not paste the `.html` file into a new Outlook email. Outlook rewrites pasted HTML and
  drops the attached images.

## How to send to several people, with copies and a reply address

```python
message = build_message(
    email,
    sender="research@example.com",
    to=["alice@example.com", "bob@example.com"],
    cc="desk@example.com",
    reply_to="rates@example.com",
    subject="Rates Weekly: special edition",   # overrides email_subject
)
```

## How to attach a file

**When to use this:** a spreadsheet, a CSV or a PDF the reader downloads.

```python
from pyhermes.delivery import Attachment

csv = "Factor,1M\nValue,0.018\n".encode()
message = build_message(
    email,
    sender="research@example.com",
    to="reader@example.com",
    attachments=[Attachment(csv, "factor-returns.csv", "text/csv")],
)
```

To attach a PDF of a report built with pyHermes, see
[Reports and PDFs](07-reports-and-pdfs.md#how-to-attach-a-pdf-report-to-an-email).

## How to send through Microsoft 365 (Outlook)

**When to use this:** the email goes out on a schedule, with nobody clicking **Send**.

**Before you start:** ask your IT team for a way to get a Microsoft Graph access token
with the `Mail.Send` permission. pyHermes never handles your password or token itself. You
give it a connection that is already signed in.

<!-- manual: skip -->
```python
import requests                      # pip install requests

from pyhermes.outlook import GraphApiTransport, send_message

session = requests.Session()
session.headers["Authorization"] = f"Bearer {token}"   # the token from your IT set-up
send_message(message, transport=GraphApiTransport(session))
```

**Result:** the email is sent from the signed-in mailbox and appears in its Sent Items.

## How to send through Gmail

<!-- manual: skip -->
```python
from googleapiclient.discovery import build   # pip install google-api-python-client

from pyhermes.gmail import GoogleApiTransport, send_message

service = build("gmail", "v1", credentials=creds)   # your signed-in Google credentials
message_id = send_message(message, transport=GoogleApiTransport(service))
```

## How to rehearse a send without sending

`save_eml(message, "preview.eml")` writes exactly the bytes that would be sent. Open it in
your mail program to check it. No network and no credentials are involved.

## How big can an email be?

| Limit | What happens |
|---|---|
| The email itself above **90 KB** | A `SizeWarning` is shown. You can still send it |
| The email itself above **102 KB** | The build stops with `SizeError`, because Gmail would cut the email off |
| The whole message with attachments above **15 MB** | A warning |
| The whole message with attachments above **20 MB** | The build stops, naming each file and its size |

Attached images count towards the 20 MB, not the 102 KB. To shrink an email that is too
big, see [Troubleshooting](08-troubleshooting.md#i-get-sizeerror-about-the-102-kb-gmail-clipping-limit).
