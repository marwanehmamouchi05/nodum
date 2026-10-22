# AWS judge deployment — October 22, 2026

Demo: https://nodum.54-173-165-46.sslip.io/app/

Video: https://youtu.be/ITCj4CzEHEg (unlisted, 2:55).

## Runtime and boundaries

One on-demand EC2 t3.micro in us-east-1 runs the reviewed packaged backend and
compiled interface. An encrypted 20 GiB gp3 volume stores the separate synthetic
judge database at `/opt/nodum/data/free-judge-demo.db` on the host, mounted at
`/data/free-judge-demo.db` in the app. The original Railway database is preserved.

Caddy provides HTTPS and renews certificates automatically. A fixed Elastic IP
backs the sslip.io hostname. Only ports 80 and 443 accept public inbound traffic;
SSH is closed. The app listens on loopback behind Caddy. The hostname depends on
the external sslip.io DNS service; a custom domain can replace it later.

The EC2 role permits the configured Nova model/profile invocation and standard
Systems Manager agent administration. No long-lived AWS key is installed in the
app. IMDSv2 is required. Owner administration uses AWS Systems Manager rather than
a public SSH endpoint. Private app configuration and reviewer passwords are not
source-controlled or included here.

Docker starts on boot. Both app and TLS containers use `unless-stopped` restart
policies. A full instance reboot passed, including fresh real Bedrock inference
and preservation of accounts, custom Ring events and product-operation records.
This is one server, not a highly available cluster or a promise of zero outages.

## Backups and recovery

A systemd timer creates a consistent SQLite backup every twelve hours and retains
fourteen copies under `/opt/nodum/data/backups/`. These copies share the instance
volume, so they protect against logical mistakes rather than total volume loss.
An initial EBS snapshot was also created for recovery independently of the instance.
The owner's private deployment checkpoint records resource/snapshot identifiers.

Before changing application code/configuration, make a new consistent database
backup and EBS snapshot. Restore into a new path/volume; never overwrite the only
copy. Check SQLite integrity and foreign keys before selecting the restored file.
Retain the runtime signing/encryption settings when recovering encrypted data.
Do not rerun a fresh installation over the active judge database.

## Availability and cost

The owner approved existing AWS credit use with an approximately $15/month hosting
target and no paid-plan upgrade. Base compute, 20 GiB storage and one public IPv4
address total approximately $13/month at the checked rates; backups, model calls
and traffic can add usage. CPU credits use Standard mode to avoid Unlimited charges.

The account had about $120 in credits and a March 28, 2027 Free-plan end date at
verification. Credits and plan expiry must still be checked through judging.
The deployment needs no entrant laptop, but it stops being available if the server
is stopped or the account/credits expire. Preserve access through November 20.

## Demonstrated scope

The hosted app passed reviewer logins, role boundaries, CSRF rejection, the custom
signed visitor-arrival simulation, actual Bedrock/Nova tool use and reboot persistence.
The video labels earlier official Ring Playground discovery separately from custom
event simulation. Temporary discovery tokens do not establish production linking,
vendor webhook delivery, visitor identity or physical door control.
