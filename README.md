# git-send-email-ntlm
A replacement for git-send-email that knows NTLM.

Supported parameters:

 * --to
 * --subject-prefix

All unknown parameters are passed on to git-format-patch.

I copy my script to /usr/lib/git-core (without the .py ending).

```bash
sudo cp git-send-email-ntlm.py /usr/lib/git-core/git-send-email-ntlm
```

You can then just run it with "git":

```bash
git send-email-ntlm --to=foo@bar.baz -M -1
```
