# mount_manager #

A simple mount management script.

## Usage ##

Run mount_manager :) It uses a directory ~/.mounts where it scans for individual files describing the mounts you want.

Each file has a yaml config like this:

type: sshfs
server: example.com
path: /usr/users/amcharg
mount: /mnt/example

The path is the path on the server you want mounted and the rest is hopefully obvious.
