# git-send-email-ntlm
A replacement for git-send-email that knows NTLM.


## Installation and usage

I copy my script to /usr/lib/git-core (without the .py ending) and make sure it's
executable.

```bash
sudo cp git-send-email-ntlm.py /usr/lib/git-core/git-send-email-ntlm
```

You can then just run it with "git":

```bash
git send-email-ntlm --to=foo@bar.baz -M -1
```

## Supported parameters

* --to
* --subject-prefix

All unknown parameters are passed on to git-format-patch.


## Configuration

git-send-email-ntlm requires the following parameters from your ~/.gitconfig:
```ini
[sendemail]
    smtpserver = some.hostname.foo
    smtpserverport = 25
    smtpuser = "DOMAIN\\username"
```

Putting your SMTP password in your .gitconfig is also possible, but I don't recommend it.

git-send-email-ntlm will ask you for your password interactively if you don't put it in your .gitconfig.

```ini
[sendemail]
    ...other options...
    smtppassword = "secret"
```
