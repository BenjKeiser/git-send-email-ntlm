#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tempfile
import subprocess
import shutil
import argparse
import sys
from ConfigParser import ConfigParser
from os.path import expanduser
from os import linesep, getpid
import StringIO
from time import gmtime, strftime, time
import getpass
import smtplib
from ntlm import ntlm

APPLICATION = "git-send-email-ntlm"
VERSION = "0.0.1"

message_sequence = 0

def create_patches(output_dir, format_patch_args=[]):
    all_args = ["git", "format-patch", "-o", output_dir]
    all_args.extend(format_patch_args)
    out_files = subprocess.check_output(
        all_args,
        stderr=subprocess.STDOUT
    )
    print out_files.strip()
    return out_files.splitlines()

def parse_patch_file(patch_file, email_address, subject_replacement="PATCH"):
    parsing_headers = True
    cc = set()
    subject = ""
    message = ""
    for line in open(patch_file, "r"):
        if parsing_headers and len(line.strip()) == 0:
            parsing_headers = False
            continue

        if parsing_headers and line.startswith("From "):
            continue
        elif parsing_headers and line.startswith("From: "):
            address = line[6:].strip()
            cc.add(address)
            print "(mbox) Adding cc: %s from line '%s'"%(address, line.strip())
        elif parsing_headers and line.startswith("Subject: "):
            subject = line[9:].replace("PATCH", subject_replacement, 1).strip()

        if not parsing_headers:
            if line.startswith("Signed-off-by: "):
                address = line[15:].strip()
                cc.add(address)
                print "(body) Adding cc: %s from line '%s'"%(address, line.strip())
            message += line

    parsed_output = {
        "cc" : list(cc),
        "subject" : subject,
        "message" : message
    }
    return parsed_output


def generate_smtp_headers(
    from_address,
    fq_from_address,
    to_address,
    subject,
    parsed_output
    ):

    global APPLICATION
    global VERSION
    global message_sequence
    message_sequence += 1
    cc = ", ".join(parsed_output["cc"])
    if len(cc) > 0:
        cc = "Cc: %s\n"%cc
    message_id = "%d-%d-%d-%s-%s"%(
        int(time()),
        getpid(),
        message_sequence,
        APPLICATION,
        from_address
    )
    headers = """From: %s
To: %s
%sSubject: %s
Date: %s
Message-Id: <%s>
X-Mailer: %s %s
"""%(
    fq_from_address,
    to_address,
    cc,
    subject,
    strftime("%a, %d %b %Y %H:%M:%S +0000", gmtime()),
    message_id,
    APPLICATION,
    VERSION
)
    return headers
  

def ntlm_authenticate(smtp, username, password):
    code, response = smtp.docmd(
        "AUTH",
        "NTLM " + ntlm.create_NTLM_NEGOTIATE_MESSAGE(username)
    )
    if code != 334:
        raise smtplib.SMTPException(
            "Server did not respond as expected to NTLM negotiate message"
        )
    challenge, flags = ntlm.parse_NTLM_CHALLENGE_MESSAGE(response)
    user_parts = username.split("\\", 1)
    code, response = smtp.docmd(
        "",
        ntlm.create_NTLM_AUTHENTICATE_MESSAGE(
            challenge,
            user_parts[1],
            user_parts[0],
            password,
            flags
        )
    )
    if code != 235:
        raise smtplib.SMTPException(code, response)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        prog=sys.argv[0],
        description="Email-sender for git with NTLM support",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        "--subject-prefix",
        dest="subject_prefix",
        help="String to replace the PATCH keyword with in the subject-line",
        default="PATCH"
    )

    parser.add_argument(
        "--to",
        dest="to",
        help="Recepient of email",
        required=True
    )
   
    args, unknown_args = parser.parse_known_args(sys.argv[1:]) 

    config_text = linesep.join(
        [line.strip() for line in open(expanduser("~/.gitconfig"))]
    )
    config_fp = StringIO.StringIO(config_text)
    config = ConfigParser()
    config.readfp(config_fp)
    email_address = config.get("user", "email")
    smtp_server = config.get("sendemail", "smtpserver")
    smtp_port = config.getint("sendemail", "smtpserverport")
    smtp_user = config.get("sendemail", "smtpuser")
    smtp_user = smtp_user.replace("\\\\", "\\").strip().replace("\"", "")
    smtp_password = ""
    if config.has_option("sendemail", "smtppassword"):
        config.get("sendemail", "smtppassword").strip().replace("\"", "")
    fq_email_address = "%s <%s>"%(
        config.get("user", "name"),
        config.get("user", "email")
    )

    temp_dir = tempfile.mkdtemp()
    patches = create_patches(temp_dir, unknown_args)
    send_all_messages = False
    for patch in patches:
        parsed_output = parse_patch_file(
            patch,
            email_address,
            args.subject_prefix
        )
        headers = generate_smtp_headers(
            email_address,
            fq_email_address,
            args.to,
            parsed_output["subject"],
            parsed_output
        )
        print ""
        print headers
        full_message = "%s\n%s"%(headers, parsed_output["message"])
        while True:
            if send_all_messages:
                user_input = "a"
            else:
                user_input = raw_input(
                    "Send this email? ([y]es|[n]o|[q]uit|[a]ll): "
                ).lower()
            if user_input not in "ynqa":
                continue

            if user_input == "q":
                sys.exit(0)

            if user_input in "ya":
                if user_input == "a":
                    send_all_messages = True
                if smtp_password == "":
                    smtp_password = getpass.getpass(
                        "Password for %s at %s:%d "%(
                            smtp_user,
                            smtp_server,
                            smtp_port
                        )
                    )
                try:
                    connection = smtplib.SMTP(smtp_server, smtp_port)
                    # connection.set_debuglevel(True)
                    connection.ehlo()
                    ntlm_authenticate(connection, smtp_user, smtp_password)
                    connection.sendmail(fq_email_address, [args.to], full_message)
                    print "Email sent."
                    print ""
                except smtplib.SMTPException, e:
                    code = e.args[0]
                    message = e.args[1]
                    print "SMTP Error:", code, message
                    sys.exit(1)
            break

    shutil.rmtree(temp_dir)
