'''
try to dynamically figure out relevant paths
'''

import getpass
username = getpass.getuser()

import socket
hostname = socket.gethostname()

def get_path_names():
    foggie_dir, output_dir = ""
    if username == "molly" and hostname == "dhumuha-2.local":
        foggie_dir = "/Users/molly/foggie/"
        output_dir = "/Users/molly/Dropbox/foggie-collab/"

    if username == "molly" and hostname == "oak":
        foggie_dir = "/astro/simulations/FOGGIE/"
        output_dir = "/Users/molly/Dropbox/foggie-collab/"

    return foggie_dir, output_dir